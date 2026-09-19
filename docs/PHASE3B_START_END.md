# Phase 3B — START → END GPU Gate

Status: implementation complete, real H3 GPU validation pending.

## Purpose

Phase 3B extends the Phase 3A structured-layout integrity layer from one START layout to a START→END transition.

The Preview still represents Frame 0 / START. Phase 3B does not claim that one Preview verifies the final END pose. Instead it guarantees that GO resumes the same Draft with the same audited START→END conditioning contract.

## Required upstream wiring

Use H3 Structured Canvas + Structured Prompter.

For every slot that should move from START to END, set the Prompter slot motion to `start_end`.

The exact Prompter STRING must still feed both:

1. the native H3 conditioner,
2. H3 Structured Layout Audit.

The audited CONDITIONING then feeds the Guider.

## Supported transition contract

- 1–3 slots A/B/C
- same slot set at START and END
- fixed Canvas width and height
- normalized 0..1000 xyxy BBOX
- Timeline Experimental v3 or v4 shell is allowed
- piecewise-linear START→END
- no explicit MID
- no Multi-Key keyframes

Static/no-op Timeline wrappers remain Phase 3A compatible and collapse to the same START hash.

## Report

For START→END layouts, `structured_layout.items[*]` includes:

- `scope: start_end`
- `start_hash`
- `end_hash`
- `transition_hash`
- `moved_slots`
- `ir_hash`
- `prompt_hash`

## GPU gate

### T0 — static regression

Use the already-passing static START workflow.

Expected:

- Preview succeeds
- GO succeeds
- final video succeeds
- `scope = start`

### T1 — one moving slot

Use one subject with different START and END BBOX values.

Expected:

- Preview succeeds
- report shows `scope = start_end`
- `moved_slots = ["a"]` (or the actual slot)
- GO succeeds
- final video succeeds

### T2 — two or three moving slots

Move A/B or A/B/C.

Expected:

- Preview succeeds
- report shows the moved slots
- GO succeeds
- final video succeeds

Visual motion quality is evaluated separately from execution correctness.

### T3 — stale END change

1. Generate Preview.
2. Change only one END BBOX.
3. Attempt GO without generating a new Preview.

Expected: Continue sampling does not start. The reviewed state is rejected as changed.

### T4 — new Preview after END change

After T3:

1. generate a new Preview,
2. approve that new state,
3. GO.

Expected: final video completes.

## Not part of Phase 3B

- explicit MID
- Multi-Key Timeline
- START + 7 intermediate keys + END
- numeric depth enforcement
- arbitrary sampler-history resume

Those remain later phases.
