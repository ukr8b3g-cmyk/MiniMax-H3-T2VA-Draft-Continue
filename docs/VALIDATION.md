# Validation

Date: 2026-09-19.

## Confirmed GPU evidence

User-confirmed real ComfyUI/H3 passes:

- Phase 0 concept: Preview 3/6 → Continue 3/6 → final video
- Phase 1 generic Sampler-level integration
- Core loader identity fix
- Phase 2 Native Reference Transparency
- Phase 3A static START structured-layout audit, including Timeline Experimental no-op wrapper compatibility
- Phase 3A final video generation

These are real-device execution results. Visual placement quality remains model-dependent and is not converted into a numeric quality certification.

## Phase 3B implementation status

START→END layout-transition auditing is implemented and host-tested. Real GPU validation is pending.

Host contract:

- static START remains backward compatible
- real `transition.end_boxes` is preserved
- START/END use the same A/B/C slot set
- one fixed Canvas geometry is required
- explicit MID and Multi-Key remain rejected
- START/END/prompt changes invalidate stale GO
- no conditioning tensor rewrite or re-encode is introduced

## Phase 3B GPU gate

- T0: static START regression → Preview → GO → final video
- T1: one moving slot START→END → Preview → GO → final video
- T2: two/three moving slots → Preview → GO → final video
- T3: after Preview, change only END BBOX → old GO must be rejected before Continue sampling
- T4: create a new Preview after the END change → GO must complete

The Preview is still Frame 0 / START-oriented. Phase 3B does not claim that a single Preview verifies the final END pose; it verifies that the reviewed Draft is bound to the exact same START→END conditioning contract.

## Remaining boundary

Not yet Phase 3B:

- explicit MID
- Multi-Key Timeline
- numeric depth enforcement
- arbitrary live ControlNet/hooks
- noise masks
- custom/multi-model guiders
- multistep solver-history resume

## Development tests

```sh
PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Host tests do not replace real MiniMax H3 GPU inference.
