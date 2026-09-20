# Phase 4A — Preview / GO State UX

Status: **GPU/UI PASS / COMPLETE** — 2026-09-20 JST.

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

The initial A0 loading problem was fixed and the subsequent browser/GPU matrix completed.

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


## A4 second-retest ordering fix

A second A4 run again completed Continue and SaveVideo successfully but returned the UI to `READY TO GO`.

The successful Queue history contained both a Draft `ready` report and a Continue `complete` report. The frontend contract is therefore tightened so Draft `ready` cannot change UI state while the synchronized pair is in `continue_queued` or `complete`.

`COMPLETE` is now terminal until the user explicitly starts a new Preview. Starting Preview moves the state to `preview_queued`, after which the new Draft `ready` report is accepted normally.


## Final real-device verdict

**A0–A7 PASS.**

The final A4 retest confirmed that successful Continue completion is terminal in the UI until a new Preview is explicitly started.

Final A4 evidence:

- Preview 70.1 s → `READY · 3/6`
- Continue resumed at step 3 and completed the remaining 3 transitions in 36.1 s
- no new noise
- no conditioning re-encode
- no schedule rebuild
- no Reference re-encode
- SaveVideo succeeded
- Draft remained `REVIEWED`
- Continue remained `COMPLETE`
- GO remained disabled
- Queue ended at 0 running / 0 pending
- no OOM

Peak observed:

- RAM ~60.7 / 63.9 GiB
- VRAM ~15.5 / 15.9 GiB

Together with the already-passed A0–A3 and A5–A7 checks, Phase 4A is **GPU/UI PASS / COMPLETE**.
