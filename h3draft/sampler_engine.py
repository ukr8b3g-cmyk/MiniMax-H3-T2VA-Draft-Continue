"""Sampler-only Preview / GO transactions; legacy integrated Engine stays unchanged."""
from __future__ import annotations

from dataclasses import dataclass
import time
import torch
from . import VERSION
from .contracts import DraftError, graph_signature
from .engine import Engine, DraftResult
from .sampler_backend import CoreSamplerBackend
from .sampler_state import SamplerDraftState, external_sigmas, freeze, native_geometry
from .structured import structured_manifest


@dataclass
class SamplerContinueResult:
    latent: dict
    denoised: dict
    report: dict


class SamplerEngine(Engine):
    def __init__(self, backend=None):
        self.backend = backend if backend is not None else CoreSamplerBackend()

    @torch.inference_mode()
    def draft_external(self, noise, guider, sampler, sigmas, latent_image, video_vae,
                       preview_steps=3, prompt=None, unique_id=""):
        report = {"version": VERSION, "operation": "sampler_draft", "status": "running",
                  "stage_timings_s": {}, "quality_certified": False,
                  "execution_path": "external_core_h3_euler_split",
                  "full_run_parity_gpu_verified": False, "warnings": []}
        started = time.perf_counter()
        with self.timed(report, "validate_inputs"):
            external_sigmas(sigmas, preview_steps)
            geometry = self.backend.validate_external(noise, guider, sampler, latent_image, video_vae)
            structured_manifest(guider.original_conds, geometry)
            owned_guider = self.backend.snapshot_guider(guider)
            owned_sampler = self.backend.snapshot_sampler(sampler)
            schedule = freeze(sigmas, "SIGMAS")
            latent = self.backend.copy_latent(latent_image)
        with self.timed(report, "draft_sampling"):
            import copy
            working = copy.copy(owned_guider)
            working.model_patcher = owned_guider.model_patcher.clone()
            working.model_options = working.model_patcher.model_options
            working.original_conds = freeze(owned_guider.original_conds, "Conditioning")
            partial, x0 = self.backend.sample_external(noise, working, owned_sampler,
                latent, schedule[:preview_steps+1].clone())
            if native_geometry(self.backend.av_parts(partial)) != geometry:
                raise DraftError("Core sampling changed the input AV geometry.")
        with self.timed(report, "preview_decode"):
            images = self.backend.decode_video(x0, video_vae)
            if tuple(images.shape) != (geometry["frame_count"], geometry["height"], geometry["width"], 3):
                raise DraftError("VAE Preview geometry does not match the input latent.")
            image = images[:1].detach().cpu().clone()
            del images, x0, latent
        with self.timed(report, "state_capture"):
            metadata = {k:v for k,v in partial.items() if k != "samples"}
            state = SamplerDraftState.create(owned_guider, owned_sampler, video_vae,
                self.backend.av_parts(partial), metadata, schedule, image, noise.seed,
                preview_steps, graph_signature(prompt, unique_id), unique_id, guider, sampler,
                latent_image, sigmas, noise)
        report.update(status="ready", state=state.summary(), total_wall_s=time.perf_counter()-started,
                      sampling_transitions=preview_steps, denoiser_evaluations=None,
                      new_noise=True, external_noise_used=True,
                      conditioning_reencoded=False, schedule_rebuilt=False,
                      native_reference_passthrough=True,
                      reference_reencoded=False,
                      reference_count=state.reference_manifest["count"],
                      preview={"kind":"x0_estimate", "frame_index":0,
                               "decoded_frames":geometry["frame_count"],
                               "prediction_eval_index":preview_steps-1,
                               "prediction_sigma":float(schedule[preview_steps-1]),
                               "not_a_guaranteed_final_frame":True})
        return DraftResult(state, report)

    @torch.inference_mode()
    def continue_external(self, state, approval, prompt=None):
        if not isinstance(state, SamplerDraftState):
            raise DraftError("Connect H3 Draft Sampler to H3 Continue Sampler; the legacy integrated Draft uses a different state type.")
        if not state._lock.acquire(blocking=False):
            raise DraftError("This draft is already being continued. Wait for the active job.")
        try:
            started = time.perf_counter()
            report = {"version": VERSION, "operation":"sampler_continue", "status":"running",
                      "stage_timings_s":{}, "quality_certified":False,
                      "full_run_parity_gpu_verified":False}
            with self.timed(report, "verify_state"):
                state.verify(approval, graph_signature(prompt, state.source_node_id))
            with self.timed(report, "continue_sampling"):
                latent = self.backend.pack(freeze(state.av, "AV state"), state.latent_metadata)
                final, x0 = self.backend.sample_external(self.backend.zero_noise(state.seed),
                    state.fresh_guider(), self.backend.snapshot_sampler(state.sampler), latent,
                    state.sigmas[state.preview_steps:].clone())
                expected = native_geometry(state.av)
                if (native_geometry(self.backend.av_parts(final)) != expected or
                        native_geometry(self.backend.av_parts(x0)) != expected):
                    raise DraftError("Continued AV geometry differs from the reviewed state.")
            remaining = len(state.sigmas)-1-state.preview_steps
            report.update(status="complete", state_id=state.state_id,
                          source_node_id=state.source_node_id, resumed_from_step=state.preview_steps,
                          sampling_transitions=remaining, denoiser_evaluations=None,
                          new_noise=False, conditioning_reencoded=False, schedule_rebuilt=False,
                          image_reencoding=False, conditioning_preserved=True,
                          native_reference_passthrough=True,
                          reference_reencoded=False,
                          reference_count=state.reference_manifest["count"],
                          reference_payload_sha256=state.reference_hash,
                          structured_layout=structured_manifest(state.guider.original_conds),
                          decoding="external_workflow", output_type="LATENT",
                          total_wall_s=time.perf_counter()-started)
            return SamplerContinueResult(final, x0, report)
        finally:
            state._lock.release()
