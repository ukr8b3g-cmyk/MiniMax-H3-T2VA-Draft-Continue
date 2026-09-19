# Validation

Date: 2026-09-19.

## Confirmed GPU evidence

User-confirmed real ComfyUI/H3 passes:

- Phase 0 concept: Preview 3/6 → Continue 3/6 → final video
- Phase 1 generic Sampler-level integration
- Core loader identity fix
- Phase 2 Native Reference Transparency
- Phase 3A static START structured-layout audit, including Timeline Experimental no-op wrapper compatibility
- Phase 3A final video generation
- Phase 3B START→END structured-layout integration gate T0–T4

These are real-device execution results. Visual placement and motion quality remain model-dependent and are not converted into a numeric quality certification.

## Phase 3B GPU PASS

Environment:

- backend: `http://127.0.0.6:8188`
- repository HEAD: `97243bd`
- GPU: NVIDIA GeForce RTX 5060 Ti 16 GB
- date: 2026-09-19 JST

Gate result: **T0–T4 PASS** for integration/correctness.

### T0 — static START regression

PASS.

- browser workflow
- Preview 79.207 s
- sampling 46.987 s
- Preview decode 32.088 s
- Continue 45.607 s
- `scope = start`
- no moved slots
- resumed from step 3
- no new noise
- no conditioning re-encode
- no schedule rebuild
- final video/audio created successfully

### T1 — one moving slot

PASS.

- real GPU server queue execution
- `scope = start_end`
- `moved_slots = ["a"]`
- Preview → Continue completed
- resumed from step 3
- conditioning preserved
- no new noise/re-encode/rebuild
- final video/audio created successfully

### T2 — two moving slots

PASS.

- real GPU server queue execution
- `scope = start_end`
- `moved_slots = ["a","b"]`
- Preview → Continue completed
- resumed from step 3
- conditioning preserved
- no new noise/re-encode/rebuild
- final video/audio created successfully

T1/T2 validated the server-side START→END path using prompt payloads derived from the repository v1.4 START-END example; they were not browser-loaded workflow runs.

### T3 — stale GO rejection

PASS.

After Preview, only the END BBOX was changed.

- old GO was rejected with “Settings changed”
- it was not queued
- queue remained 0 running / 0 pending
- no continuation sampling started

This satisfies the stale-approval safety contract.

### T4 — re-preview then GO

PASS.

- browser workflow
- Preview 76.091 s
- Continue 42.597 s
- `scope = start_end`
- moved slot `b`
- `start_hash`, `end_hash`, `transition_hash` present
- Draft and Continue structured-layout payload hashes matched
- resumed from step 3
- no new noise/re-encode/rebuild
- conditioning preserved
- final video/audio created successfully

## Media checks

T0 final media:

- H.264
- 768×768
- 24 fps
- 124 frames
- 5.166667 s
- AAC 32 kHz stereo
- audio 5.167 s

T1/T2 final media:

- H.264
- 512×768
- 24 fps
- 124 frames
- 5.166667 s
- AAC 32 kHz stereo
- audio 5.167 s

T4 final media:

- H.264
- 768×768
- 24 fps
- 124 frames
- 5.166667 s
- AAC 32 kHz stereo
- audio 5.167 s

## Stability and resource note

No OOM, NaN, crash, or failed queue execution was observed.

T0 sampled peak was approximately:

- VRAM: 15,122 MiB
- system RAM: 62.31 GiB

The machine had about 63.93 GiB total system RAM, so **system RAM headroom is a material warning** even though the gate passed.

Final cleanup check:

- queue: 0 running / 0 pending
- backend left running
- final GPU memory: 1,496 / 16,311 MiB

## Current certification

- Phase 1 generic Draft/Continue: **GPU PASS**
- Core loader identity fix: **GPU PASS**
- Phase 2 Native Reference Transparency: **GPU PASS**
- Phase 3A static START structured layout: **GPU PASS**
- Phase 3B START→END structured layout: **GPU PASS**
- subjective START→END motion quality: **not graded**
- explicit MID / Multi-Key Timeline: **not yet Phase 3B**

## Remaining boundary

Not yet covered:

- explicit MID
- Multi-Key Timeline
- numeric depth enforcement
- arbitrary live ControlNet/hooks
- noise masks
- custom/multi-model guiders
- multistep solver-history resume
