"""Preview and Continue transactions; cancellation never yields an approved state."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import time
import torch
from . import VERSION
from .backend import CoreBackend
from .contracts import DraftError, Settings, graph_signature
from .state import DraftState, clone_cpu, validate_av, validate_sigmas


@dataclass
class DraftResult:
    state: DraftState
    report: dict


@dataclass
class ContinueResult:
    video: object
    latent: dict
    report: dict


class Engine:
    def __init__(self, backend=None):
        self.backend = backend if backend is not None else CoreBackend()

    @contextmanager
    def timed(self, report, stage):
        self.backend.interrupt()
        started = time.perf_counter()
        report["stage"] = stage
        try:
            yield
        finally:
            report["stage_timings_s"][stage] = time.perf_counter() - started

    @torch.inference_mode()
    def draft(self, settings, model, clip, video_vae, audio_vae, prompt=None, unique_id=""):
        settings.validate()
        report = {"version": VERSION, "operation": "draft", "status": "running", "stage_timings_s": {},
                  "quality_certified": False, "execution_path": "native_core_t2va_euler_split",
                  "full_run_parity_gpu_verified": False, "warnings": []}
        start = time.perf_counter()
        with self.timed(report, "validate_models"):
            self.backend.validate_models(model, clip, video_vae, audio_vae)
            model = model.clone()
        with self.timed(report, "conditioning_and_schedule"):
            positive, latent, sigmas = self.backend.prepare(model, clip, video_vae, settings)
            validate_sigmas(sigmas, settings)
            validate_av(self.backend.av_parts(latent), settings)
        with self.timed(report, "draft_sampling"):
            partial, x0 = self.backend.sample(model, positive, latent,
                sigmas[:settings.preview_steps+1], settings, resume=False)
            validate_av(self.backend.av_parts(partial), settings)
        with self.timed(report, "preview_decode"):
            images = self.backend.decode_video(x0, video_vae)
            if tuple(images.shape) != (settings.frame_count, settings.height, settings.width, 3):
                raise DraftError("Decoded frame geometry differs from the requested H3 frame grid.")
            preview = images[:1].detach().cpu().clone()
            del images, x0, latent
        with self.timed(report, "state_capture"):
            state = DraftState.create(settings, model, clip, video_vae, audio_vae,
                self.backend.av_parts(partial), positive, sigmas, preview,
                graph_signature(prompt, unique_id), unique_id)
        report.update(status="ready", state=state.summary(), total_wall_s=time.perf_counter()-start,
                      preview={"kind": "x0_estimate", "frame_index": 0,
                               "decoded_frames": settings.frame_count,
                               "prediction_eval_index": settings.preview_steps-1,
                               "prediction_sigma": float(sigmas[settings.preview_steps-1]),
                               "not_a_guaranteed_final_frame": True},
                      denoiser_evaluations=settings.preview_steps, new_noise=True)
        if settings.width * settings.height > 768 * 1344:
            report["warnings"].append("Canvas exceeds the conventional H3 area; memory and quality require local verification.")
        return DraftResult(state, report)

    @torch.inference_mode()
    def continue_(self, state, approval, prompt=None):
        if not isinstance(state, DraftState):
            raise DraftError("Connect H3 T2VA Draft's draft_state output. A LATENT or image is not a Draft State.")
        if not state._lock.acquire(blocking=False):
            raise DraftError("This draft is already being continued. Wait for the active job.")
        try:
            report = {"version": VERSION, "operation": "continue", "status": "running", "stage_timings_s": {},
                      "quality_certified": False, "full_run_parity_gpu_verified": False}
            start = time.perf_counter()
            with self.timed(report, "verify_state"):
                state.verify(approval, graph_signature(prompt, state.source_node_id))
            with self.timed(report, "continue_sampling"):
                latent = self.backend.latent(clone_cpu(state.av))
                final, _ = self.backend.sample(state.model, clone_cpu(state.conditioning), latent,
                    state.sigmas[state.settings.preview_steps:].clone(), state.settings, resume=True)
                validate_av(self.backend.av_parts(final), state.settings)
            with self.timed(report, "decode_video"):
                images = self.backend.decode_video(final, state.video_vae)
                if tuple(images.shape) != (state.settings.frame_count, state.settings.height, state.settings.width, 3):
                    raise DraftError("Final decoded frame geometry differs from the Draft State.")
            with self.timed(report, "decode_audio"):
                audio = self.backend.decode_audio(final, state.audio_vae)
            with self.timed(report, "create_video"):
                video = self.backend.create_video(images, audio)
            report.update(status="complete", state_id=state.state_id,
                          source_node_id=state.source_node_id, settings=state.settings.manifest(),
                          resumed_from_step=state.settings.preview_steps,
                          denoiser_evaluations=state.settings.total_steps-state.settings.preview_steps,
                          new_noise=False, image_reencoding=False, t2va_preserved=True,
                          total_wall_s=time.perf_counter()-start)
            return ContinueResult(video, final, report)
        finally:
            state._lock.release()
