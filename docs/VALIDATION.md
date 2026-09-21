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

## Phase 3D combined Reference + Structured integration — GPU PASS / COMPLETE

Date: 2026-09-20 JST.

Overall status: **GPU PASS / COMPLETE**.

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
- Phase 4A Preview / GO State UX: **GPU/UI PASS / COMPLETE (A0–A7)**

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

Implementation status: **GPU/UI PASS / COMPLETE**.

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

### Phase 4A first real-device attempt — A0 BLOCKED

Date: 2026-09-20 JST.

Backend/GPU sampling itself was healthy: a direct Draft Preview completed successfully on RTX 5060 Ti with no OOM. However, the Phase 4A status panel and controls did not appear on either the loaded workflow node or a newly added Draft Sampler, so A0 could not be certified and A1–A7 were not started.

This isolates the first failure to frontend extension loading/registration rather than the sampler GPU path.

Observed Preview run:

- 512×768, requested 5 s
- Euler / 6 total steps / Preview at 3
- 2 References
- Preview history success
- ~132.83 s
- minimum observed free VRAM ~1.31 GiB
- minimum observed free RAM ~3.41 GiB
- no OOM

Follow-up hardening on main:

- version the `logic.mjs` dependency URL from `draft.js`
- use a namespace import so a stale dependency cannot fail solely on a newly added named export
- provide a minimal fail-safe state renderer if the old dependency is still returned
- expose `globalThis.__H3_DRAFT_CONTINUE_UI__` and a console load marker for A0 diagnostics

A0–A7 remain pending until the frontend panel is visible on a fresh real browser run.

Real-device Phase 4A gate:

- A0: workflow load → Preview required
- A1: Preview queued → Preview running / GO locked
- A2: Preview success → Draft READY and Continue READY TO GO
- A3: GO → CONTINUING
- A4: Continue success → COMPLETE
- A5: upstream change after Preview → stale / not queued
- A6: new Preview after stale → READY again / GO enabled
- A7: save → close → reopen → approval not restored / Preview required


### Phase 4A A0–A7 real-device retest — PARTIAL

Date: 2026-09-20 JST.

Result:

- A0 PASS
- A1 PASS
- A2 PASS
- A3 PASS
- A4 FAIL — Continue and video save succeeded, but UI remained `READY TO GO` with GO enabled instead of transitioning to `COMPLETE`
- A5 PASS
- A6 PASS
- A7 PASS

Runtime behavior during A3/A4 remained correct:

- Continue history reported success / complete
- resumed from step 3
- no new noise
- no conditioning re-encode
- no schedule rebuild
- video save succeeded
- final queue 0 running / 0 pending
- no OOM or crash

Observed maxima:

- system RAM ~60.2 / 63.93 GiB
- VRAM ~15,138 / 16,311 MiB

Root cause boundary: frontend completion-state finalization only. Sampling and save paths are not implicated.

Main fix: when a tracked Continue prompt emits `execution_success` while the synchronized review state is still `continue_queued`, force the pair to `complete`. This is a fail-safe for cases where the node-level `onExecuted` UI report is not delivered to the browser.

A4 requires one browser retest after updating main. A0–A3 and A5–A7 do not need to be repeated unless the user wants a full matrix rerun.


### Phase 4A A4 second retest — still FAIL

Continue sampling and SaveVideo again succeeded, but after completion the browser UI returned to `READY TO GO` and re-enabled GO.

History for the same successful Queue showed:

- Draft node report: `ready`
- Continue node report: `complete`

This supports an event-order rollback: a late/cached Draft `ready` UI report can arrive after Continue completion and overwrite the terminal display.

Main follow-up fix:

- treat `continue_queued` and `complete` as protected phases against Draft `ready` reports
- `COMPLETE` is terminal until an explicit new Preview first moves the state to `preview_queued`
- retain the prompt-level `execution_success` completion fallback
- add regression tests proving a late Draft `ready` cannot reopen GO after Continue

A4 remains pending one targeted browser retest.


### Phase 4A final A4 retest — PASS

The terminal-state ordering fix passed on real browser/GPU.

A4 final retest:

- Preview: 70.1 s, `READY · 3/6`
- Continue: resumed from step 3 for the remaining 3 transitions, 36.1 s
- no new noise
- no conditioning re-encode
- no schedule rebuild
- no Reference re-encode
- SaveVideo succeeded and was retrievable over HTTP 200
- final Draft UI: `REVIEWED`
- final Continue UI: `COMPLETE`
- GO remained disabled
- final Queue: 0 running / 0 pending
- no OOM

Observed peak during the final A4 retest:

- system RAM ~60.7 / 63.9 GiB
- VRAM ~15.5 / 15.9 GiB

With the previously confirmed A0–A3 and A5–A7 results, the complete Phase 4A browser UX gate is now:

- A0 PASS
- A1 PASS
- A2 PASS
- A3 PASS
- A4 PASS
- A5 PASS
- A6 PASS
- A7 PASS

