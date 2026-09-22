# C9 GPU Memory Endurance

Date: 2026-09-22

Runtime: ComfyUI 0.37.0 / Frontend 1.52.7

Draft Continue: Runtime 1.7.10 / UI Build 1.7.10

GPU: NVIDIA GeForce RTX 5060 Ti 16 GB

Workflow: H3-BBOX-Draft-Continue-Neon-v1 (T2VA, 512 × 768, 124 frames, 24 fps)

## Result

**C9 PASS**

Five fresh Preview → READY 3/6 → GO → Continue → Decode/Save cycles completed. Every Preview produced a distinct State ID. Every GO history ended with `execution_success`, output node 24, no `execution_error`, and Queue 0/0.

The recovery script retained its original labels, so the official five-run mapping is:

| Official run | Recorded label | State ID | Saved output | Result |
| ---: | --- | --- | --- | --- |
| 1 | cycle02 | `e04d82edd53547cab7203ce21224095d` | `H3_C9_T2VA_cycle02_00001_.mp4` | PASS |
| 2 | cycle03 first run | `c538bf37f82b4b8db2972335d23b7a26` | `H3_C9_T2VA_cycle03_00001_.mp4` | PASS |
| 3 | cycle03 recorded rerun | `5019bbfd8bf1403f8d1c132880003910` | `H3_C9_T2VA_cycle03_00002_.mp4` | PASS |
| 4 | cycle04 | `21d0853071e44b4e92fbe32b1de31109` | `H3_C9_T2VA_cycle04_00001_.mp4` | PASS |
| 5 | cycle05 | `9fc678a33cd8416ba3b06eadcfbaf666` | `H3_C9_T2VA_cycle05_00001_.mp4` | PASS |

## Memory checkpoints

| Official run | Observed peak VRAM | Observed peak RAM | Settled VRAM | Settled RAM | Queue |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 15,576 MiB | 42.22 GB | 14,916 MiB | 41.72 GB | 0/0 |
| 3 | 15,679 MiB | 42.71 GB | 15,003 MiB | 41.29 GB | 0/0 |
| 5 | 15,636 MiB | 41.85 GB | 15,025 MiB | 41.17 GB | 0/0 |

Settled VRAM changed by +109 MiB from run 1 to run 5, about 0.7%. Settled RAM changed by -0.55 GB. The recorded settled VRAM endpoints were 14,916 → 15,003 → 14,997 → 15,025 MiB. Five cycles showed no significant cumulative VRAM growth or leak trend. The maximum observed temperature was 76 °C.

## Media and failure checks

All five official MP4 files passed `ffprobe` metadata checks at 512 × 768, 24 fps, 124 readable video frames, and approximately 5.17 seconds.

- OOM: none
- NaN: none
- Backend crash: none
- `execution_error`: none in the five official Preview/GO histories
- Queue residue: none
- Reused State ID: none
- Missing Decode/Save output: none

The browser had unrelated Workflow-tab focus changes during setup, so the endurance loop used the same T2VA API graph reconstructed from successful live Preview/GO history. It executed the same `H3DraftSampler`, `H3ContinueSampler`, video/audio decode, `CreateVideo`, and `SaveVideo` nodes. C8 had already established visible Frontend COMPLETE timing; C9 tested repeated GPU/backend lifecycle, State ownership, Decode/Save completion, Queue cleanup, and memory return.
