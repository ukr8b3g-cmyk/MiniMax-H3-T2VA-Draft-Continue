# Structured Layout Transparency — Phase 3A / 3B

## Architecture

The optional **H3 Structured Layout Audit** attaches provenance to native CONDITIONING. Draft/Continue sampler ports and sampling equations remain unchanged.

The provider contract is H3 Structured Canvas schema `h3_structured_canvas/0.9`.

```text
Canvas.layout ───────────────→ Structured Prompter.layout
     │                                │ exact prompt STRING
     │                                ├────────→ native H3 conditioner.prompt
     │                                └────────→ Layout Audit.compiled_prompt
     └─────────────────────────────────────────→ Layout Audit.layout
native conditioner.positive ───────────────────→ Layout Audit.positive
Layout Audit.positive → Guider → H3 Draft Sampler → State → H3 Continue Sampler
```

The audit never recompiles the prompt, changes conditioning tensors, changes Reference payloads, or creates a second layout representation for the model.

## Phase 3A — static START

Static START layouts with 1–3 A/B/C boxes are canonicalized and hashed.

Timeline Experimental automatically wraps static data in `transition + timeline_experimental`. When END equals START and MID/Multi-Key is empty, that wrapper collapses to the exact same START IR/hash.

Phase 3A is user GPU/video PASS.

## Phase 3B — START → END

When END differs from START, the transition is retained.

Requirements:

- START and END have the same A/B/C slot set
- START/END Canvas geometry is identical
- normalized 0..1000 xyxy BBOX
- no explicit MID
- no Multi-Key keyframes
- known Timeline Experimental v3/v4 shell only

The canonical IR keeps:

```json
{
  "canvas": "...fixed start canvas...",
  "boxes": "...START boxes...",
  "transition": {
    "end_canvas": "...same canvas geometry...",
    "end_boxes": "...END boxes..."
  }
}
```

The audit report exposes:

- `scope = start` or `start_end`
- `ir_hash`
- `prompt_hash`
- `start_hash`
- `end_hash`
- `transition_hash`
- `slots`
- `moved_slots`

A change to START, END, slot identity or the exact compiled prompt invalidates the reviewed Draft before Continue sampling.

## Provider semantics

H3 Structured Canvas compiler reads `transition.end_boxes`. When a slot's Prompter motion is `start_end`, it emits model-facing `start_bbox / end_bbox` and a trajectory instruction.

Draft-Continue does not reproduce this compiler behavior. It only binds the reviewed Draft to the already-produced conditioning and its provenance.

## Deliberate boundary

Phase 3B does not accept explicit MID or Multi-Key semantics. Those belong to Phase 3C.

It also does not claim that Frame 0 Preview proves the eventual END pose. Preview remains useful for START composition/identity review; the State integrity layer ensures GO continues with the same reviewed START→END contract.

See [PHASE3B_START_END.md](PHASE3B_START_END.md) for the real-device gate.