Therefore Phase 4A Preview / GO State UX is **GPU/UI PASS / COMPLETE**.



## Phase 4B — Lifecycle / stale-state management

Implementation status: **implemented on main; real-browser retest pending**.

Initial real-device result: **PARTIAL**.

Observed before the Phase 4B fix:

- B0 PASS — workflow opened in `PREVIEW REQUIRED`, GO disabled, Queue empty
- B1 PASS — Preview completed and reached `READY · 3/6`
- B2 FAIL — switching to another already-open Workflow and back reset READY to `PREVIEW REQUIRED`
- B3 FAIL — editing Slot A description after Preview left `READY TO GO` active instead of immediately invalidating approval
- B6 PASS — GO resumed step 3 and reached COMPLETE; SaveVideo succeeded
- B7 FAIL — switching away/back after completion reset COMPLETE to `PREVIEW REQUIRED`
- B4/B5/B8/B9/B10 — not run

Initial Phase 4B resource observation:

- RAM peak ~50.2 / 63.9 GiB
- VRAM peak ~15.3 / 15.9 GiB
- no OOM
- final Queue 0 running / 0 pending

### Phase 4B implementation

B2/B7:

- stable review state is held only in browser-session memory
- the cache is keyed by the live workflow-state object supplied to `beforeConfigureGraph`
- switching between already-open tabs can restore `READY`, `STALE`, or `COMPLETE`
- pending states are not restored
- nothing is written to workflow JSON
- closing/unloading and reopening a saved workflow creates a fresh workflow-state object, so the existing Phase 4A approval-reset boundary remains intact

B3:

- listen for ComfyUI ChangeTracker `graphChanged`
- while a Draft is `READY`, debounce and recompute the upstream graph signature
- mismatch or an invalid upstream graph immediately marks the Draft `PREVIEW STALE`
- GO remains locked until a fresh Preview
- GO-time signature verification remains unchanged as a second safety layer

Next real-browser gate should re-run B2, B3 and B7 first, then continue B4/B5/B8/B9/B10.


### Phase 4B second implementation correction

The first Phase 4B fix did not change B2/B3/B7 on real browser.

Root cause was confirmed from current ComfyUI frontend source:

- `loadGraphData()` clones workflow JSON before `beforeConfigureGraph`
- `clean()` runs before `beforeConfigureGraph`
- therefore object-identity WeakMap keys cannot survive tab round-trips, and outgoing Draft runtime is already gone when `beforeConfigureGraph` runs

Corrected implementation:

- capture outgoing Draft review state in `beforeLoadGraph`, before graph cleanup
- restore in `afterLoadGraph`
- key state by the currently open workflow tab path
- keep the cache browser-session-only
- prune cache when a workflow tab closes, preserving the Phase 4A save/close/reopen reset contract
- trigger READY signature revalidation from `graphChanged` plus `input/change/mouseup/keyup` user interaction events

B2/B3/B7 require another targeted browser retest on v1.7.1.


### Phase 4B v1.7.1 retest

Result:

- B2 FAIL — READY still reset to `PREVIEW REQUIRED` after tab round-trip
- B3 PASS — Slot A description edit immediately produced `PREVIEW STALE / NEW PREVIEW REQUIRED`, GO disabled, Queue stayed empty
- B7 FAIL — COMPLETE still reset to `PREVIEW REQUIRED` after tab round-trip

Runtime remained healthy:

- Preview ~64.8 s
- Continue resumed at step 3 and completed
- no OOM
- peak RAM ~61.4 / 63.9 GiB
- peak VRAM ~15.56 / 15.93 GiB
- final Queue empty

The v1.7.1 stale-detection path is therefore validated, while tab-state identity was still wrong.

### Phase 4B v1.7.2 tab identity correction

Current ComfyUI frontend exposes the live workflow store through:

`app.extensionManager.workflow.activeWorkflow.path`

and `openWorkflows`.

v1.7.2 now uses those values directly for session review-state keys and close pruning. DOM-selected tab lookup is retained only as a fallback.

This specifically targets B2/B7. B3 does not need regression rerun unless desired.


### Phase 4B v1.7.2 retest

Result:

- B2 FAIL — READY still reset to `PREVIEW REQUIRED` after switching away/back
- B7 FAIL — COMPLETE still reset to `PREVIEW REQUIRED` after switching away/back
- B3 remains PASS from the previous v1.7.1 retest

Runtime during the retest remained healthy:

- Preview ~67.6 s
- Continue resumed at step 3 and completed the remaining 3 steps in ~35.6 s
- no OOM or generation failure
- peak RAM ~60.71 / 63.93 GiB
- peak VRAM ~15.42 / 15.93 GiB
- final Queue empty

### Phase 4B v1.7.3 tracker-keyed lifecycle fix

Path-based lifecycle identity was removed.

Current ComfyUI keeps a per-open-workflow `changeTracker` object:

- switching between already-open Workflow tabs keeps the same tracker for each tab
- closing a persisted Workflow calls `unload()`, which clears its tracker
- reopening creates a new tracker

