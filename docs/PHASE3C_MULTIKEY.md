# Phase 3C — Multi-Key Timeline GPU Gate

Status: implementation complete, host regression PASS, real H3 GPU validation pending.

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

Expected `structured_layout.items[*]` fields:

- `scope = multi_key`
- `start_hash`
- `end_hash`
- `transition_hash`
- `timeline_hash`
- `keyframe_hash`
- `key_count`
- `key_times`
- `duration_seconds`

## GPU gate

### M0 — Phase 3B regression
Run the already-passing START→END case. Expected: Preview → GO → final media.

### M1 — one slot / three keys
A only, keys at roughly 0.25 / 0.50 / 0.75.

Expected:
- Preview succeeds
- `scope = multi_key`
- `key_count = 3`
- GO succeeds
- final media succeeds

### M2 — two slots / three keys each
A/B with independent trajectories.

Expected:
- `key_count = 6`
- per-slot `key_times` present
- Preview → GO → final media succeeds

### M3 — maximum seven keys
Use one slot with 7 intermediate keys.

Expected:
- `key_count = 7`
- Preview → GO → final media succeeds

### M4 — stale Key edit
After Preview, change only one intermediate Key BBOX.

Expected:
- old GO rejected before Continue sampling
- no queued continuation

### M5 — stale Key-time or Duration edit
After Preview, change one Key time or Duration.

Expected:
- old GO rejected before Continue sampling

### M6 — re-preview
After M4/M5 change, create a fresh Preview and GO.

Expected:
- new State completes final media

## Pass condition

M0–M6 PASS establishes Phase 3C GPU integration PASS.

Subjective path-following/motion quality is recorded separately and is not required for the correctness PASS.
