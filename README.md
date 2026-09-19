# MiniMax H3 Draft Continue

**Review one predicted first frame, then continue the same H3 generation.**

[日本語](README_JA.md) · [Workflow integration](docs/WORKFLOW_INTEROP.md) · [Reference GPU gate](docs/REFERENCE_GATE.md) · [Validation](docs/VALIDATION.md)

## v1.4.0 — START → END Layout Transition (Phase 3B)

The structured audit now accepts real START→END geometry from H3 Structured Canvas. The upstream Prompter already compiles matching `transition.end_boxes` into model-facing `start_bbox / end_bbox`; Draft-Continue now fingerprints that same transition instead of rejecting it.

Supported Phase 3B contract:

- 1–3 slots A/B/C
- same slot set at START and END
- fixed Canvas width/height and normalized 0..1000 xyxy coordinates
- known Timeline Experimental v3/v4 wrapper
- no explicit MID
- no Multi-Key keyframes

The report adds `start_hash`, `end_hash`, `transition_hash`, and `moved_slots`. Changing START, END or the exact compiled prompt after Preview invalidates the old GO before Continue sampling.

[Phase 3B details](docs/PHASE3B_START_END.md) · [START→END workflow example](examples/H3-START-END-Layout-Draft.json)

Phase 3A static START + Timeline no-op compatibility remains supported and has user-confirmed GPU/video PASS.

## v1.3.1 — START layout audit + Timeline Experimental compatibility

Timeline Experimental automatically serializes a loaded static Canvas as `transition + timeline_experimental`. v1.3.1 accepts that wrapper only when it is semantically a no-op: END must equal START and there must be no explicit MID or Multi-Key data. The wrapper is then canonicalized to the same START IR/hash as the original static Canvas.

Real END movement, explicit MID, Multi-Key data, unknown transition metadata, and unsupported timeline versions still fail closed instead of being discarded.

## v1.3.0 — START layout audit (Phase 3A)

An optional **H3 Structured Layout Audit (START)** node attaches existing Canvas layout and exact compiled-prompt provenance to native CONDITIONING. Draft/Continue ports, conditioning tensors, the sampler, Reference processing and model selection are unchanged. The Canvas repository is not modified or imported by this package.

Connect the same Prompter STRING to the native H3 conditioner and the audit node, then connect audited CONDITIONING to your existing Guider. Changed layout/prompt metadata rejects stale GO. This is an integrity check, not stronger BBOX enforcement or proof that arbitrary conditioning was encoded from the supplied text.

[START wiring and scope](docs/STRUCTURED_LAYOUT.md) · [日本語ガイド](docs/PHASE3A_JA.md) · [UI workflow example](examples/H3-START-Layout-Draft.json)

Phase 3A supports 1–3 static START boxes in A/B/C and has user-confirmed Preview → GO → final-video GPU PASS. Real END movement is handled by Phase 3B; MID/Multi-Key remains later.

## v1.2.0 — Native Reference Transparency

The generic Draft/Continue pair now formally preserves MiniMax H3 native Reference conditioning.

No Reference ports are added to these nodes. Keep using the normal upstream H3 conditioning nodes.

```text
MiniMax H3 native conditioning / Reference
                  ↓
      NOISE / GUIDER / SAMPLER / SIGMAS / AV LATENT
                  ↓
           H3 Draft Sampler
              Preview
                  ↓ state
          H3 Continue Sampler
                  ↓ standard LATENT
      your normal Decode / postprocess / Save
```

Core `minimax_refs` blocks remain inside CONDITIONING. Draft-Continue snapshots and fingerprints them without converting or re-encoding them.

An approved Draft is invalidated if native Reference content, count, order, kind or native metadata changes after Preview.

The Draft report includes:
- Reference count and kind distribution
- original ordered Reference list
- Reference tensor shapes/dtypes
- Reference payload SHA-256
- `reference_reencoded=false`

Phase 1 Generic Draft/Continue is user GPU PASS. Phase 2 Reference support is implemented and host-tested; the R0-R3 real-GPU gate is still pending.

## Existing workflow integration

Replace the sampling block, not the whole workflow:

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

The pair does not rebuild prompts, conditioning, CFG, geometry, noise sources or schedules. Model loading, Turbo LoRA, native H3 Reference/Guide/Keyframe conditioning remain upstream. Decoding and saving remain downstream.

Recommended proven concept baseline: shared 4-step Turbo LoRA at 1.0, 6 total steps, Preview after 3, Continue for the remaining 3. The generic sampler pair currently resumes native Core Euler without churn.

## Scope

- native MiniMax H3 joint AV latent, batch=1
- Core BasicGuider / CFGGuider / DualCFGGuider
- Core Euler without churn
- external H3 flow SIGMAS
- native tensor/scalar `minimax_refs`
- state bound to the current ComfyUI backend session
- 512 MiB Draft-state payload budget

Live ControlNet/hook objects, noise masks, custom/multi-model guiders and multistep solver history need dedicated adapters.

No additional pip/runtime dependencies or model downloads are required.
