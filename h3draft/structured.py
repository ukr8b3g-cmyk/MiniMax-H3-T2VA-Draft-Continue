"""Optional START-layout audit metadata; never compiles prompts or touches tensors.

Provider contract audited at H3-Structured-Canvas 46c86f9. The layout compiler
stays upstream. This module has no Canvas or ComfyUI import dependency.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from .contracts import DraftError, digest_json

KEY = "h3_structured_source"
SCHEMA = "h3_draft_structured_source/1"
LAYOUT_SCHEMA = "h3_structured_canvas/0.9"
PROVIDER = "H3-Structured-Canvas"
MAX_TEXT = 128_000
MAX_METADATA_BYTES = 512_000
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _json_data(value, depth=0):
    """Bounded, detached primitive copy. No live IMAGE/model objects allowed."""
    if depth > 12:
        raise DraftError("Structured metadata is too deeply nested.")
    if value is None or type(value) is bool:
        return value
    if type(value) is str:
        if len(value) > MAX_TEXT:
            raise DraftError("Structured metadata text exceeds the safety limit.")
        return value
    if type(value) in (int, float):
        if abs(value) > 2**53 - 1 or not math.isfinite(value):
            raise DraftError("Structured metadata needs finite, precisely representable numbers.")
        return 0 if value == 0 else (int(value) if float(value).is_integer() else value)
    if type(value) is list:
        if len(value) > 1024:
            raise DraftError("Structured metadata contains too many items.")
        return [_json_data(v, depth + 1) for v in value]
    if type(value) is dict:
        if len(value) > 128 or not all(type(k) is str and len(k) <= 128 for k in value):
            raise DraftError("Structured metadata must use bounded string keys.")
        return {k: _json_data(v, depth + 1) for k, v in value.items()}
    raise DraftError("Structured audit metadata must be primitive JSON data, not live objects.")


def _bounded(value):
    out = _json_data(value)
    try:
        size = len(json.dumps(out, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except UnicodeError as exc:
        raise DraftError("Structured metadata contains invalid Unicode.") from exc
    if size > MAX_METADATA_BYTES:
        raise DraftError("Structured audit metadata exceeds 512 kB.")
    return out


def _semantic_canvas(canvas, label="Structured canvas"):
    if type(canvas) is not dict:
        raise DraftError(f"{label} must be a dictionary.")
    out = _json_data({k: v for k, v in canvas.items()
                      if k not in {"grid", "show_boxes", "active_slot", "aspect_ratio"}})
    if (out.get("coordinate_space") != "normalized_0_1000" or
            out.get("bbox_format") != "xyxy"):
        raise DraftError(
            f"{label} requires normalized_0_1000 xyxy coordinates; no implicit conversion."
        )
    for name in ("width", "height"):
        value = out.get(name)
        if (type(value) not in (int, float) or not math.isfinite(value) or
                value != int(value) or not 32 <= value <= 16384):
            raise DraftError(f"{label} {name} must be an integer from 32 to 16384.")
        out[name] = int(value)
    return out


def _canonical_start_boxes(boxes):
    if type(boxes) is not list or not 1 <= len(boxes) <= 3:
        raise DraftError("Structured layout requires 1–3 START boxes in slots A/B/C.")
    seen = set()
    result = []
    for box in boxes:
        if type(box) is not dict or box.get("slot") not in ("a", "b", "c"):
            raise DraftError("START boxes must use Canvas slots a, b or c.")
        slot = box["slot"]
        if slot in seen:
            raise DraftError("Duplicate START slot; fix the upstream Canvas.")
        seen.add(slot)
        coords = box.get("bbox_2d")
        if (type(coords) is not list or len(coords) != 4 or
                any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1000 for v in coords) or
                not (coords[0] < coords[2] and coords[1] < coords[3])):
            raise DraftError(
                "START bbox_2d must be nonempty xyxy in [0,1000]; coordinates are not clamped."
            )
        result.append(_json_data({k: v for k, v in box.items() if k != "ui_color"}))
    return result


def _canonical_end_boxes(boxes, start_boxes):
    if type(boxes) is not list:
        raise DraftError("Structured transition end_boxes must be a list.")
    start_slots = [box["slot"] for box in start_boxes]
    by_slot = {}
    for box in boxes:
        if type(box) is not dict or box.get("slot") not in ("a", "b", "c"):
            raise DraftError("END boxes must use Canvas slots a, b or c.")
        slot = box["slot"]
        if slot in by_slot:
            raise DraftError("Duplicate END slot; fix the upstream Canvas.")
        coords = box.get("bbox_2d")
        if (type(coords) is not list or len(coords) != 4 or
                any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1000 for v in coords) or
                not (coords[0] < coords[2] and coords[1] < coords[3])):
            raise DraftError(
                "END bbox_2d must be nonempty xyxy in [0,1000]; coordinates are not clamped."
            )
        # The provider compiler consumes END geometry by slot. UI color and
        # unrelated START semantic annotations are intentionally not invented.
        by_slot[slot] = {"slot": slot, "bbox_2d": _json_data(coords)}
    if set(by_slot) != set(start_slots):
        raise DraftError(
            "Phase 3B requires the same A/B/C slot set at START and END so identity is unambiguous."
        )
    return [by_slot[slot] for slot in start_slots]


def _keyframes_are_empty(value):
    if value is None or value == {}:
        return True
    if type(value) is not dict:
        return False
    return all(type(items) is list and not items for items in value.values())


def _validate_start_end_timeline_shell(timeline):
    """Validate known Timeline Experimental wrapper fields, without adopting keys."""
    if timeline is None:
        return
    if type(timeline) is not dict:
        raise DraftError("timeline_experimental must be a dictionary.")
    allowed = {
        "version", "slots", "duration_seconds", "interpolation",
        "canonical_time", "mid_time", "mid_boxes", "coordinate_space",
        "max_intermediate_keys", "keyframes",
    }
    if not set(timeline) <= allowed:
        raise DraftError(
            "Phase 3B cannot discard unknown Timeline Experimental metadata."
        )
    version = timeline.get("version")
    if version not in (3, 4):
        raise DraftError(
            "Phase 3B accepts only known Timeline Experimental v3/v4 START→END wrappers."
        )
    if timeline.get("interpolation", "piecewise_linear") != "piecewise_linear":
        raise DraftError("Phase 3B requires piecewise_linear START→END interpolation.")
    if timeline.get("canonical_time", "normalized_0_1") != "normalized_0_1":
        raise DraftError("Phase 3B requires normalized_0_1 timeline time.")
    if timeline.get("mid_boxes") not in (None, []):
        raise DraftError(
            "Phase 3B audits START→END only. Explicit MID data requires the Multi-Key phase."
        )
    if not _keyframes_are_empty(timeline.get("keyframes")):
        raise DraftError(
            "Phase 3B audits START→END only. Multi-Key data requires the Multi-Key phase."
        )
    duration = timeline.get("duration_seconds")
    if duration is not None and (
            type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0):
        raise DraftError("Timeline duration_seconds must be finite and positive.")


def canonical_layout(layout):
    """Canonical Phase 3A/3B IR.

    Static/no-op Timeline Experimental wrappers collapse to the original START
    IR. A real START→END transition is retained as model-facing geometry.
    Explicit MID/Multi-Key semantics remain fail-closed for Phase 3C.
    """
    if type(layout) is not dict or layout.get("schema") != LAYOUT_SCHEMA:
        raise DraftError(f"Connect Canvas H3_LAYOUT with schema {LAYOUT_SCHEMA}.")
    if layout.get("timeline") is not None or layout.get("keyframes") is not None:
        raise DraftError(
            "Phase 3B does not accept top-level timeline/keyframes; use the Multi-Key phase."
        )

    clean = {k: v for k, v in layout.items()
             if k not in {"_h3_slot_images", "warnings", "transition", "timeline_experimental"}}
    start_canvas = _semantic_canvas(layout.get("canvas"), "Structured START canvas")
    start_boxes = _canonical_start_boxes(layout.get("boxes"))
    clean["canvas"] = start_canvas
    clean["boxes"] = start_boxes

    transition = layout.get("transition")
    timeline = layout.get("timeline_experimental")
    _validate_start_end_timeline_shell(timeline)

    if timeline is not None and transition is None:
        raise DraftError(
            "Timeline Experimental metadata is present without transition END data."
        )
    if transition is None:
        return _bounded(clean)
    if type(transition) is not dict or set(transition) != {"end_canvas", "end_boxes"}:
        raise DraftError(
            "Phase 3B requires transition with exactly end_canvas and end_boxes."
        )

    end_canvas = _semantic_canvas(transition.get("end_canvas"), "Structured END canvas")
    if end_canvas != start_canvas:
        raise DraftError(
            "Phase 3B keeps one fixed H3 canvas. START and END canvas geometry must match."
        )
    end_boxes = _canonical_end_boxes(transition.get("end_boxes"), start_boxes)

    start_geometry = {box["slot"]: box["bbox_2d"] for box in start_boxes}
    end_geometry = {box["slot"]: box["bbox_2d"] for box in end_boxes}
    moved = [slot for slot in start_geometry if start_geometry[slot] != end_geometry[slot]]
    if not moved:
        # Timeline Experimental auto-wraps static Canvas state. Preserve exact
        # Phase 3A canonical hash for that semantic no-op.
        return _bounded(clean)

    clean["transition"] = {
        "end_canvas": end_canvas,
        "end_boxes": end_boxes,
    }
    return _bounded(clean)


def canonical_start_layout(layout):
    """Backward-compatible public name; now also retains Phase 3B START→END IR."""
    return canonical_layout(layout)

def make_source(layout, compiled_prompt):
    ir = canonical_start_layout(layout)
    if type(compiled_prompt) is not str or not compiled_prompt.strip() or len(compiled_prompt) > MAX_TEXT:
        raise DraftError("Connect the exact nonempty Prompter output (up to 128000 characters).")
    try:
        prompt_hash = hashlib.sha256(compiled_prompt.encode("utf-8")).hexdigest()
    except UnicodeError as exc:
        raise DraftError("Compiled prompt contains invalid Unicode.") from exc
    return _bounded({"schema": SCHEMA, "provider": PROVIDER, "layout_schema": LAYOUT_SCHEMA,
                     "scope": "start", "ir": ir, "ir_hash": digest_json(ir),
                     "compiled_prompt": compiled_prompt, "prompt_hash": prompt_hash})


def validate_source(source):
    data = _bounded(source)
    fields = {"schema", "provider", "layout_schema", "scope", "ir", "ir_hash", "compiled_prompt", "prompt_hash"}
    if (type(data) is not dict or set(data) != fields or data.get("schema") != SCHEMA or
            data.get("provider") != PROVIDER or data.get("layout_schema") != LAYOUT_SCHEMA or
            data.get("scope") != "start"):
        raise DraftError("Unsupported structured-source metadata contract; no fields were silently dropped.")
    for key in ("ir_hash", "prompt_hash"):
        if type(data[key]) is not str or not _HEX.fullmatch(data[key]):
            raise DraftError(f"Invalid structured {key}.")
    expected = make_source(data["ir"], data["compiled_prompt"])
    if digest_json(data) != digest_json(expected):
        raise DraftError("Structured layout or prompt hash does not match its payload.")
    return expected


def attach_source(positive, layout, compiled_prompt):
    """Shallow copy only metadata; every conditioning/reference tensor is unchanged."""
    source = make_source(layout, compiled_prompt)
    if type(positive) is not list or not positive:
        raise DraftError("Connect nonempty native CONDITIONING before the Layout Audit node.")
    result = []
    for entry in positive:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2 or type(entry[1]) is not dict:
            raise DraftError("Expected native CONDITIONING [tensor, metadata] entries.")
        meta = entry[1].copy()
        if KEY in meta and digest_json(validate_source(meta[KEY])) != digest_json(source):
            raise DraftError("Conditioning already has a different layout audit. Rebuild it upstream.")
        meta[KEY] = _json_data(source)
        result.append([entry[0], meta])
    return result


def structured_manifest(conds, geometry=None):
    """Read optional audit data in converted Core GUIDER conditions, not model_conds."""
    if type(conds) is not dict:
        raise DraftError("GUIDER conditioning must be a dictionary.")
    items = []
    for branch, entries in sorted(conds.items()):
        if not isinstance(entries, list):
            continue
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict) or KEY not in entry:
                continue
            src = validate_source(entry[KEY])
            canvas = src["ir"]["canvas"]
            if geometry is not None and any(canvas[k] != geometry[k] for k in ("width", "height")):
                raise DraftError("Structured Canvas size differs from the AV latent. Connect Canvas width/height upstream; no implicit resize.")
            items.append({"conditioning": branch, "conditioning_index": i,
                          "provider": src["provider"], "schema": src["layout_schema"], "scope": "start",
                          "ir_hash": src["ir_hash"], "prompt_hash": src["prompt_hash"],
                          "slot_count": len(src["ir"]["boxes"]),
                          "slots": [b["slot"] for b in src["ir"]["boxes"]]})
    return {"present": bool(items), "contract": SCHEMA, "items": items,
            "payload_sha256": digest_json(items), "conditioning_reencoded": False,
            "semantic_accuracy_verified": False, "prompt_binding_verified": False}


def verify_structured_pair(stored, current):
    a = structured_manifest(stored)
    b = structured_manifest(current)
    if a["payload_sha256"] != b["payload_sha256"]:
        raise DraftError("Structured layout changed after Preview. Generate a new Preview before GO.")
    return a
