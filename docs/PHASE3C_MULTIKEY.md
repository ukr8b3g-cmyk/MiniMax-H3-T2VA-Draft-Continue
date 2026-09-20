# Phase 3C — Multi-Key Timeline GPU Gate

Status: **GPU PASS** — 2026-09-20 JST.

## Scope

Phase 3C audits H3 Structured Canvas Timeline Experimental v4.

- START + up to 7 intermediate keys + END
- A/B/C independent tracks
- Duration 5.0–15.0 seconds
- normalized 0..1 key time
- Piecewise Linear
- offscreen overscan -1000..2000 supported
- Draft-Continue does not create or interpolate keys

## Report

`structured_layout.items[*]` includes:

- `scope = multi_key`
- `start_hash`
- `end_hash`
- `transition_hash`
- `timeline_hash`
- `keyframe_hash`
- `key_count`
- `key_times`
- `duration_seconds`

## GPU gate result

### M0 — Phase 3B regression

**PASS.**

Existing START→END behavior remained intact.

### M1 — one slot / three keys

**PASS.**

One-slot Multi-Key Preview → Continue → final media completed.

### M2 — two slots / three keys each

**PASS.**

A/B independent Multi-Key trajectories completed Preview → Continue → final media.

### M3 — maximum seven keys

**PASS.**

A one-slot trajectory with seven intermediate keys completed successfully.

### M4 — stale Key BBOX edit

**PASS.**

Changing an intermediate Key BBOX after Preview caused the old GO to be rejected before continuation.

### M5A — stale Key-time edit

**PASS.**

Changing a Key time after Preview caused the old GO to be rejected.

### M5B — stale Duration edit

**PASS.**

Changing Duration after Preview caused the old GO to be rejected.

### M6 — re-preview

**PASS.**

After the changed Key-time state was re-Previewed:

- the changed Key time was reflected in the new Preview state
- Continue resumed at `3/6`
- no new noise was introduced
- conditioning was not re-encoded
- schedule was not rebuilt
- final video save completed

## Duration / frame-grid observation

A 7.5-second timeline setting produced:

- 192 frames
- 8.0 seconds output

after H3-valid frame alignment.

This does not invalidate the gate: Phase 3C certifies that the reviewed Multi-Key/Duration contract is bound to the resumed Draft State. Exact frame-grid duration is governed by the H3-valid frame conversion upstream.

## Stability

- queue empty after tests
- no OOM
- no crash
- workflow not saved
- implementation code not modified during testing

Observed peak resource usage:

- system RAM: ~59.35 / 63.93 GiB
- VRAM: ~15.40 / 15.93 GiB

The gate passed, but resource headroom is limited and remains a production-hardening concern.

## Verdict

**Phase 3C Multi-Key Timeline GPU integration: PASS.**

Subjective path-following/motion quality was intentionally not graded and remains separate from the correctness verdict.
