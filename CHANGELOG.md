# Changelog

## 1.7.6 - 2026-09-21

- Fix Phase 4B B10 browser-reload approval reset.
- Treat reviewed Draft state as page-local provenance: only Preview/GO state created in the currently evaluated browser page, or explicitly restored within that same page, can participate in lifecycle persistence.
- Ignore startup/historical Draft `ready` and Continue `complete` reports when they are not associated with a current-page execution.
- Keep B2/B7 open-tab restoration working by re-marking restored runtime as owned by the current page.
- Keep B3 stale-signature detection, sampling math, SIGMAS, conditioning, Reference handling and backend state unchanged.
- Add host regression tests for historical report rejection and a simulated full-page reload boundary.
- B4/B5/B8/B9 are user-confirmed PASS; B10 requires one real-browser retest on v1.7.6.
- Phase 4B remains PARTIAL until B10 passes.

## 1.7.4 - 2026-09-21

- Add a backward-compatible lifecycle bridge for ComfyUI Frontend 1.52.7.
- Confirmed Frontend 1.52.7 does not invoke the newer `beforeLoadGraph` / `afterLoadGraph` extension hooks used by v1.7.3.
- Wrap the stable `app.loadGraphData()` entry point instead: capture stable Draft review state immediately before graph replacement and restore it after the load resolves.
- Keep the session cache keyed by the live workflow `changeTracker` object, so open-tab switches can restore `READY / STALE / COMPLETE`, while close/reopen creates a new tracker and still requires a new Preview.
- Only bridge clean graph replacement loads; undo/redo style `clean=false` loads are not treated as workflow-tab lifecycle restores.
- Keep the already-passing B3 live stale-signature detection unchanged.
- Add `web/lifecycle.mjs` and dedicated Node tests covering before/load/after ordering, idempotent installation, load-error propagation, and bridge-hook isolation.
- Add lifecycle module syntax checking to CI.
- Frontend 1.52.7 browser retest after full reload: B2 PASS, B3 PASS, B7 PASS. READY and COMPLETE survive open-tab round-trips and live upstream edits invalidate READY to STALE.
- Exclude the earlier apparent v1.7.4 B2/B7 failure because the browser page still had an old v1.1.1-era `draft.js` module resident in memory.
- Phase 4B remains PARTIAL until B4/B5/B8/B9/B10 are completed.

## 1.7.3 - 2026-09-21

- Start Phase 4B lifecycle / stale-state management.
- Preserve stable in-session review states (`READY`, `STALE`, `COMPLETE`) when switching between already-open Workflow tabs.
- Keep saved-workflow close/reopen safety: approval/state is not serialized and a reopened workflow still requires a new Preview.
- Use ComfyUI frontend `beforeConfigureGraph / afterConfigureGraph` hooks with an in-memory WeakMap keyed by the live workflow-state object; no approval state is written into workflow JSON.
- Listen to ComfyUI ChangeTracker `graphChanged` and re-check the reviewed Draft graph signature while the UI is `READY`.
- Immediately move to `PREVIEW STALE / NEW PREVIEW REQUIRED` when upstream prompt/layout/reference/sampler inputs no longer match the reviewed Preview.
- Keep GO-time signature verification as the final safety check.
- Initial Phase 4B real-device matrix: B0/B1/B6 PASS; B2/B3/B7 exposed lifecycle gaps; B4/B5/B8/B9/B10 not yet run.
- Phase 4B implementation targets the B2/B3/B7 failures; real-browser retest remains required.
- Correct lifecycle implementation after confirming ComfyUI clones workflow JSON before `beforeConfigureGraph`: capture outgoing state in `beforeLoadGraph` before `clean()`, restore after `afterLoadGraph`, key session state by active workflow tab path, and prune cache when tabs close.
- Expand live stale detection beyond `graphChanged` to browser `input/change/mouseup/keyup` activity so custom DOM and LiteGraph widget edits also trigger reviewed-signature revalidation.
- v1.7.1 real-browser retest: B3 PASS; B2/B7 still FAIL because DOM tab selection was not a reliable workflow identity source.
- v1.7.2 uses `app.extensionManager.workflow.activeWorkflow.path` and `openWorkflows` directly, matching current ComfyUI frontend/browser-test practice; DOM lookup remains fallback only.
- v1.7.2 real-browser retest still failed B2/B7.
- v1.7.3 removes path/DOM lifecycle identity entirely and keys session review state by the workflow's live `changeTracker` object. The same tracker survives open-tab switches; closing a persisted workflow unloads it and reopening creates a new tracker, preserving the Preview-required safety boundary.

