# Phase 3A — START Layout Transparency / v1.3.0

## Scope

One optional upstream adapter, **H3 Structured Layout Audit (START)**, attaches provenance to native CONDITIONING. The existing Draft/Continue sampler ports and sampling equations are unchanged. Ordinary workflows without the adapter continue without structured metadata.

The provider was inspected at `ukr8b3g-cmyk/H3-Structured-Canvas` commit `46c86f9e033acf16d20cae18b64876522e02d7d4`. Its actual output is `H3_LAYOUT`, schema `h3_structured_canvas/0.9`, with `canvas`, `boxes`, `slot`, and `bbox_2d` in normalized 0..1000 xyxy coordinates. The earlier proposed `h3_structured_ir_v1` is **not** treated as an existing provider API.

No Canvas source, compiler, experimental branch, or Timeline behavior is changed. No extra pip dependency is added. Canvas is needed only for workflows that use its layout output.

## Wiring

```text
Canvas.layout ───────────────→ Structured Prompter.layout
     │                                │ exact prompt STRING
     │                                ├────────→ Core H3 conditioner.prompt
     │                                └────────→ Layout Audit.compiled_prompt
     └─────────────────────────────────────────→ Layout Audit.layout
Core H3 conditioner.positive ───────────────────→ Layout Audit.positive
Layout Audit.positive → existing Basic/CFG Guider → H3 Draft Sampler
Core H3 conditioner.LATENT ─────────────────────→ H3 Draft Sampler
H3 Draft Sampler → reviewed State → H3 Continue Sampler → ordinary Decode/Save
```

Connect the same Prompter STRING to the conditioner and audit node; connect Canvas width/height to the conditioner. The adapter never creates conditioning from an instruction and never replaces the model-facing prompt. `examples/H3-START-Layout-Draft.json` supplies this wiring for two subjects, no image Reference, shared installed 4-step Turbo, 6 total / 3 preview / Euler / simple.

**Important:** metadata cannot prove which text originally produced an arbitrary CONDITIONING tensor. The report therefore says `prompt_binding_verified=false`. This is an audit bridge, not a new grounding model or a guarantee of BBOX compliance.

## What is stored

`h3_structured_source` is top-level CONDITIONING metadata, not `model_conds`. It carries a bounded primitive copy of START layout, exact compiled prompt, provider/schema/scope, canonical IR hash, and exact UTF-8 prompt hash. Existing state freezing and whole-payload hashing protect it with the original conditioning. There is no extra image/model cache or new persistent state format.

Canonicalization sorts dictionary keys and normalizes equivalent numeric values (`100` and `100.0`). It does **not** round BBOX coordinates. Canvas `grid`, `show_boxes`, `active_slot`, derived aspect display, box `ui_color`, and warnings are excluded. `_h3_slot_images` is excluded without reading/cloning it: actual reference payloads remain covered by Phase 2. Descriptions, labels, IDs, slot order, and other primitive semantic fields are retained.

The existing conservative workflow fingerprint/cache is not relaxed. Changing a serialized UI-only field can still require re-Preview, even when the semantic IR hash is unchanged.

## Validation / stale GO

Before Draft sampling: validate metadata shape/hash and Canvas-versus-latent dimensions. At state capture and before Continue: compare the current and stored structured provenance. Layout, slot, count, order, prompt, or metadata removal/addition changes reject stale GO; existing approval, reference, payload, and model checks remain in force.

Report: `state.structured_layout` on Draft, `structured_layout` on Continue. Each item lists provider, schema, scope, slots, IR hash and prompt hash. `semantic_accuracy_verified=false`: this is metadata integrity, not a semantic quality score.

## Deliberate boundary

Phase 3A accepts **1–3 START boxes, A/B/C, normalized 0..1000 xyxy**. No coordinate clamps or implicit resizes. Transition, Timeline/Multi-Key metadata, overscan, unknown schemas, live objects, nonfinite values, and oversized metadata are rejected by the opt-in adapter. They are not silently stripped. Existing generic workflows without this adapter are not reclassified as START-only.

END / Multi-Key / numeric depth enforcement / Motion Graphics / combined Reference+BBOX quality certification remain later phases. The audit itself adds no spatial control; the upstream Canvas compiler and H3 determine visual results.

## Verification status

New local tests cover canonicalization, exact text, no tensor changes, state capture/restore, stale approval, Reference compatibility, and sample graph wiring. Local lifecycle tests use CPU host doubles, not H3 weights. State/engine/contract test bases were matched to the GitHub main blob hashes. Existing CI runs the repository tests against the committed source.

**Real ComfyUI, Canvas browser interaction, GPU inference and BBOX adherence for Phase 3A have not been verified here.** Previous user-reported operation remains separate evidence, not certification of this new adapter.

## B0–B3 real-device gate

B0: Existing workflow without the adapter still previews and completes. B1: One START subject, Preview then GO. B2: Two/three subjects, Preview then GO; assess visual placement separately from execution success. B3: Change BBOX or prompt after Preview and try old GO; it must stop before Continue sampling. Depending on cache/UI detection the message may mention upstream changes, unreviewed State ID, or `Structured layout changed after Preview`.

After a change, create a new Preview before GO. No new seed sweep, new model, or extra GPU experiments are required for this gate.
