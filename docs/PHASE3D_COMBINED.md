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

## Browser stale-state gate

D5–D9: **PASS**.

The tests used a separate unsaved browser workflow tab. After a valid Preview, one approved input was changed and the existing GO control was used.

| Case | Mutation after Preview | Result |
| --- | --- | --- |
| D5 | Reference A image changed | stale GO rejected before Queue |
| D6 | Reference A/C assignments swapped | stale GO rejected before Queue |
| D7 | A-Key 1 BBOX changed | stale GO rejected before Queue |
| D8a | A-Key 1 time changed | stale GO rejected before Queue |
| D8b | Duration changed | stale GO rejected before Queue |
| D9 | scene/prompt text changed | stale GO rejected before Queue |

For every stale attempt:

- UI requested a new Preview
- no continuation request entered Queue
- running = 0
- pending = 0
- no Continue sampling started

Observed browser Preview-setup peaks:

- system RAM: ~59.98 / 63.93 GiB
- VRAM: ~15.42 / 15.93 GiB

No OOM or crash occurred.

## Browser valid-GO and saved-workflow reload

G11/G12: **PASS**.

G11 verified valid browser Preview → GO → Continue → Save on the combined Reference + Multi-Key workflow.

G12 verified the persistence boundary by saving the test workflow, closing its tab, reopening it, and confirming that approval state was reset. A fresh GPU Preview with a new seed was then generated, followed by a valid GO → Continue → Save.

Verified in both flows:

- two native References
- `scope=multi_key`
- six keys
- step-3 resume
- no new noise
- no conditioning re-encode
- no Reference re-encode
- no schedule rebuild
- successful saved video
- final queue empty

Observed peak across G11/G12:

- system RAM: ~60.62 / 63.93 GiB
- VRAM: ~15.39 / 15.93 GiB

No OOM, crash, or sampling error occurred.

## Remaining qualification

Still not verified:

- subjective identity/trajectory quality

## Quality boundary

Not graded in this gate:

- subjective identity retention
- exact BBOX placement
- exact Key-path fidelity
- crossing identity stability
- semantic Reference-to-person match

## Verdict

- GPU/API combined integration: **PASS**
- Browser stale-state rejection: **PASS (D5–D9)**
- Browser valid-GO/save/reload: **PASS (G11/G12)**
- Runtime/integration qualification: **PASS**
- Subjective visual quality: **NOT GRADED**
- Phase 3D overall: **PARTIAL (visual-quality gate only)**

All defined runtime/integration gates are now closed and PASS. Overall Phase 3D remains PARTIAL only because the separately defined subjective visual-quality gate has not been graded.
