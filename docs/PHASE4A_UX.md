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

## Acceptance gate

- A0 load → Preview required
- A1 Preview queued → running
- A2 Preview success → READY / READY TO GO
- A3 GO → CONTINUING
- A4 Continue success → COMPLETE
- A5 upstream change → stale, no Queue
- A6 fresh Preview after stale → READY
- A7 save/reopen → approval reset, Preview required