## 1.6.0 - 2026-09-20

- Add Phase 4A Preview / GO State UX.
- Present Draft and Continue as one synchronized review gate in the browser UI.
- Add explicit `PREVIEW REQUIRED`, `PREVIEW RUNNING`, `READY TO GO`, `PREVIEW STALE`, `CONTINUING`, `COMPLETE`, and error states.
- Move Preview / New Seed / GO controls into the status panel and disable GO unless the connected Draft is currently reviewed and valid.
- Mirror Draft readiness to the directly connected Continue node.
- Keep the GO-time graph signature re-check; stale settings invalidate UI approval before Queue.
- Saved workflows still never restore approval/state IDs and reopen in Preview-required state.
- Keep backend sampler/state/reference/structured contracts unchanged.
- Add pure JavaScript state-contract tests and browser-extension syntax checks in CI.
- After the first real-device A0 attempt showed no Phase 4A panel despite successful backend Preview sampling, harden frontend module loading with a versioned `logic.mjs` import, namespace import fallback, and an explicit UI-load diagnostic marker.
- Fix A4 completion display: use tracked `execution_success` as a frontend fail-safe to transition a successful Continue from `continue_queued` to `complete` when the node-level UI report did not finalize the panel.
- After the second A4 retest showed a late Draft `ready` report reopening GO after successful Continue, make `continue_queued`/`complete` reject Draft `ready` UI rollback; `COMPLETE` remains terminal until an explicit new Preview.
- Final A4 browser/GPU retest PASS: Draft remained `REVIEWED`, Continue remained `COMPLETE`, GO stayed disabled, SaveVideo succeeded, and Queue ended 0/0.
- Phase 4A A0–A7 GPU/UI gate PASS on RTX 5060 Ti; observed final A4 peak RAM ~60.7/63.9 GiB and VRAM ~15.5/15.9 GiB with no OOM.

## 1.5.0 - 2026-09-19

- Add Phase 3C Multi-Key Timeline Transparency.
- Accept H3 Structured Canvas `timeline_experimental.version = 4` with up to 7 intermediate keys per A/B/C slot.
- Preserve normalized key times, BBOX coordinates, duration, START and END geometry without interpolating or rewriting them.
- Support Timeline Experimental duration from 5.0 to 15.0 seconds and provider minimum key spacing.
- Validate legacy `mid_boxes` against the v4 key at `t=0.5`, then canonicalize the redundant MID mirror away.
- Preserve provider offscreen overscan coordinates within -1000..2000 for v4 Multi-Key trajectories.
- Report `scope=multi_key`, `timeline_hash`, `keyframe_hash`, `key_count`, `key_times`, and `duration_seconds`.
- Reject stale GO after Key position/time/count/order, Duration, START, END, or compiled-prompt changes.
- Keep Phase 3A static START and Phase 3B START→END contracts backward compatible.
- Add Multi-Key host regression gates and a connected Multi-Key workflow example.
- GPU gate M0–M6 PASS on RTX 5060 Ti 16 GB.
- Verified stale Key-BBOX, Key-time, and Duration edits reject old GO; fresh Preview then resumes from step 3 and completes.
- 7.5 s timeline produced 192 frames / 8.0 s after H3-valid frame alignment.
- Observed peak system RAM ~59.35 / 63.93 GiB and VRAM ~15.40 / 15.93 GiB; memory headroom remains a production-hardening warning.
- Phase 3D combined Reference + Structured GPU/API matrix: 8/8 executed cases PASS.
- Phase 3D browser stale-GO gate D5–D9 PASS: Reference replacement/order, BBOX, Key-time, Duration and Prompt mutations all rejected old GO before Queue.
- Phase 3D browser valid Preview→GO→Continue→Save PASS (G11), and saved-workflow close/reopen → fresh Preview→GO→Continue→Save PASS (G12).
- Saved workflow reload correctly resets approval/runtime state and requires a new Preview.
- Phase 3D runtime/integration qualification is fully PASS.
- Phase 3D visual-quality gate is user-confirmed PASS; overall Phase 3D is GPU PASS / COMPLETE.
- G11/G12 observed peaks: system RAM ~60.62 / 63.93 GiB and VRAM ~15.39 / 15.93 GiB; no OOM, crash, or sampling error.
- Phase 3D observed peaks: VRAM 15,637 / 16,311 MiB and system RAM 60.155 / 63.927 GiB; no OOM or crash.
- D3B requested 7.5 s and produced 192 frames / 8.0 s after H3-valid frame alignment.
- Corrected D10 verified per-slot Key-time change (A K1=0.30 while C K1=0.25), re-Preview, step-3 resume, and final video completion.

