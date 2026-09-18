# Phase 2 — Native Reference GPU Gate

Status: implementation complete, real H3 GPU validation pending.

## Design contract

Draft-Continue does not add Reference ports and does not rebuild Reference conditioning.

```text
MiniMaxH3ReferenceToVideo / native H3 conditioning
                    ↓
          GUIDER + H3 AV LATENT
                    ↓
             H3 Draft Sampler
                    ↓
             reviewed Draft State
                    ↓
            H3 Continue Sampler
                    ↓
              standard LATENT
```

The Core `minimax_refs` list remains in CONDITIONING unchanged. Draft-Continue only snapshots and fingerprints it.

## R0-R3 GPU gates

### R0 — no Reference
Run the existing proven baseline. Preview and Continue must behave exactly as before.

### R1 — one image Reference
Use one native `MiniMaxH3ReferenceToVideo` image Reference. Confirm:
- Preview appears at the selected split.
- report shows `native_references.count = 1` and `kind=image`.
- GO completes the same Draft.
- no Reference re-encode is performed by Draft-Continue.

### R2 — multiple References
Use at least two native References. Prefer image + image first, then mixed Reference types if available. Confirm:
- order is preserved in `native_references.items`.
- Preview completes.
- GO completes.
- final workflow receives normal LATENT outputs.

### R3 — stale GO must fail
After Preview, change one Reference source and try GO without generating a new Preview. Repeat for:
1. Reference content change,
2. Reference count change,
3. Reference order change.

Expected error contains:

```text
Native H3 reference conditioning changed after Preview
```

Then generate a new Preview and GO again.

## PASS condition

Phase 2 is GPU PASS only after R0, R1, R2 and R3 all pass on the real ComfyUI/H3 environment.

Host regression tests are necessary but are not a substitute for this GPU gate.
