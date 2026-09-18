"""Small, deterministic contracts shared by the runtime and CPU tests."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct
from typing import Any

FPS = 24
MAX_SEED = 2**53 - 1
MAX_STATE_BYTES = 512 * 1024 * 1024


class DraftError(RuntimeError):
    """An actionable user-facing failure; never silently changes the request."""


@dataclass(frozen=True)
class Settings:
    prompt: str
    seed: int = 1234
    width: int = 544
    height: int = 800
    duration_seconds: float = 5.0
    total_steps: int = 6
    preview_steps: int = 3
    sampler: str = "euler"
    scheduler: str = "simple"

    def validate(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip() or len(self.prompt) > 16000:
            raise DraftError("Prompt must contain 1–16000 characters. It is passed to H3 unchanged.")
        for name, lo, hi in (("seed", 0, MAX_SEED), ("width", 32, 2048),
                             ("height", 32, 2048), ("total_steps", 2, 100),
                             ("preview_steps", 1, 99)):
            value = getattr(self, name)
            if type(value) is not int or not lo <= value <= hi:
                raise DraftError(f"{name} must be an integer in [{lo}, {hi}].")
        if self.width % 32 or self.height % 32:
            raise DraftError("Width and height must be multiples of 32; no implicit crop or resize is used.")
        if self.preview_steps >= self.total_steps:
            raise DraftError("Preview steps must be less than Total steps, leaving at least one Continue step.")
        d = self.duration_seconds
        if isinstance(d, bool) or not isinstance(d, (float, int)) or not math.isfinite(d) or not 1 <= d <= 15:
            raise DraftError("Duration must be a finite number between 1 and 15 seconds.")
        if self.sampler != "euler" or self.scheduler != "simple":
            raise DraftError("V1 supports Euler / simple only. Multi-step solver history is not discarded or approximated.")

    @property
    def frame_count(self) -> int:
        requested = max(5, round(self.duration_seconds * FPS))
        return requested + (5 - requested % 17) % 17

    @property
    def video_t(self) -> int:
        return 2 + ((self.frame_count - 5) // 17) * 5

    @property
    def audio_t(self) -> int:
        return round(self.frame_count / FPS * 40)

    def manifest(self) -> dict:
        return {**asdict(self), "fps": FPS, "frame_count": self.frame_count,
                "actual_duration_seconds": self.frame_count / FPS,
                "cfg": 1.0, "denoise": 1.0, "mode": "t2va",
                "preview_frame": 0}


def canonical(value: Any) -> str:
    if value is None or isinstance(value, (str, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite numbers cannot enter a fingerprint.")
        return "n:" + struct.pack(">d", number if number else 0.0).hex()
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(str(k), ensure_ascii=False) + ":" + canonical(v)
                              for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))) + "}"
    raise TypeError(f"Unsupported fingerprint value: {type(value).__name__}")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def graph_branch(prompt: dict | None, root: str | int) -> dict:
    if not isinstance(prompt, dict) or str(root) not in prompt:
        return {}
    seen, active = {}, set()
    def visit(key):
        key = str(key)
        if key in active:
            raise DraftError("Workflow contains a dependency cycle.")
        if key in seen:
            return
        node = prompt.get(key)
        if not isinstance(node, dict) or "class_type" not in node:
            raise DraftError(f"Invalid upstream node: {key}.")
        active.add(key)
        inputs = node.get("inputs", {})
        for value in inputs.values():
            if (isinstance(value, list) and len(value) == 2 and
                    isinstance(value[0], str) and value[0] in prompt and type(value[1]) is int):
                visit(value[0])
        seen[key] = {"class_type": node["class_type"], "inputs": inputs}
        active.remove(key)
    visit(root)
    return seen


def graph_signature(prompt: dict | None, root: str | int) -> str:
    branch = graph_branch(prompt, root)
    return digest_json(branch) if branch else ""
