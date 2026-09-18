# MiniMax H3 Draft Continue

**Review one predicted first frame, then continue the same H3 generation.**

[日本語](README_JA.md) · [Workflow integration](docs/WORKFLOW_INTEROP.md) · [Validation](docs/VALIDATION.md)

## v1.1.1 compatibility fix

ComfyUI can register the stock `BasicGuider` from a separately-loaded extension module instance. v1.1.0 compared Python class identities and could therefore reject the ordinary Core `BasicGuider` before sampling. v1.1.1 validates the supported Core guider contract/MRO instead and snapshots the actual graph instance, while still rejecting dual-model/custom guiders that need a dedicated resume adapter.

## Insert into your existing workflow

Replace the sampling block, not the entire workflow:

```text
Your NOISE / GUIDER / SAMPLER / SIGMAS / H3 AV LATENT
                             ↓
                      H3 Draft Sampler  ← video VAE
                      one-image Preview
                             ↓ state
                     H3 Continue Sampler
                             ↓ standard LATENT
        Your video/audio VAE Decode → postprocess → Save
```

The pair does not rebuild prompts, conditioning, CFG, geometry, noise sources or schedules. Model loading, Turbo LoRA and conditioning (including native H3 references/keyframes) remain upstream. Decoding and saving remain downstream. Continue returns the same two LATENT port names/order as SamplerCustomAdvanced: `output`, `denoised_output`.

The original **H3 T2VA Draft / H3 T2VA Continue** integrated pair remains available.

### Start

Install this repository into `ComfyUI/custom_nodes`, restart ComfyUI and refresh the browser. No additional pip/runtime dependencies or model downloads are required.

Recommended proven concept baseline: shared 4-step Turbo LoRA at 1.0, 6 total steps, Preview after 3, Continue for the remaining 3. The generic sampler pair currently resumes native Core Euler without churn.

Click **Preview**, review one image, then click **GO · Continue this draft**. **New seed + Preview** changes only a directly connected Core RandomNoise seed. For other noise providers, edit the upstream seed yourself.

### Scope and safety

Standard ports do not mean all-model/all-sampler support. This version targets native MiniMax H3 joint AV, batch=1; Core Basic/CFG/DualCFG guiders; Core Euler without churn; valid descending H3 flow SIGMAS ending at zero. Live ControlNet/hook objects, masks and multistep solver histories need dedicated adapters.

State is session-bound and integrity checked. GO binds to the reviewed State ID and refuses changed inputs, changed runtime bindings, mutated payloads or a regenerated unseen draft. No new random noise, image re-encoding, automatic approval, forced unload or disk-state import is used.

The user-confirmed Core proof-of-concept passed Preview → Continue → video generation. The v1.1.1 guider compatibility fix is covered by host regression tests; rerun the actual H3 GPU workflow after updating to certify the fix in your environment.
