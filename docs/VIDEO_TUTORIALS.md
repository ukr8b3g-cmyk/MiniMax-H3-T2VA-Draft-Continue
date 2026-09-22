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

## Two-reference I2VA — Cyberpunk

[Watch the English I2VA tutorial on YouTube](https://youtu.be/HopdznXTFjk) — approximately 1 minute 55 seconds, 1440p workflow-only recording, English stock female narration, captions and quiet original instrumental music. Rendering waits are accelerated and labeled; operations and review steps remain visible. An English narration subtitle track is included on YouTube.

[Download the workflow and both images (ZIP)](https://raw.githubusercontent.com/ukr8b3g-cmyk/MiniMax-H3-T2VA-Draft-Continue/main/examples/H3-I2VA-BBOX-Cyberpunk-v1.zip) · [Workflow JSON](../examples/H3-I2VA-BBOX-Cyberpunk-v1.json) · [Courier reference](../examples/assets/cyberpunk/h3-cyberpunk-courier.png) · [Rover reference](../examples/assets/cyberpunk/h3-cyberpunk-rover.png)

![Actual two-reference cyberpunk output](assets/h3-i2va-preview.jpg)

This clean example has 23 nodes in six groups. The supplied AI-generated reference images define the silver-haired courier and the small amber-lit delivery rover. They are **subject references, not the first and last video frames**. The workflow and both images are included in the download above.

1. Extract the ZIP and open `H3-I2VA-BBOX-Cyberpunk-v1.json` in ComfyUI. Choose the model files installed locally.
2. Load `h3-cyberpunk-courier.png` in **A / Silver-haired Courier** and `h3-cyberpunk-rover.png` in **B / Amber Service Rover**.
3. Keep the Load Image outputs connected to the Canvas A/B reference inputs. The Canvas `layout` output goes to the Structured Prompter, Layout Audit, and **H3 Structured Reference to Video** conditioner. Use a version of [H3 Structured Canvas](https://github.com/ukr8b3g-cmyk/H3-Structured-Canvas) that supplies these nodes and its START/END timeline.
4. Set START/END boxes and match the scene/slot descriptions. The example moves the rover slightly left while the courier turns toward it.
5. Confirm **UI 1.7.10 · VERIFIED**, click **Preview**, inspect **READY · 3/6**, then **GO**. Review the final video after Decode/Save and COMPLETE.

The model/LoRA/encoder/VAE and seed match the T2VA table above. This version uses **768 × 512, 124 frames, 24 fps**, six Euler/simple steps, with Preview at three. The JSON has GO false and no saved Approval; recipients must generate a fresh Preview. Model weights are not included.

### Recorded check, 2026-09-22

Preview completed successfully and the UI reached READY 3/6. GO reused the cached upstream nodes and Draft, resumed three sampling steps, and completed the connected Decode/Save chain. The saved output is approximately 5.17 seconds. The courier and rover remain identifiable and separate while the rover approaches the courier. Layout is guidance, not a promise of exact pixel positions.

Recorded environment: ComfyUI 0.37.0, Frontend 1.52.7, Draft/Continue runtime and UI 1.7.10, RTX 5060 Ti 16 GB. The workflow-only OBS recording is 2560 × 1440 at 30 fps; this tutorial resolution is separate from the generated example's 768 × 512 resolution.

This is one demonstration cycle, not C9 memory endurance. C9 remains skipped and C11 remains unverified.
