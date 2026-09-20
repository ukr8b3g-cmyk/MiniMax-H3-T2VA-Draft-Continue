# Phase 4B — Lifecycle / Stale-State Management

Status: v1.7.4 implementation on main; GPU/browser gate **PARTIAL / B2+B7 retest pending**.

## Purpose

Phase 4A established the visible Preview → READY → GO → COMPLETE state machine.

Phase 4B makes that state survive normal in-session workflow navigation while invalidating approval as soon as the execution-relevant graph changes.

## Session lifecycle contract

Stable session-only phases:

- `ready`
- `stale`
- `complete`

These may be restored when the user switches from one already-open Workflow tab to another and then returns.

Not restored:

- `preview_required`
- `preview_queued`
- `continue_queued`
- `error`

The state cache is browser-memory only. It uses a WeakMap keyed by the live workflow-state object passed through ComfyUI's graph configuration hooks.

No approval or state ID is serialized into workflow JSON.

Therefore:

- open-tab switch → stable review state may return
- save + close + reopen → new Preview required
- browser reload / new JS session → new Preview required

## Live stale-state contract

ComfyUI ChangeTracker emits `graphChanged` after workflow edits.

While a Draft is `READY`:

1. debounce the graph change
2. rebuild the current API prompt
3. recompute the Draft upstream signature
4. compare with the reviewed Preview hash
5. mismatch → `PREVIEW STALE / NEW PREVIEW REQUIRED`
6. GO is disabled

The existing GO-click signature check is retained as the final safety check.

## Initial real-device result

Before this lifecycle implementation:

| Case | Result | Observation |
| --- | --- | --- |
| B0 | PASS | open → Preview required |
| B1 | PASS | Preview → READY 3/6 |
| B2 | FAIL | tab switch lost READY |
| B3 | FAIL | upstream description edit did not immediately stale |
| B6 | PASS | Continue + Save completed |
| B7 | FAIL | tab switch lost COMPLETE |

B4/B5/B8/B9/B10 were not run.

## Retest priority

1. B2 — READY survives open-tab round-trip
2. B3 — upstream semantic edit immediately becomes STALE / GO disabled
3. B7 — COMPLETE survives open-tab round-trip
4. continue remaining B4/B5/B8/B9/B10 matrix

Backend sampler/state math is unchanged.


## v1.7.1 lifecycle correction

The original WeakMap implementation was invalid for current ComfyUI because `loadGraphData()` clones the workflow JSON before extension `beforeConfigureGraph` hooks and clears the outgoing graph before that hook.

v1.7.1 instead:

- captures the outgoing graph in `beforeLoadGraph`
- stores stable review phases under the active workflow tab path
- restores them in `afterLoadGraph`
- removes cached state when that tab is closed
- adds DOM/LiteGraph interaction-triggered signature checks in addition to `graphChanged`

This specifically targets B2, B3 and B7 while keeping close/reopen approval reset intact.


## v1.7.2 active-workflow identity fix

The v1.7.1 retest produced B3 PASS but B2/B7 still FAIL.

The remaining issue was not state capture timing; it was workflow identity. DOM tab-selection classes are not a reliable source of the active workflow path across current ComfyUI render modes.

ComfyUI exposes the authoritative store at:

```js
app.extensionManager.workflow.activeWorkflow.path
app.extensionManager.workflow.openWorkflows
```

v1.7.2 uses those directly for:

- outgoing session-state key
- incoming restore key
- closed-tab cache pruning

DOM path lookup remains fallback only.

Targeted retest: B2 and B7.


## v1.7.3 tracker-keyed session state

v1.7.2 still failed B2 and B7, so workflow path identity was removed from the runtime contract.

Session review state is now keyed by the active workflow's live `changeTracker` object.

Why this matches ComfyUI lifecycle:

- an already-open Workflow keeps the same `changeTracker` when switching tabs
- closing a persisted Workflow calls `unload()` and clears that tracker
- reopening constructs a new `changeTracker`

The cache is a `WeakMap`, so it remains browser-session-only and cannot serialize into workflow files.

Targeted retest remains B2 and B7 only. B3 already passed and its stale-signature implementation is unchanged.


## v1.7.4 Frontend 1.52.7 compatibility bridge

Root cause confirmed on ComfyUI Frontend 1.52.7:

- `beforeLoadGraph` is not an available/invoked extension lifecycle hook
- `afterLoadGraph` is not an available/invoked extension lifecycle hook
- therefore v1.7.3 never reached its session capture/restore path

v1.7.4 installs a compatibility bridge around `app.loadGraphData()`, which exists in Frontend 1.52.7 and current Frontend main.

The bridge:

- captures outgoing stable review state before clean graph replacement
- delegates to the original `loadGraphData()`
- restores against the incoming workflow's `changeTracker` after successful load
- ignores `clean=false` loads
- is idempotent and fail-isolated
- keeps close/reopen safety because a reopened persisted Workflow receives a new tracker

B3 live stale detection is unchanged and remains PASS.

Targeted retest: B2 and B7 on Frontend 1.52.7.
