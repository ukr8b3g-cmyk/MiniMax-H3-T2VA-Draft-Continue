# Changelog

## 1.1.1 - 2026-09-18

- Fix Core `BasicGuider` rejection caused by extension-loader class identity differences.
- Validate supported Core guider families by contract/MRO instead of exact Python class object.
- Snapshot the actual graph guider instance and clone its primary ModelPatcher/options.
- Keep `Guider_DualModel` and unknown custom/multi-model guiders fail-closed until a dedicated resume adapter exists.
- Add regression tests reproducing separately-loaded Core guider classes.

## 1.1.0 - 2026-09-18

- Add generic Sampler-level `H3 Draft Sampler` / `H3 Continue Sampler` pair.
- Preserve external NOISE / GUIDER / SAMPLER / SIGMAS / LATENT semantics and standard LATENT outputs.
- Keep the integrated v1.0 Preview / GO nodes for compatibility.
