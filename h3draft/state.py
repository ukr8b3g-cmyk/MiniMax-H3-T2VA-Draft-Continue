"""Immutable session-bound state, CPU tensor ownership and approval checks.

The AV payload is Core SamplerCustomAdvanced.output, NOT raw x_sigma or x0.
Core has already applied inverse_noise_scaling at the split boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import threading
import uuid
from typing import Any

import torch
from .contracts import DraftError, MAX_STATE_BYTES, Settings, digest_json

PROCESS_ID = uuid.uuid4().hex
SCHEMA = "h3_draft_state_v1"


def clone_cpu(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().to("cpu", copy=True).contiguous()
    if isinstance(value, dict):
        return {k: clone_cpu(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clone_cpu(v) for v in value]
    if isinstance(value, tuple):
        return tuple(clone_cpu(v) for v in value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise DraftError(f"Unsupported persistent conditioning value: {type(value).__name__}. V1 only supports native T2VA.")


def content_digest(value: Any) -> tuple[str, int]:
    h = hashlib.sha256()
    count = 0
    def add(v):
        nonlocal count
        if isinstance(v, torch.Tensor):
            if v.device.type != "cpu" or not bool(torch.isfinite(v).all()):
                raise DraftError("Draft tensors must be finite CPU tensors.")
            h.update(f"tensor:{v.dtype}:{tuple(v.shape)}:".encode())
            raw = v.detach().contiguous().reshape(-1).view(torch.uint8).numpy()
            h.update(memoryview(raw).cast("B"))
            count += v.numel() * v.element_size()
        elif isinstance(v, dict):
            h.update(b"dict[")
            for k in sorted(v):
                h.update(str(k).encode()); h.update(b":"); add(v[k])
            h.update(b"]")
        elif isinstance(v, (list, tuple)):
            h.update(b"sequence[")
            for x in v:
                add(x)
            h.update(b"]")
        else:
            h.update(digest_json(v).encode())
    add(value)
    return h.hexdigest(), count


def runtime_signature(model, clip, video_vae, audio_vae) -> str:
    """Object/patch identity only; does not hash weights, load models or query CUDA."""
    def version(t):
        try:
            return t._version
        except RuntimeError:
            return None
    def describe(v, depth=0):
        if v is None or isinstance(v, (str, bool, int, float)):
            return v
        if isinstance(v, torch.Tensor):
            return ["tensor", id(v), str(v.dtype), list(v.shape), version(v)]
        if depth < 8 and isinstance(v, dict):
            return {str(k): describe(x, depth+1) for k, x in sorted(v.items(), key=lambda p: str(p[0]))}
        if depth < 8 and isinstance(v, (list, tuple)):
            return [describe(x, depth+1) for x in v]
        return [type(v).__module__, type(v).__name__, id(v)]
    ms = model.get_model_object("model_sampling")
    return digest_json({
        "process": PROCESS_ID, "model": id(model.model),
        "patches_uuid": str(getattr(model, "patches_uuid", "unknown")),
        "patches": describe(getattr(model, "patches", {})),
        "object_patches": describe(getattr(model, "object_patches", {})),
        "model_options": describe(getattr(model, "model_options", {})),
        "sampling": {k: getattr(ms, k, None) for k in ("shift", "audio_shift", "noise_scale", "multiplier")},
        "clip": id(clip), "video_vae": id(video_vae), "audio_vae": id(audio_vae),
    })


def validate_av(parts, settings: Settings) -> None:
    expected = ((1, 24, settings.video_t, settings.height//16, settings.width//16),
                (1, 32, 2, settings.audio_t))
    if not isinstance(parts, (tuple, list)) or len(parts) != 2:
        raise DraftError("Expected both video and audio latent streams.")
    for name, tensor, shape in zip(("video", "audio"), parts, expected):
        if not isinstance(tensor, torch.Tensor) or tuple(tensor.shape) != shape:
            raise DraftError(f"Unexpected {name} latent shape: expected {shape}, got {getattr(tensor, 'shape', None)}.")
        if not tensor.is_floating_point() or not bool(torch.isfinite(tensor).all()):
            raise DraftError(f"{name} latent contains non-finite values or is not floating point.")


def validate_sigmas(sigmas: torch.Tensor, settings: Settings) -> None:
    if (not isinstance(sigmas, torch.Tensor) or sigmas.ndim != 1 or
            len(sigmas) != settings.total_steps+1 or not bool(torch.isfinite(sigmas).all()) or
            not bool((sigmas[:-1] > sigmas[1:]).all()) or float(sigmas[-1]) != 0 or
            not 0 < float(sigmas[settings.preview_steps]) < 1):
        raise DraftError("Invalid sigma schedule: need a strictly descending full schedule with a nonzero split and a final zero.")


@dataclass(frozen=True, eq=False)
class DraftState:
    settings: Settings
    model: Any = field(repr=False)
    clip: Any = field(repr=False)
    video_vae: Any = field(repr=False)
    audio_vae: Any = field(repr=False)
    av: tuple = field(repr=False)
    conditioning: list = field(repr=False)
    sigmas: torch.Tensor = field(repr=False)
    preview: torch.Tensor = field(repr=False)
    graph_hash: str
    runtime_hash: str
    payload_hash: str
    storage_bytes: int
    source_node_id: str
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    process_id: str = PROCESS_ID
    schema: str = SCHEMA
    _lock: Any = field(default_factory=threading.Lock, repr=False, compare=False)

    @classmethod
    def create(cls, settings, model, clip, video_vae, audio_vae, av, conditioning,
               sigmas, preview, graph_hash="", source_node_id=""):
        settings.validate(); validate_av(av, settings); validate_sigmas(sigmas, settings)
        if tuple(preview.shape) != (1, settings.height, settings.width, 3):
            raise DraftError("Preview must be exactly one RGB image matching the canvas.")
        av, cond, schedule, image = clone_cpu(tuple(av)), clone_cpu(conditioning), clone_cpu(sigmas), clone_cpu(preview)
        digest, size = content_digest((av, cond, schedule, image, settings.manifest(), graph_hash))
        if size > MAX_STATE_BYTES:
            raise DraftError(f"Draft state exceeds the {MAX_STATE_BYTES//1024**2} MiB safety limit. Reduce resolution or duration.")
        return cls(settings, model, clip, video_vae, audio_vae, av, cond, schedule, image,
                   graph_hash, runtime_signature(model, clip, video_vae, audio_vae),
                   digest, size, str(source_node_id))

    def verify(self, approval: str, request_hash: str = "") -> None:
        if self.schema != SCHEMA or self.process_id != PROCESS_ID:
            raise DraftError("Draft is from another backend session/schema. Generate a new Preview.")
        if not approval or approval != self.state_id:
            raise DraftError("This draft has not been reviewed. Preview again, then press GO for that exact draft. The cached state may have expired.")
        if request_hash and self.graph_hash and request_hash != self.graph_hash:
            raise DraftError("Prompt, model, LoRA or another upstream setting changed after Preview. Generate a new Preview.")
        if runtime_signature(self.model, self.clip, self.video_vae, self.audio_vae) != self.runtime_hash:
            raise DraftError("Model/LoRA/runtime changed after Preview. Generate a new Preview; no model substitution was performed.")
        if content_digest((self.av, self.conditioning, self.sigmas, self.preview,
                           self.settings.manifest(), self.graph_hash))[0] != self.payload_hash:
            raise DraftError("Draft payload was modified. Generate a new Preview.")
        validate_av(self.av, self.settings); validate_sigmas(self.sigmas, self.settings)

    def summary(self) -> dict:
        return {"schema": self.schema, "state_id": self.state_id, "source_node_id": self.source_node_id,
                "process_scope": "current_backend_session_only", "graph_hash": self.graph_hash,
                "settings": self.settings.manifest(), "payload_sha256": self.payload_hash,
                "storage_bytes": self.storage_bytes, "video_shape": list(self.av[0].shape),
                "audio_shape": list(self.av[1].shape), "current_step": self.settings.preview_steps,
                "current_sigma": float(self.sigmas[self.settings.preview_steps]),
                "remaining_steps": self.settings.total_steps-self.settings.preview_steps,
                "boundary_format": "comfy_sampler_output_inverse_noise_scaled",
                "models_residency": "managed_by_ComfyUI_not_pinned_by_this_extension"}
