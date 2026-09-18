# Sampler-level workflow interoperability

## Purpose

The original integrated nodes create T2VA conditioning and schedules internally. The sampler pair is designed for normal ComfyUI workflows where those components already exist.

`H3DraftSampler` consumes the five native `SamplerCustomAdvanced` ports: NOISE, GUIDER, SAMPLER, SIGMAS and LATENT. It additionally needs the MiniMax H3 video VAE for review and a split index.

`H3ContinueSampler` outputs standard Core LATENT `output` and `denoised_output`. Existing VAE decode, audio decode, video creation, postprocessing, refinement and saving remain outside.

## Exact state boundary

The stored AV streams are Core `SamplerCustomAdvanced.output` after inverse-noise scaling and process-latent-out. Continue feeds those values to the same Core sampling path with zero new noise and the original remaining sigma slice.

Preview uses the last `denoised_output` prediction, decodes the full video and displays one first frame. This is not a finalized first frame and not a single-frame decode optimization.

## External workflow ownership

The new pair does not own:
- model loading
- Turbo LoRA
- prompt construction
- Reference/Keyframe conditioning
- CFG
- scheduler construction
- resolution or duration
- downstream decode/save

These stay in the user's existing workflow.

## Guider and condition ownership

Native Core Basic, CFG and DualCFG guider families are supported. The snapshot preserves their guidance scalar parameters and tensor-based conditioning, including native H3 reference/keyframe tensors and token tags.

The v1.1.1 compatibility fix validates the supported guider contract/MRO instead of exact class-object identity because ComfyUI may instantiate the stock class from a separately loaded module object.

Live control/hook/custom objects are rejected with an adapter requirement rather than silently removed. `Guider_DualModel` is also rejected until a two-model resume adapter exists.

## Approval and output traversal

Both pairs use explicit reviewed-State-ID approval. GO submits the selected Continue plus reachable output nodes through downstream data edges, so Decode → CreateVideo → SaveVideo chains work. Another Draft/Continue branch is a hard boundary.

Upstream changes invalidate the reviewed draft. Postprocessing or save-path changes do not.

## Current supported resume contract

- Model: native MiniMax H3
- Latent: joint H3 video+audio NestedTensor, batch 1
- Guider: Core BasicGuider / CFGGuider / DualCFGGuider
- Sampler: Core Euler, churn=0
- SIGMAS: external, strictly descending H3 flow schedule ending in zero
- No noise_mask

`res_multistep` and other history-dependent solvers are not silently approximated. They need solver-history capture before they can be claimed exact.
