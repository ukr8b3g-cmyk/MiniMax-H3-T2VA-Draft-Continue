# Phase 4C qualification status

Updated: 2026-09-22. Runtime / UI build: **1.7.10**.

| Cases | Recorded status |
|---|---|
| C0–C8 | PASS — user-confirmed live results |
| C9 — Memory Endurance | PASS — five consecutive Preview → GO → Decode/Save cycles |
| C10 — Browser / Backend boundary | PASS — user-confirmed, code unchanged |
| C11 — Production regression | PASS — production lifecycle and visual-output checks |
| Phase 4C overall | **PASS / COMPLETE** |

C9 completed five fresh Preview → READY 3/6 → GO → Continue → Decode/Save cycles on the real GPU backend. All five State IDs were distinct, all five MP4 files were saved with 124 readable frames at 24 fps, every Queue returned to 0/0, and no OOM, NaN, crash, or `execution_error` occurred. Settled RAM was 41.72 → 41.29 → 41.17 GB at runs 1/3/5. Settled VRAM was 14,916 → 15,003 → 15,025 MiB, a +109 MiB change (about 0.7%); across all recorded endpoints there was no significant cumulative VRAM growth or leak trend. [Detailed C9 record](C9_GPU_ENDURANCE.md)

C8 functional GPU acceptance was confirmed after the local syntax correction: Continue stays pending through downstream Decode/Save, reaches COMPLETE only after prompt-wide execution success, and clears approval on downstream failure. The extra-brace correction is included in main at `83edaa9f2976887c4127d543456a80321b84180c`.

C10 confirmed that browser reload and backend-session changes do not restore the old approval.

C11 closed the production regression with two normal completion cycles, interrupt recovery, duplicate-Queue prevention, a successful third Preview, and no OOM/NaN. The production graph included Reference + Structured BBOX + Multi-Key. Final output inspection confirmed stable reference identity, separate A/B subjects, and the intended spatial/motion progression. The checked outputs were 512 × 768, 124 frames, 24 fps, and decoded successfully.

Phase 4C is therefore complete. These qualification results do not change sampling math, Euler/simple, SIGMAS, noise, Reference, BBOX, Multi-Key, or Decode/Save contracts.
