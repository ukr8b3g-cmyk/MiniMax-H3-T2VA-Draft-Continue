# Validation

Date: 2026-09-18.

## Concept GPU evidence

The user confirmed the Core-only proof of concept:
- MiniMax H3 T2VA
- shared 4-step Turbo LoRA
- 6 total steps
- Preview after 3
- Continue for the remaining 3
- final video generation succeeds

That proves the Preview → Continue concept in the tested Core workflow.

## v1.1.1 compatibility fix

A real ComfyUI 0.36.0 / Python 3.13.12 run reached `H3DraftSampler` and failed before denoising because v1.1.0 compared the incoming stock `BasicGuider` by exact Python class identity even though the workflow used Core BasicGuider.

v1.1.1 replaces that identity check with supported Core contract/MRO validation and snapshots the actual incoming guider instance. Host regression tests simulate separately-loaded `Guider_Basic` and `CFGGuider`; a `Guider_DualModel` lookalike remains rejected.

## What is and is not certified

- Core proof-of-concept Preview → Continue → video: **user GPU PASS**
- v1.1.1 class-identity regression: **host regression PASS**
- v1.1.1 fix on the user's actual H3 GPU workflow: **rerun required**
- arbitrary samplers / custom guiders / masks / live controls: **not supported by the current exact-resume contract**

## Safety checks

The implementation verifies:
- reviewed state ID
- process/session scope
- upstream graph signature
- model/LoRA runtime binding
- guider and sampler signatures
- source AV latent, SIGMAS and noise identity
- state payload integrity
- joint video/audio geometry
- no new random noise on Continue

Unsupported inputs are rejected before continuation rather than silently changed.

## Reproduce development contract tests

```sh
PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Browser tests are development-only mocked-host checks; they are not actual ComfyUI GPU inference.
