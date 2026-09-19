# Changelog

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
- Real Phase 3C GPU gate is pending.

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
