# Phase 3D — Reference + BBOX / Multi-Key Combined Integration

Status: **PARTIAL** — 2026-09-20 JST.

## Purpose

Phase 3D qualifies Phase 2 Native Reference and Phase 3A–3C Structured Layout / Multi-Key when they are used together in the same Draft → Preview → GO → Continue path.

This phase does not introduce a new Reference format or a new BBOX compiler. It verifies that the existing native Reference contract and structured-layout contract coexist without being rewritten or losing stale-state protection.

## GPU/API results

Executed cases: **8/8 PASS**.

| Case | Configuration | Result |
| --- | --- | --- |
| D0 | No Reference; Slot A, 3 keys | PASS |
| D1 | Reference A; static START | PASS |
| D2 | Reference A; START→END | PASS |
| D3A | Reference A; Slot A, 3 keys | PASS |
| D3B | Reference A; Slot A, 7 keys; requested 7.5 s | PASS |
| D4A | References A+B; A/B each 3 keys | PASS |
| D4B | Sparse References A+C; A/C each 3 keys | PASS |
| D10 | References A+C; corrected per-slot Key-time change; re-Preview then Continue | PASS |

Every executed case completed Preview → Continue → saved video.

Verified common properties:

- same structured payload between Preview and Continue
- native Reference payload present and preserved
- resume at step 3
- `new_noise=false`
- conditioning re-encode false
- Reference re-encode false
- schedule rebuild false
- final queue empty

## Corrected D10

The first D10 fixture changed both A-K1 and C-K1 to 0.30 and is excluded from the verdict.

Corrected D10:

- A key times: `[0.30, 0.50, 0.75]`
- C key times: `[0.25, 0.50, 0.75]`
- A-K1 BBOX changed
- C keys unchanged
- two References remained present
- Reference payload matched between Preview and Continue
- Preview 96.731 s
- Continue 60.434 s
- Continue resumed at step 3 and completed final video

## Duration / frame-grid observation

D3B requested 7.5 seconds and produced:

- 192 frames
- 8.0 seconds

after H3-valid frame alignment.

## Resource observations

Maximum sampled usage:

- VRAM: **15,637 / 16,311 MiB**
- system RAM: **60.155 / 63.927 GiB**

No OOM, NaN, crash, or failed GPU execution occurred.

Resource headroom is limited and remains a production-hardening concern.

## Remaining browser stale-state gate

D5–D9 were not executed because Chrome blocked temporary local ComfyUI tabs with `ERR_BLOCKED_BY_CLIENT`.

Pending browser/UI cases:

- D5 — change Reference image after Preview; old GO must be rejected before Queue
- D6 — change Reference order after Preview; old GO must be rejected
- D7 — change START/END or intermediate-Key BBOX after Preview; old GO must be rejected
- D8 — change Key time or Duration after Preview; old GO must be rejected
- D9 — change compiled prompt after Preview; old GO must be rejected

The existing user ComfyUI tab/workflow was intentionally left untouched.

Direct API execution validates the server-side combined generation path, but it does not prove the requested frontend pre-queue stale-GO behavior.

## Quality boundary

Not graded in this gate:

- subjective identity retention
- exact BBOX placement
- exact Key-path fidelity
- crossing identity stability
- semantic Reference-to-person match

## Verdict

- GPU/API combined integration: **PASS**
- Browser stale-state rejection: **PENDING**
- Phase 3D overall: **PARTIAL**

Full Phase 3D PASS requires the remaining D5–D9 browser stale-state checks, or an explicitly equivalent browser/frontend gate.
