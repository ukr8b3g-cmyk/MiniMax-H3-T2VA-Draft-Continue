# Phase 3B — START → END GPU Gate

Status: **GPU PASS** — 2026-09-19 JST.

## Result

The real ComfyUI/H3 integration gate passed T0–T4 on:

- backend: `http://127.0.0.6:8188`
- repository HEAD: `97243bd`
- GPU: NVIDIA GeForce RTX 5060 Ti 16 GB

This is an integration/correctness PASS, not a subjective visual-motion-quality grade.

## Purpose

Phase 3B extends the Phase 3A structured-layout integrity layer from one START layout to a START→END transition.

The Preview still represents Frame 0 / START. Phase 3B does not claim that one Preview verifies the final END pose. Instead it guarantees that GO resumes the same Draft with the same audited START→END conditioning contract.

## Supported transition contract

- 1–3 slots A/B/C
- same slot set at START and END
- fixed Canvas width and height
- normalized 0..1000 xyxy BBOX
- Timeline Experimental v3 or v4 shell
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

## GPU gate results

### T0 — static regression

**PASS.**

- browser workflow
- Preview 79.207 s
- Continue 45.607 s
- `scope = start`
- no moved slots
- resumed from step 3
- final media completed

### T1 — one moving slot

**PASS.**

- real GPU server queue execution
- `scope = start_end`
- moved slot `a`
- Preview → Continue → final media completed
- no new noise / re-encode / schedule rebuild

### T2 — two moving slots

**PASS.**

- real GPU server queue execution
- `scope = start_end`
- moved slots `a,b`
- Preview → Continue → final media completed
- no new noise / re-encode / schedule rebuild

T1/T2 used prompt payloads derived from the repository v1.4 START-END example through the same ComfyUI backend rather than browser-loaded workflow runs.

### T3 — stale END change

**PASS.**

After Preview, one END BBOX was changed.

- old GO rejected with “Settings changed”
- request was not queued
- queue stayed empty
- continuation sampling did not start

### T4 — new Preview after END change

**PASS.**

- browser workflow
- Preview 76.091 s
- Continue 42.597 s
- `scope = start_end`
- moved slot `b`
- START/END/transition hashes present
- Draft and Continue payload hashes matched
- final media completed

## Resource warning

No OOM, NaN, crash, or failed queue execution was observed.

Observed T0 peak:

- ~15,122 MiB VRAM
- ~62.31 GiB system RAM

The machine had ~63.93 GiB system RAM total. Phase 3B therefore passes correctness, but system RAM headroom is tight and should be treated as a production-hardening concern.

## Not part of Phase 3B

- subjective motion-quality certification
- explicit MID
- Multi-Key Timeline
- START + 7 intermediate keys + END
- numeric depth enforcement
- arbitrary sampler-history resume

Those remain later phases.
