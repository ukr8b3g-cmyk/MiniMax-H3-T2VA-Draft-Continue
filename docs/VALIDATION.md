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

## Current certification

- Phase 1 generic Draft/Continue: **GPU PASS**
- Core loader identity fix: **GPU PASS**
- Phase 2 Native Reference Transparency: **GPU PASS**
- Phase 3A static START structured layout: **GPU PASS**
- Phase 3B START→END structured layout: **GPU PASS**
- Phase 3C Multi-Key Timeline: **GPU PASS**
- subjective START→END motion quality: **not graded**
- subjective Multi-Key path-following quality: **not graded**

## Remaining boundary

Not yet covered:

- Phase 3D combined Reference + BBOX / Multi-Key certification
- numeric depth enforcement
- arbitrary live ControlNet/hooks
- noise masks
- custom/multi-model guiders
- multistep solver-history resume
- production memory-headroom hardening
