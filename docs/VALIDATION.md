# Validation

Date: 2026-09-20.

## Confirmed GPU evidence

User-confirmed real ComfyUI/H3 passes:

- Phase 0 concept: Preview 3/6 → Continue 3/6 → final video
- Phase 1 generic Sampler-level integration
- Core loader identity fix
- Phase 2 Native Reference Transparency
- Phase 3A static START structured-layout audit, including Timeline Experimental no-op wrapper compatibility
- Phase 3A final video generation
- Phase 3B START→END structured-layout integration gate T0–T4
- Phase 3C Multi-Key Timeline integration gate M0–M6

These are real-device execution results. Visual placement and motion quality remain model-dependent and are not converted into a numeric quality certification.

## Phase 3B GPU PASS

Environment:

- backend: `http://127.0.0.6:8188`
- repository HEAD: `97243bd`
- GPU: NVIDIA GeForce RTX 5060 Ti 16 GB
- date: 2026-09-19 JST

Gate result: **T0–T4 PASS** for integration/correctness.

Key verified properties:

- static START regression preserved
- one/two moving-slot START→END continuation completed
- stale END change rejected before Continue sampling
- new Preview after END change completed
- resume started from step 3
- no new noise
- no conditioning re-encode
- no schedule rebuild
- final video/audio created successfully

T1/T2 validated the server-side START→END path using prompt payloads derived from the repository v1.4 START-END example; they were not browser-loaded workflow runs.

Observed T0 peak:

- VRAM: ~15,122 MiB
- system RAM: ~62.31 GiB / ~63.93 GiB total

System RAM headroom was tight even though the gate passed.

## Phase 3C GPU PASS

Date: 2026-09-20 JST.

Gate result: **M0–M6 PASS** for integration/correctness.

Verified:

- M0: Phase 3B regression completed
- M1: one-slot Multi-Key Preview → Continue → final media
- M2: two-slot independent Multi-Key Preview → Continue → final media
- M3: maximum seven intermediate keys completed
- M4: changing an intermediate Key BBOX after Preview rejected the old GO
- M5A: changing a Key time after Preview rejected the old GO
- M5B: changing Duration after Preview rejected the old GO
- M6: after re-Preview, the changed Key-time state completed Continue and video save

M6-specific evidence:

- changed Key time was reflected in the new Preview state
- Continue resumed at `3/6`
- no new noise
- no conditioning re-encode
- no schedule rebuild
- final video saved successfully

Duration/frame-grid note:

- configured Duration: 7.5 seconds
- H3 frame-grid aligned result: 192 frames / 8.0 seconds

This is expected from the H3-valid frame alignment used by the workflow. Phase 3C therefore certifies the structured timeline state binding, not exact unrounded wall-clock duration.

Stability:

- queue empty after the gate
- no OOM
- no crash
- no workflow save
- no implementation-code modification during the GPU test

Observed Phase 3C peaks:

- system RAM: ~59.35 / 63.93 GiB
- VRAM: ~15.40 / 15.93 GiB

Both passed without OOM, but remaining resource headroom is small and should remain a production-hardening concern.

## Phase 3D combined Reference + Structured integration — PARTIAL

Date: 2026-09-20 JST.

Overall status: **PARTIAL**.

GPU/API integration matrix: **PASS (8/8 executed cases)**.

Executed successfully:

- D0: no native Reference + Multi-Key baseline
- D1: one native Reference + static START
- D2: one native Reference + START→END
- D3A: one native Reference + one-slot / three-key Multi-Key
- D3B: one native Reference + one-slot / seven-key Multi-Key at requested 7.5 s
- D4A: two References A+B + two-slot Multi-Key
- D4B: sparse References A+C (B unconnected) + A/C Multi-Key
- D10: corrected re-preview run with A-K1 time changed to 0.30 while C-K1 remained 0.25

All executed GPU/API cases:

- completed Preview → Continue → saved video
- preserved identical structured payloads between Preview and Continue
- resumed at step 3
- introduced no new noise
- did not re-encode conditioning
- did not re-encode Reference
- did not rebuild the schedule
- completed with an empty final queue

D10 correction note:

- the first D10 fixture unintentionally changed both A-K1 and C-K1 to 0.30
- that run was excluded from verdicts
- corrected D10 used A key times `[0.30, 0.50, 0.75]` and C key times `[0.25, 0.50, 0.75]`
- corrected D10 passed Preview → Continue → final video

D3B duration/frame-grid observation:

- requested timeline duration: 7.5 s
- H3-valid aligned output: 192 frames / 8.0 s

Resource peaks:

- VRAM: 15,637 / 16,311 MiB
- system RAM: 60.155 / 63.927 GiB

No OOM, NaN, crash, or failed GPU execution occurred.

### Browser stale-state gate D5–D9

**PASS.**

Using a separate unsaved browser workflow tab, each approved input was mutated after Preview and the existing GO control was pressed.

