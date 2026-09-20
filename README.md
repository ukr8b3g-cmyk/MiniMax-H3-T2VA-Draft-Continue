# MiniMax H3 Draft Continue

**Review one predicted first frame, then continue the same H3 generation.**

[日本語](README_JA.md) · [Workflow integration](docs/WORKFLOW_INTEROP.md) · [Reference GPU gate](docs/REFERENCE_GATE.md) · [Validation](docs/VALIDATION.md)

## v1.7.0 — Lifecycle / Stale-State Management (Phase 4B)

Phase 4B keeps reviewed UI state across normal switches between already-open Workflow tabs, without serializing approval into the workflow file.

Stable session phases (`READY`, `STALE`, `COMPLETE`) are cached only in browser memory and restored through ComfyUI's graph lifecycle hooks. Closing and reopening a saved workflow still requires a new Preview.

While a Draft is `READY`, ComfyUI's `graphChanged` event now triggers a debounced upstream signature re-check. Execution-relevant edits immediately move the UI to `PREVIEW STALE / NEW PREVIEW REQUIRED`; the existing GO-time signature check remains the final guard.

Initial Phase 4B real-device testing was PARTIAL: B0/B1/B6 passed, while B2/B3/B7 exposed the lifecycle gaps now addressed on main. B4/B5/B8/B9/B10 remain pending.

## v1.6.0 — Preview / GO State UX (Phase 4A)

Draft and Continue now render as one synchronized browser review gate.

The UI exposes a small explicit state machine:

- `PREVIEW REQUIRED`
- `PREVIEW RUNNING`
- `READY TO GO`
- `PREVIEW STALE`
- `CONTINUING`
- `COMPLETE`
- error

Preview / New Seed / GO controls now live inside the status panel. GO is disabled unless the directly connected Draft has a valid reviewed Preview. GO still performs the full upstream graph signature check immediately before Queue, so the UI does not replace the existing safety contract.

Saved workflows never restore approval. Reopen always returns to Preview-required state.

Phase 4A is frontend-only: SamplerEngine, Draft State, Reference/Structured hashes, SIGMAS, noise and resume math are unchanged.

**Phase 4A A0–A7 is GPU/UI PASS** on RTX 5060 Ti. The final A4 retest verified terminal `REVIEWED / COMPLETE`, GO disabled, successful SaveVideo, and an empty Queue after completion.

## Phase 3D — Reference + Structured combined integration

Phase 2 Native Reference and Phase 3C Multi-Key have now been exercised together on the real GPU backend.

**Phase 3D: GPU PASS / COMPLETE.**

Passing combined cases include static START, START→END, 3-key and 7-key Multi-Key, two References, sparse A+C References, and a corrected re-Preview/Continue run after a per-slot Key-time change. All executed cases resumed at step 3 with no new noise, conditioning/Reference re-encode, or schedule rebuild.

Browser stale-state rejection D5–D9 is **PASS**, and browser valid GO→Continue→Save plus saved-workflow reload are **PASS (G11/G12)**. The separately defined Phase 3D visual-quality gate is also **user-confirmed PASS**. All Phase 3D gates are now closed.

[Phase 3D qualification status](docs/PHASE3D_COMBINED.md)

## v1.5.0 — Multi-Key Timeline Transparency (Phase 3C)

Draft-Continue now audits the H3 Structured Canvas Multi-Key v4 timeline without generating or interpolating keys itself.

Supported contract:

- A/B/C independent tracks
- START + up to 7 intermediate keys + END per slot
- `duration_seconds` 5.0–15.0
- `canonical_time = normalized_0_1`
- `interpolation = piecewise_linear`
- provider offscreen overscan up to -1000..2000
- exact compiled prompt remains bound to the same reviewed Draft

The report adds `scope=multi_key`, `timeline_hash`, `keyframe_hash`, `key_count`, `key_times`, and `duration_seconds`. Changing any key position/time/count/order, Duration, START, END or compiled prompt after Preview invalidates the old GO before Continue sampling.

[Phase 3C GPU gate](docs/PHASE3C_MULTIKEY.md) · [Multi-Key workflow example](examples/H3-MULTI-KEY-Layout-Draft.json)

Phase 3A and 3B remain supported. **Phase 3C M0–M6 is GPU PASS** on RTX 5060 Ti 16 GB: one/two-slot Multi-Key, maximum seven keys, stale Key/Duration rejection, and re-Preview continuation all completed. Subjective path-following quality was not graded.

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

Phase 3A static START + Timeline no-op compatibility remains supported and has user-confirmed GPU/video PASS. **Phase 3B T0–T4 is also GPU PASS** on RTX 5060 Ti 16 GB. T1/T2 exercised the same backend through server queue payloads; T0/T3/T4 included browser workflow runs. Subjective motion quality was not graded.

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

Phase 1 Generic Draft/Continue is user GPU PASS. Phase 2 Native Reference Transparency is also GPU PASS.

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
