# Phase 4A — Preview / GO State UX

Status: implementation complete on main; real browser/GPU UX gate pending.

## Goal

Present H3 Draft Sampler and H3 Continue Sampler as one synchronized review gate.

Phase 4A does not change sampling equations, state payloads, Reference/Structured contracts, SIGMAS, noise, or resume behavior.

## UI state machine

| State | Draft | Continue | GO |
| --- | --- | --- | --- |
| preview_required | PREVIEW REQUIRED | WAITING FOR PREVIEW | locked |
| preview_queued | PREVIEW RUNNING | WAITING | locked |
| ready | READY · current/total | READY TO GO | enabled |
| stale | PREVIEW STALE | NEW PREVIEW REQUIRED | locked |
| continue_queued | REVIEWED | CONTINUING | locked |
| complete | REVIEWED | COMPLETE | locked |
| error | REVIEW ERROR | NOT READY | locked |

Only the `ready` state enables GO.

## Safety contract

GO UI readiness is not trusted by itself.

Immediately before Queue:

1. graphToPrompt()
2. recompute Draft upstream signature
3. compare with the reviewed Preview graph hash
4. on mismatch, clear UI approval and mark stale
5. Queue only when the signature still matches

Saved workflows use the existing safeWorkflow contract and never persist GO approval / approved state ID.

## Controls

Draft status panel:

- Preview
- New seed + Preview

Continue status panel:

- GO · Continue this draft

Buttons are disabled according to the pure review state contract.

## Backend boundary

Unchanged:

- SamplerEngine
- SamplerDraftState
- Reference hash/fingerprint
- Structured layout hashes
- SIGMAS
- Noise
- Euler resume
- AV latent
- sampling equations

## First real-device attempt

The first Phase 4A browser attempt reached the backend and completed a Draft Preview, but A0 was blocked because the Phase 4A panel/buttons were absent even on a newly added Draft Sampler.

This means the sampler path was operational while the frontend extension had not registered successfully.

Main was hardened to avoid a stale `logic.mjs` dependency breaking the whole extension after the new Phase 4A export was introduced. The frontend now also exposes:

```js
globalThis.__H3_DRAFT_CONTINUE_UI__
```

Expected after load:

```js
{ loaded: true, version: "1.6.0", logicStateContract: "native" }
```

A0–A7 still require a fresh browser/GPU rerun.

## Acceptance gate

- A0 load → Preview required
- A1 Preview queued → running
- A2 Preview success → READY / READY TO GO
- A3 GO → CONTINUING
- A4 Continue success → COMPLETE
- A5 upstream change → stale, no Queue
- A6 fresh Preview after stale → READY
- A7 save/reopen → approval reset, Preview required

## A4 completion-display fix

The first full A0–A7 real-device pass reached A4 with successful Continue sampling and successful video save, but the UI stayed at `READY TO GO` and left GO enabled.

The browser now treats the tracked prompt-level `execution_success` event as a completion fail-safe:

- if the submitted node is Continue
- and the synchronized Draft state is still `continue_queued`
- transition the review pair to `complete`

The existing node-level `onExecuted` report path remains in place and can still supply the richer completion detail. The success-event transition only closes the UI state when that report path did not finalize the panel.

Only A4 needs targeted real-browser retest after this fix.