Verified cases:

- D5: Reference A image changed → stale GO rejected
- D6: Reference A/C assignments swapped → stale GO rejected
- D7: A-Key 1 BBOX changed → stale GO rejected
- D8a: A-Key 1 time changed 1.25 s → 1.50 s → stale GO rejected
- D8b: Duration changed 5.0 s → 6.0 s → stale GO rejected
- D9: scene/prompt text changed → stale GO rejected

For every case:

- UI required a new Preview before GO
- request was not queued
- `queue_running=[]`
- `queue_pending=[]`
- no continuation sampling started

Observed browser Preview-setup peaks:

- system RAM: ~59.98 / 63.93 GiB
- VRAM: ~15.42 / 15.93 GiB

No OOM or crash occurred.

### Browser valid-GO / saved-workflow reload G11–G12

**PASS.**

G11 verified a normal browser Preview → GO → Continue → Save path using the combined Reference + Multi-Key workflow:

- 512 × 768, 124 frames, 24 fps
- two native References (A and C)
- `scope = multi_key`
- six total keys
- Preview ready at 3/6
- Continue resumed from step 3
- `new_noise=false`
- `conditioning_reencoded=false`
- `reference_reencoded=false`
- `schedule_rebuilt=false`
- final video saved successfully

G12 then saved the test workflow, closed its tab, reopened it from the workflow list, and verified the persistence boundary:

- saved workflow reopened successfully
- approval/runtime state was not restored
- UI required a new Preview
- a fresh GPU Preview with a new seed completed
- new approval was accepted
- GO → Continue → Save completed successfully

Highest observed across G11/G12:

- system RAM: ~60.62 / 63.93 GiB
- VRAM: ~15.39 / 15.93 GiB

No OOM, crash, or sampling error occurred. Final queue was 0 running / 0 pending.

### Phase 3D visual-quality gate

**PASS — user-confirmed.**

The user confirmed that the separately defined Phase 3D quality gate passed. No additional per-metric breakdown was supplied in that confirmation, so this record does not invent scores or sub-results beyond the confirmed PASS.

Therefore:

- Phase 3D GPU/API combined integration: **PASS**
- Phase 3D browser stale-state gate: **PASS**
- Phase 3D browser valid-GO/save/reload workflow: **PASS (G11/G12)**
- Phase 3D visual-quality gate: **PASS (user-confirmed)**
- Phase 3D runtime/integration qualification: **PASS**
- Phase 3D overall: **GPU PASS / COMPLETE**

## Current certification

- Phase 1 generic Draft/Continue: **GPU PASS**
- Core loader identity fix: **GPU PASS**
- Phase 2 Native Reference Transparency: **GPU PASS**
- Phase 3A static START structured layout: **GPU PASS**
- Phase 3B START→END structured layout: **GPU PASS**
- Phase 3C Multi-Key Timeline: **GPU PASS**
- Phase 3D Reference + Structured GPU/API integration: **PASS (8/8 executed)**
- Phase 3D browser stale-state rejection gate: **PASS (D5–D9)**
- Phase 3D browser valid-GO/save/reload workflow: **PASS (G11/G12)**
- Phase 3D visual-quality gate: **PASS (user-confirmed)**
- Phase 3D overall: **GPU PASS / COMPLETE**
- Phase 3D combined visual-quality gate: **PASS (user-confirmed)**

## Remaining boundary

Not yet covered:

- numeric depth enforcement
- arbitrary live ControlNet/hooks
- noise masks
- custom/multi-model guiders
- multistep solver-history resume
- production memory-headroom hardening

## Phase 4A — Preview / GO State UX

Implementation status: **implemented on main; browser GPU/UI gate pending**.

Phase 4A changes only frontend review UX. Backend sampling and state contracts are unchanged.

Implemented browser states:

- `preview_required`
- `preview_queued`
- `ready`
- `stale`
- `continue_queued`
- `complete`
- `error`

Key contract:

- Draft and directly connected Continue mirror one review state.
- GO is enabled only in `ready`.
- GO still recomputes the upstream graph signature immediately before Queue.
- A signature mismatch clears UI approval and shows `PREVIEW STALE / NEW PREVIEW REQUIRED`.
- Saved workflows never persist GO approval or State ID.
- Reopen returns to Preview-required state.
- Preview/New Seed/GO controls are inside the status panel.

Host/CI coverage includes pure state transitions, GO-enable exclusivity, sampler approval reset, browser-extension syntax checks, and existing Python/JavaScript contracts.

Real-device Phase 4A gate:

- A0: workflow load → Preview required
- A1: Preview queued → Preview running / GO locked
- A2: Preview success → Draft READY and Continue READY TO GO
- A3: GO → CONTINUING
- A4: Continue success → COMPLETE
- A5: upstream change after Preview → stale / not queued
- A6: new Preview after stale → READY again / GO enabled
- A7: save → close → reopen → approval not restored / Preview required