## 1.4.0 - 2026-09-19

- Add Phase 3B START → END Layout Transition audit.
- Preserve model-facing `transition.end_boxes` instead of rejecting real END movement.
- Keep static/no-op Timeline Experimental wrappers canonicalized to the existing Phase 3A START hash.
- Require the same A/B/C slot set at START and END and a fixed H3 canvas.
- Accept known Timeline Experimental v3/v4 wrappers only when MID and Multi-Key data are empty.
- Report START hash, END hash, transition hash and moved slots.
- Reject stale GO when START, END or compiled prompt changes after Preview.
- Add a connected START→END workflow example.
- Phase 3A static START path remains backward compatible.
- GPU gate T0–T4 PASS on RTX 5060 Ti 16 GB; stale END change rejection and re-preview continuation verified.
- Note: observed T0 peak system RAM was ~62.31 GiB on a ~63.93 GiB machine, so RAM headroom remains a production-hardening warning.

## 1.3.1 - 2026-09-19

- Fix Phase 3A compatibility with Timeline Experimental Canvas auto-serialization.
- Accept only semantically static v3/v4 wrappers where END exactly equals START and MID/Multi-Key data is empty.
- Canonicalize those no-op wrappers to the same START IR/hash as the original static Canvas.
- Continue to fail closed when END differs, explicit MID exists, Multi-Key data exists, or unknown timeline/transition metadata would be discarded.
- Add regression tests reproducing the frontend-added `transition` / `timeline_experimental` wrapper.
- GitHub Actions CPU and workflow contracts pass; real Phase 3A GPU/UI rerun remains required.

## 1.3.0 - 2026-09-19

- Add optional START-layout audit for H3 Structured Canvas without changing Draft/Continue sampler ports.
- Attach exact compiled-prompt provenance and canonical START layout metadata to CONDITIONING.
- Reject stale GO after audited layout or compiled prompt changes.
- Keep Reference handling, sampling math and conditioning tensors unchanged.

## 1.2.0 - 2026-09-19

- Add Phase 2 Native Reference Transparency for MiniMax H3.
- Keep Core `minimax_refs` inside the original external CONDITIONING; no custom reference format or re-encoding is introduced.
- Snapshot and fingerprint native H3 reference payloads, including ordered `image`, `video`, `video_audio`, and `audio` blocks.
- Report reference count, kind distribution, tensor shapes and reference payload SHA-256 in Draft State.
- Invalidate an approved Draft when native Reference content, count, order, kind or native metadata changes after Preview.
- Add R0-R3 host regression gates for no-reference baseline, one image reference, multiple mixed references, and stale-GO rejection after Reference changes.
- GPU Reference Gate is pending; no release tag is created by this implementation step.

## 1.1.1 - 2026-09-18

- Fix Core `BasicGuider` rejection caused by ComfyUI built-in extra-node loader class identity differences.
- Bind to node classes already registered in `nodes.NODE_CLASS_MAPPINGS` instead of re-importing `comfy_extras.nodes_custom_sampler`.
- Snapshot the actual graph guider instance and clone its primary ModelPatcher/options.
- Keep custom/multi-model guiders fail-closed until a dedicated resume adapter exists.
- Add regression tests for loader identity.

## 1.1.0 - 2026-09-18

- Add generic Sampler-level `H3 Draft Sampler` / `H3 Continue Sampler` pair.
- Preserve external NOISE / GUIDER / SAMPLER / SIGMAS / LATENT semantics and standard LATENT outputs.
- Keep the integrated v1.0 Preview / GO nodes for compatibility.
