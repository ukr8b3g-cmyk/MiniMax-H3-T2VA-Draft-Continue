# Validation

Date: 2026-09-19.

## Confirmed GPU evidence

The user confirmed:
- Core proof of concept Preview 3/6 → Continue 3/6 → final video
- generic Sampler-level integration works in the real ComfyUI_W environment
- the Core loader identity fix passes the real workflow

These establish Phase 1 Generic Draft/Continue as GPU PASS.

## Phase 2 implementation status

Native Reference Transparency is implemented but not yet GPU-certified.

Implemented host contracts:
- no extra Reference input ports
- native `minimax_refs` stays inside external CONDITIONING
- reference tensors are snapshotted without re-encoding
- reference order/kind/shape metadata is reported
- dedicated reference payload hash is stored
- content/count/order/metadata changes invalidate stale GO
- existing whole-conditioning integrity checks remain active

## Phase 2 R0-R3

- R0: no Reference baseline
- R1: one native image Reference
- R2: multiple native References
- R3: change Reference content/count/order after Preview and confirm stale GO is rejected

See [REFERENCE_GATE.md](REFERENCE_GATE.md).

## What is and is not certified

- Phase 1 generic Draft/Continue: **user GPU PASS**
- Core loader identity fix: **user GPU PASS**
- Phase 2 Native Reference host regression: **CI/host gate**
- Phase 2 Native Reference real H3 inference: **pending GPU gate**
- arbitrary samplers/custom guiders/masks/live controls: **not supported**

## Development tests

```sh
PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Host tests are contract tests and do not replace real MiniMax H3 GPU inference.
