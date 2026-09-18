"""Session-bound, externally conditioned H3 sampler state.

Unlike the legacy Settings state, this contract derives geometry from the input
AV latent and never rebuilds conditioning, noise or a sigma schedule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
import math
import threading
import uuid
from typing import Any

import torch
from .contracts import DraftError, MAX_STATE_BYTES, digest_json
from .state import PROCESS_ID, content_digest, runtime_signature

SAMPLER_SCHEMA = "h3_sampler_draft_state_v1"


def freeze(value: Any, label: str) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().to("cpu", copy=True).contiguous()
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise DraftError(f"{label} must use string dictionary keys.")
        return {k: freeze(v, f"{label}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [freeze(v, label) for v in value]
    if isinstance(value, tuple):
        return tuple(freeze(v, label) for v in value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise DraftError(
        f"{label} contains a live custom object which cannot be snapshotted safely. "
        "Use native tensor-based CONDITIONING/LATENT (including H3 references or keyframes). "
        "Live ControlNet/hook objects need a dedicated adapter; they are not silently dropped."
    )


def payload_digest(value: Any) -> tuple[str, int]:
    def project(v):
        if isinstance(v, uuid.UUID):
            return ("runtime_uuid", v.hex)
        if isinstance(v, dict):
            return ("dict", {k: project(x) for k, x in v.items()})
        if isinstance(v, list):
            return ("list", [project(x) for x in v])
        if isinstance(v, tuple):
            return ("tuple", [project(x) for x in v])
        return v
    return content_digest(project(value))


def sampler_signature(sampler) -> str:
    fn = getattr(sampler, "sampler_function", None)
    return digest_json({
        "type": [type(sampler).__module__, type(sampler).__name__],
        "function": [getattr(fn, "__module__", ""), getattr(fn, "__name__", ""), id(fn)],
        "extra_options": getattr(sampler, "extra_options", {}),
        "inpaint_options": getattr(sampler, "inpaint_options", {}),
    })


def guider_parameters(guider) -> dict:
    result = {}
    for name in ("cfg", "cfg1", "cfg2", "nested"):
        if not hasattr(guider, name):
            continue
        value = getattr(guider, name)
        if name == "nested":
            if type(value) is not bool:
                raise DraftError("GUIDER nested must be boolean.")
        elif type(value) not in (int, float) or not math.isfinite(value):
            raise DraftError(f"GUIDER {name} must be finite.")
        result[name] = value
    return result


def input_signature(latent, sigmas, noise) -> str:
    samples = latent.get("samples")
    if not getattr(samples, "is_nested", False):
        raise DraftError("The upstream LATENT changed format after Preview.")
    metadata = {k:v for k,v in latent.items() if k != "samples"}
    return payload_digest((freeze(tuple(samples.unbind()), "Upstream AV latent"),
        freeze(metadata, "Upstream LATENT metadata"), freeze(sigmas, "Upstream SIGMAS"),
        type(noise).__module__, type(noise).__name__, getattr(noise, "seed", None)))[0]


def guider_signature(guider, vae) -> str:
    cond, _ = payload_digest(freeze(guider.original_conds, "GUIDER conditioning"))
    model_view = copy.copy(guider.model_patcher)
    model_view.model_options = guider.model_options
    return digest_json({
        "type": [type(guider).__module__, type(guider).__name__],
        "model": runtime_signature(model_view, None, vae, None),
        "parameters": guider_parameters(guider), "conditioning": cond,
    })


def native_geometry(av: tuple) -> dict:
    if not isinstance(av, (tuple, list)) or len(av) != 2:
        raise DraftError("Expected H3 joint video + audio LATENT, not an image or video-only latent.")
    v, a = av
    if not isinstance(v, torch.Tensor) or v.ndim != 5 or v.shape[0] != 1 or v.shape[1] != 24:
        raise DraftError("Video LATENT must have shape [1,24,T,H/16,W/16] (native MiniMax H3).")
    t, h, w = v.shape[2:]
    if t < 2 or (t - 2) % 5 or h < 2 or w < 2 or h % 2 or w % 2:
        raise DraftError("Invalid H3 latent geometry: temporal T=5k+2 and spatial dimensions must be even.")
    frames = 5 + (t - 2) // 5 * 17
    audio_t = round(frames / 24 * 40)
    if not isinstance(a, torch.Tensor) or tuple(a.shape) != (1, 32, 2, audio_t):
        raise DraftError(f"Audio LATENT must match the full video length: expected [1,32,2,{audio_t}].")
    for label, tensor in (("video", v), ("audio", a)):
        if not tensor.is_floating_point() or not bool(torch.isfinite(tensor).all()):
            raise DraftError(f"{label} LATENT must be finite and floating point.")
    if sum(x.numel() * x.element_size() for x in av) > MAX_STATE_BYTES:
        raise DraftError("Input AV latent exceeds the 512 MiB state budget.")
    return {"width": w * 16, "height": h * 16, "frame_count": frames,
            "video_t": t, "audio_t": audio_t, "fps": 24,
            "actual_duration_seconds": frames / 24, "batch_size": 1}


def external_sigmas(sigmas, preview_steps: int) -> None:
    if (not isinstance(sigmas, torch.Tensor) or sigmas.ndim != 1 or
            not sigmas.is_floating_point() or not 3 <= len(sigmas) <= 1001 or
            not bool(torch.isfinite(sigmas).all()) or
            not bool((sigmas[:-1] > sigmas[1:]).all()) or
            float(sigmas[-1]) != 0.0 or float(sigmas[0]) > 1.0):
        raise DraftError("SIGMAS must be a finite, strictly descending H3 flow schedule in [0,1], ending at zero. No schedule is rebuilt.")
    if type(preview_steps) is not int or not 1 <= preview_steps < len(sigmas)-1:
        raise DraftError("preview_steps must leave at least one transition for Continue.")
    if not 0.0 < float(sigmas[preview_steps]) < 1.0:
        raise DraftError("The split sigma must be strictly between zero and one.")


@dataclass(frozen=True, eq=False)
class SamplerDraftState:
    guider: Any = field(repr=False)
    sampler: Any = field(repr=False)
    video_vae: Any = field(repr=False)
    av: tuple = field(repr=False)
    latent_metadata: dict = field(repr=False)
    sigmas: torch.Tensor = field(repr=False)
    preview: torch.Tensor = field(repr=False)
    seed: int
    preview_steps: int
    graph_hash: str
    source_node_id: str
    payload_hash: str
    storage_bytes: int
    runtime_hash: str
    sampler_hash: str
    source_guider: Any = field(repr=False)
    source_sampler: Any = field(repr=False)
    source_guider_hash: str
    source_sampler_hash: str
    source_latent: Any = field(repr=False)
    source_sigmas: Any = field(repr=False)
    source_noise: Any = field(repr=False)
    source_inputs_hash: str
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    process_id: str = PROCESS_ID
    schema: str = SAMPLER_SCHEMA
    _lock: Any = field(default_factory=threading.Lock, repr=False, compare=False)

    @classmethod
    def create(cls, guider, sampler, video_vae, av, metadata, sigmas, preview,
               seed, preview_steps, graph_hash, source_node_id, source_guider, source_sampler,
               source_latent, source_sigmas, source_noise):
        g = native_geometry(av)
        external_sigmas(sigmas, preview_steps)
        if tuple(preview.shape) != (1, g["height"], g["width"], 3):
            raise DraftError("Preview must contain exactly Frame 0 at the input latent resolution.")
        av = freeze(tuple(av), "AV state")
        metadata = freeze(metadata, "LATENT metadata")
        sigmas, preview = freeze(sigmas, "SIGMAS"), freeze(preview, "Preview")
        payload = (av, metadata, sigmas, preview, guider.original_conds,
                   guider_parameters(guider), seed, preview_steps, graph_hash)
        hashed, size = payload_digest(payload)
        if size > MAX_STATE_BYTES:
            raise DraftError("Draft including conditioning exceeds 512 MiB. Reduce resolution, duration or references.")
        return cls(guider, sampler, video_vae, av, metadata, sigmas, preview, seed,
                   preview_steps, graph_hash, str(source_node_id), hashed, size,
                   runtime_signature(guider.model_patcher, None, video_vae, None),
                   sampler_signature(sampler), source_guider, source_sampler,
                   guider_signature(source_guider, video_vae), sampler_signature(source_sampler),
                   source_latent, source_sigmas, source_noise,
                   input_signature(source_latent, source_sigmas, source_noise))

    def fresh_guider(self):
        out = copy.copy(self.guider)
        out.model_patcher = self.guider.model_patcher.clone()
        out.model_options = out.model_patcher.model_options
        out.original_conds = freeze(self.guider.original_conds, "Stored conditioning")
        for name in ("conds", "inner_model", "loaded_models"):
            out.__dict__.pop(name, None)
        return out

    def verify(self, approval: str, request_hash: str = "") -> None:
        if self.schema != SAMPLER_SCHEMA or self.process_id != PROCESS_ID:
            raise DraftError("Draft belongs to another backend session/schema. Preview again.")
        if not approval or approval != self.state_id:
            raise DraftError("This sampler draft has not been reviewed. Preview again and GO for that exact State ID.")
        if request_hash and self.graph_hash and request_hash != self.graph_hash:
            raise DraftError("An upstream workflow setting changed. Preview again before GO.")
        if runtime_signature(self.guider.model_patcher, None, self.video_vae, None) != self.runtime_hash:
            raise DraftError("Stored model/LoRA/runtime changed. Preview again.")
        if (guider_signature(self.source_guider, self.video_vae) != self.source_guider_hash or
                sampler_signature(self.source_sampler) != self.source_sampler_hash or
                sampler_signature(self.sampler) != self.sampler_hash):
            raise DraftError("External GUIDER/SAMPLER or its conditioning changed. Preview again.")
        if input_signature(self.source_latent, self.source_sigmas, self.source_noise) != self.source_inputs_hash:
            raise DraftError("External LATENT/SIGMAS/NOISE changed after Preview. Generate a new Preview.")
        actual, _ = payload_digest((self.av, self.latent_metadata, self.sigmas, self.preview,
            self.guider.original_conds, guider_parameters(self.guider), self.seed,
            self.preview_steps, self.graph_hash))
        if actual != self.payload_hash:
            raise DraftError("Sampler Draft payload was modified. Preview again.")
        native_geometry(self.av)
        external_sigmas(self.sigmas, self.preview_steps)

    def summary(self) -> dict:
        g = native_geometry(self.av)
        total = len(self.sigmas)-1
        return {"schema": self.schema, "state_id": self.state_id,
                "source_node_id": self.source_node_id, "graph_hash": self.graph_hash,
                "process_scope": "current_backend_session_only", "payload_sha256": self.payload_hash,
                "storage_bytes": self.storage_bytes, "current_step": self.preview_steps,
                "current_sigma": float(self.sigmas[self.preview_steps]),
                "remaining_steps": total-self.preview_steps,
                "video_shape": list(self.av[0].shape), "audio_shape": list(self.av[1].shape),
                "settings": {**g, "seed": self.seed, "total_steps": total,
                    "preview_steps": self.preview_steps, "sampler": "euler",
                    "scheduler": "external_SIGMAS_unchanged", **guider_parameters(self.guider)},
                "boundary_format": "comfy_sampler_output_inverse_noise_scaled",
                "conditioning_source": "external_GUIDER_unchanged",
                "models_residency": "managed_by_ComfyUI_not_pinned_by_this_extension"}
