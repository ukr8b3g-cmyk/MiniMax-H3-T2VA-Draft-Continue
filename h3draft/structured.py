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


def canonical_start_layout(layout):
    """Preserve semantic fields; remove only documented Canvas presentation data.

    Numbers are normalized without rounding coordinates. Overscan, transitions,
    and timelines are not silently folded into a START-only contract.
    """
    if type(layout) is not dict or layout.get("schema") != LAYOUT_SCHEMA:
        raise DraftError(f"Connect Canvas H3_LAYOUT with schema {LAYOUT_SCHEMA}.")
    for key in ("transition", "timeline_experimental", "timeline", "keyframes"):
        if layout.get(key) is not None:
            raise DraftError("Phase 3A audits START only. END/Multi-Key data must not be discarded; use a static Canvas layout.")
    # Image sidecars are already handled by the upstream native Reference path.
    clean = {k: v for k, v in layout.items() if k not in {"_h3_slot_images", "warnings"}}
    canvas = clean.get("canvas")
    boxes = clean.get("boxes")
    if type(canvas) is not dict or type(boxes) is not list:
        raise DraftError("H3_LAYOUT must contain canvas and boxes.")
    if (canvas.get("coordinate_space") != "normalized_0_1000" or
            canvas.get("bbox_format") != "xyxy"):
        raise DraftError("Phase 3A requires normalized_0_1000 xyxy BBOX coordinates; no implicit conversion.")
    for name in ("width", "height"):
        v = canvas.get(name)
        if type(v) not in (int, float) or not math.isfinite(v) or v != int(v) or not 32 <= v <= 16384:
            raise DraftError(f"Structured canvas {name} must be an integer from 32 to 16384.")
    if not 1 <= len(boxes) <= 3:
        raise DraftError("Phase 3A requires 1–3 START boxes in slots A/B/C.")
    clean["canvas"] = {k: v for k, v in canvas.items()
                       if k not in {"grid", "show_boxes", "active_slot", "aspect_ratio"}}
    seen = set()
    clean_boxes = []
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
            raise DraftError("START bbox_2d must be nonempty xyxy in [0,1000]; coordinates are not clamped.")
        # ui_color is a Canvas handle color, not the subject's visual identity.
        clean_boxes.append({k: v for k, v in box.items() if k != "ui_color"})
    clean["boxes"] = clean_boxes
    return _bounded(clean)


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
