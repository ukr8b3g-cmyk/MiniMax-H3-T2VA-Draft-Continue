# Architecture — legacy pair and v1.1 sampler adapters

The sections below describe both the retained v1.0 integrated pair and the v1.1 standard-port pair.

## Frozen baseline / deliberate scope

The approved concept is a native T2VA run with a shared 4-step Turbo LoRA, 6 total Euler/simple steps, a split after 3 transitions and ONE Frame 0 preview. Both AV streams exist at full target length from the start. The user reported successful video continuation. This implementation does not convert to I2VA, extend a 5-frame draft, change models on GO, rewrite prompts or introduce a second planner.

## Why the boundary representation matters

`SamplerCustomAdvanced.output` and `denoised_output` are different values.

For CONST flow, Core's KSAMPLER returns `inverse_noise_scaling(sigma_end, x) = x / (1 - sigma_end)`, then converts to the external latent format. At resume, zero noise with `noise_scaling(sigma_start, 0, latent) = (1 - sigma_start) * latent` reconstructs the sampling state. H3 also applies audio-scale conversion through the model's whole-pack latent interface.

We keep **the exact Core output**, including video AND audio. No extra `(1-sigma)` factor, no raw callback tensor substitution, no audio-only repacking math, no image encode and no added random noise. The host performs both model-space conversions. The same seed is retained as metadata even on the zero-noise continuation.

`denoised_output` is used **only for viewing**. The last callback estimate is produced at the evaluation before the split boundary. It is an estimate, not an already finalized Frame 0.

## Standard-port sampler pair

`H3DraftSampler` receives external NOISE / GUIDER / SAMPLER / SIGMAS / LATENT and therefore can be inserted where `SamplerCustomAdvanced` normally sits. `H3ContinueSampler` returns standard LATENT outputs and leaves decode/post-processing/save outside the custom node.

The generic pair never rebuilds external conditioning, CFG, noise sources, schedules, reference tensors or AV geometry. It snapshots the actual supported Core guider instance, the sampler and the exact remaining sigma schedule.

## Core GUIDER compatibility

The sampler pair accepts Core `BasicGuider`, `CFGGuider` and `DualCFGGuider` by their supported contract/MRO rather than Python class-object identity. This matters because ComfyUI's extension loader can register the stock class from a separately-loaded module instance.

The snapshot is made from the actual graph instance with a cloned primary ModelPatcher/model-options and frozen native conditioning. `Guider_DualModel`, any guider carrying a second `uncond_model_patcher`, and unknown custom guiders remain rejected until they have an explicit resume adapter.

## State ownership and safety

State tensors are detached CPU clones. Comfy's cache owns the state object's lifetime; there is no extra global model or tensor cache. A unique `state_id` identifies each successful Draft. Frozen dataclasses plus payload hashing reject mutation. A per-state lock rejects concurrent continuation.

V1 does not load untrusted state files, pickle objects, arbitrary paths or custom REST endpoints. There is no disk import/export mode.

## Queue / GO behavior

Preview queues only the selected Draft and its upstream dependencies. GO checks the current upstream graph SHA against the reviewed state, then queues only that Continue and reachable output nodes. The browser changes `go=true` and `approved_state_id` only in the submitted API request, not in stored widgets.

Backend validation remains authoritative if JavaScript is bypassed.

## Remaining compatibility boundary

Native MiniMax H3 joint AV, single batch, Core Euler without churn, external valid H3 flow SIGMAS. Multistep solver history, live ControlNet/hooks, multi-model guiders and noise_mask require dedicated resume adapters. Unsupported inputs fail closed rather than being silently approximated.
