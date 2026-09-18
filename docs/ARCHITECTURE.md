# Architecture — generic sampler adapters and Native Reference transparency

## Frozen sampling baseline

The approved concept remains native MiniMax H3 T2VA with a shared Turbo LoRA, 6 total Euler/simple steps, Preview after 3 transitions, and Continue for the remaining 3. Both video and audio latents exist at full target length from the start.

`H3 Draft Sampler` receives external NOISE / GUIDER / SAMPLER / SIGMAS / LATENT and `H3 Continue Sampler` returns normal LATENT outputs.

## Sampling boundary

`SamplerCustomAdvanced.output` and `denoised_output` are different values.

Draft State stores the exact Core sampler output at the split boundary. Continue uses zero new noise and the remaining sigma slice. The x0/denoised output is used only for the one-frame Preview.

## Core loader binding

ComfyUI loads built-in extra-node files through its own loader and registers the resulting node classes in `nodes.NODE_CLASS_MAPPINGS`.

Draft-Continue binds to those registered classes instead of re-importing `comfy_extras.nodes_custom_sampler`. This avoids duplicate Python class identities for stock `Guider_Basic`.

Supported guider families remain Core BasicGuider / CFGGuider / DualCFGGuider. Unknown custom/multi-model guiders fail closed.

## Phase 2 — Native Reference Transparency

MiniMax H3 native reference conditioning is carried in `minimax_refs` on CONDITIONING. Core currently emits ordered blocks with these kinds:

- `image`
- `video`
- `video_audio`
- `audio`

Draft-Continue does not interpret those references into a new format and does not re-encode them.

At Draft capture:

1. the actual external GUIDER conditioning is frozen to CPU-owned state;
2. every `minimax_refs` list is validated as native tensor/scalar data;
3. order is preserved;
4. a Reference-only payload SHA-256 is computed;
5. a manifest records kind, order, tensor shape/dtype/size and native scalar metadata.

At GO:

1. the source GUIDER's current Reference hash is recomputed;
2. the stored Draft Reference hash is recomputed;
3. content/count/order/kind/metadata changes reject the stale approval before continuation sampling;
4. unchanged stored CONDITIONING is cloned into the fresh guider used by Continue.

This is intentionally separate from the generic whole-CONDITIONING hash. The dedicated hash provides explicit Reference invalidation and observability while the existing conditioning signature continues to protect all other conditioning fields.

## State ownership and safety

State tensors are detached CPU clones. ComfyUI cache owns the state object's lifetime; there is no separate global tensor/model cache.

A unique State ID binds GO to the exact reviewed Preview. State is session-bound and not serialized to disk.

The current state payload budget is 512 MiB, including stored conditioning and native Reference tensors.

## Remaining compatibility boundary

- native MiniMax H3 joint AV latent, batch=1
- Core Euler without churn
- external valid descending H3 flow SIGMAS
- Core Basic/CFG/DualCFG guider families
- tensor/scalar native `minimax_refs`

Multistep solver history, live ControlNet/hooks, custom/multi-model guiders and noise masks require separate resume adapters.

See [REFERENCE_GATE.md](REFERENCE_GATE.md) for the real-GPU Phase 2 acceptance gate.