v1.7.3 therefore stores session-only review state in a `WeakMap` keyed directly by:

`app.extensionManager.workflow.activeWorkflow.changeTracker`

Lifecycle:

- `beforeLoadGraph` captures READY/STALE/COMPLETE under the outgoing tracker
- `afterLoadGraph` restores from the incoming tracker
- close/reopen cannot recover the old entry because the tracker identity changes

This specifically targets B2/B7. B3 stale detection is unchanged because it already passed.


### Phase 4B v1.7.3 root cause — Frontend 1.52.7 lifecycle incompatibility

The v1.7.3 B2/B7 failures were traced to the installed ComfyUI Frontend 1.52.7 lifecycle API.

Frontend 1.52.7 supports `beforeConfigureGraph / afterConfigureGraph`, but does not expose or invoke the newer `beforeLoadGraph / afterLoadGraph` extension hooks used by v1.7.3.

Observed consequence:

- READY / COMPLETE existed before Workflow switch
- v1.7.3 lifecycle capture hook never ran
- graph replacement reset Draft/Continue UI to `PREVIEW REQUIRED`
- restore hook never ran
- Preview, Continue, SaveVideo and Queue completion themselves remained healthy

This also explains why the pure JavaScript state tests passed while real browser lifecycle integration failed: the tests did not exercise the host Frontend's extension-hook availability.

### Phase 4B v1.7.4 compatibility implementation

v1.7.4 no longer depends on `beforeLoadGraph / afterLoadGraph`.

Instead it installs a guarded wrapper around the long-standing `app.loadGraphData()` method:

1. before the original load runs, capture stable review state from the outgoing workflow tracker
2. run the original ComfyUI `loadGraphData()` unchanged
3. after it resolves, read the incoming active workflow tracker
4. if the tracker changed and has a cached session state, restore `READY / STALE / COMPLETE`

Safety boundaries:

- cache remains a `WeakMap` keyed by `changeTracker`
- no approval/state ID is serialized into Workflow JSON
- close/reopen creates a new tracker and therefore still returns to `PREVIEW REQUIRED`
- `clean=false` graph reloads are excluded from lifecycle restoration
- bridge hook errors are isolated so they do not block ComfyUI core loading

New host-facing coverage:

- lifecycle bridge before/load/after ordering
- wrapper idempotency
- original load error rethrow
- bridge-hook failure isolation
- lifecycle module syntax check in CI

B3 remains PASS. B2/B7 require a targeted Frontend 1.52.7 browser retest.


### Phase 4B v1.7.4 real-browser retest — B2/B7 PASS

After a full browser reload (Ctrl+F5), the actual v1.7.4 frontend extension and Frontend 1.52.7 compatibility bridge were loaded.

Diagnostics confirmed:

- lifecycle bridge startup: `loadGraphData-wrapper`
- B2 tab switch: capture log present, restore log present
- B7 tab switch: capture log present, restore log present

Results:

- B2 PASS — after Preview reached `READY · 3/6`, switching to another Workflow and returning preserved `READY · 3/6`, `READY TO GO`, and GO enabled
- B7 PASS — after Continue completed, switching away/back preserved Draft `REVIEWED`, Continue `COMPLETE`, disabled completion/GO control, and an empty Queue
- Continue resumed 3 steps and completed in ~33 s
- Queue after B7: 0 active
- no OOM or crash

The earlier v1.7.4 B2/B7 result is excluded because that browser page still had an old v1.1.1-era `draft.js` module resident in page memory. Backend restart alone does not replace already-loaded extension JavaScript in an open browser page.

Current Phase 4B matrix:

- B0 PASS
- B1 PASS
- B2 PASS
- B3 PASS
- B6 PASS
- B7 PASS
- B4/B5/B8/B9/B10 not yet run

Phase 4B overall remains **PARTIAL** until the remaining B4/B5/B8/B9/B10 cases are completed.


### Phase 4B B4/B5/B8/B9/B10 real-browser result

Frontend 1.52.7 / UI build 1.7.5:

- B4 PASS
- B5 PASS
- B8 PASS
- B9 PASS
- B10 FAIL — after Ctrl+F5 the UI still showed `READY · 3/6` with GO enabled instead of `PREVIEW REQUIRED`

B10 was not a GPU/sampling failure. Queue was empty, UI build verification reported 1.7.5 VERIFIED, and the lifecycle wrapper was active.

The saved test workflow does not contain an approval: Draft status is empty and Continue persists `go=false` with an empty approval ID. The failure is therefore a browser-runtime lifecycle boundary, not workflow-file persistence.

v1.7.6 fix:

- stable lifecycle state must be owned by the currently evaluated browser page
- startup/historical `ready/complete` reports cannot recreate approval without a current-page execution
- open-tab restore rebinds the cached state to the current page token
- B2/B7 semantics are preserved
- B10 requires targeted real-browser retest

Current Phase 4B status: **PARTIAL — B10 only pending**.
