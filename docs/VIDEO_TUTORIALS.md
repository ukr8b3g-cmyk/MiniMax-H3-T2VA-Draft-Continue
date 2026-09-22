# Video tutorials and distributable workflows

## T2VA — Neon BBOX, Preview and Continue

[Watch the English tutorial](https://youtu.be/4cMJKsY5B_o) · [Download the workflow](https://raw.githubusercontent.com/ukr8b3g-cmyk/MiniMax-H3-T2VA-Draft-Continue/main/examples/H3-BBOX-Draft-Continue-Neon-v1.json)

This is the repository's clean tutorial template. It contains 21 nodes in five groups, with no disconnected test branch. The distributed copy uses a larger BBOX editing area than the recorded take; generation settings are unchanged. No images, model weights, reviewed State IDs or approval are bundled in the workflow.

### Setup

1. Use a ComfyUI installation that provides the native MiniMax H3 model, conditioning, video and audio nodes.
2. Install this repository and [H3 Structured Canvas](https://github.com/ukr8b3g-cmyk/H3-Structured-Canvas), which supplies the BBOX editor, timeline and structured prompter.
3. Download the JSON and open it in ComfyUI. Select your installed model files in the loader nodes; the example filenames are listed below.
4. Confirm the Draft/Continue UI build is verified, edit the scene and A/B descriptions, and set START and END boxes.
5. Click **Preview**, review `READY · 3/6`, then click **GO**. Wait for Decode/Save to finish and `COMPLETE` to appear. The final video is available in the output node.

The template opens with GO false and an empty approval ID. A new Preview is required. Input changes after Preview require another Preview.

### Recorded settings

| Setting | Value |
|---|---|
| Model | `minimax/DasiwaMinimaxH3_dasiwaHybridV2_int8.safetensors` |
| Turbo LoRA | `minimax/minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors`, strength 1 |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` |
| Output | 512 × 768, 124 frames, 24 fps, approximately 5.17 seconds |
| Sampling | Euler / simple, 6 total steps, Preview at step 3 |
| Seed | 6367846465849230, fixed |
| References | None; text slots A and B enabled |
| Draft/Continue runtime and UI | 1.7.10 |

Model weights are not included. Choose valid local filenames and follow their respective model licenses. The filenames above document the actual recorded setup rather than a guarantee for every model variant.

### What the tutorial shows

- The BBOX timeline previews layout positions, not generated video.
- The Draft image is an intermediate first-frame estimate, not final image quality.
- GO resumes the remaining sampling steps of the same generation. It does not extend the clip's duration.
- Generation waits are accelerated and labeled in the tutorial. UI actions remain visible.
- The tutorial uses English synthetic female narration and original instrumental background music. The example output is AI-generated.

The real T2VA recording completed Preview → GO → Decode/Save with an empty queue afterward. The subsequent distribution copy enlarged the editor and changed presentation only. This demonstration is not a five-cycle memory endurance test; [C9 was explicitly skipped](PHASE4C_STATUS.md).

## Two-reference I2VA tutorial

A separate cyberpunk example with two supplied reference images is in preparation. Its workflow, assets and video link will be added after the corresponding checks; the T2VA download above remains a text-only template.
