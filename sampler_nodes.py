"""Standard Comfy sampling ports with an explicit review gate."""
from __future__ import annotations

import json
from .h3draft.sampler_engine import SamplerEngine

CATEGORY = "MiniMax H3/Draft Continue"


class H3DraftSampler:
    CATEGORY = CATEGORY
    RETURN_TYPES = ("IMAGE", "H3_SAMPLER_DRAFT_STATE", "STRING")
    RETURN_NAMES = ("preview_image", "draft_state", "report")
    FUNCTION = "preview"
    OUTPUT_NODE = True
    DESCRIPTION = ("Insert at SamplerCustomAdvanced: connect its NOISE/GUIDER/SAMPLER/SIGMAS/LATENT inputs. "
                   "Accepts external H3 conditioning, references/keyframes and CFG. One x0 Preview; no input image encoding. "
                   "Current resumable solver: native Euler without churn.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "noise": ("NOISE",), "guider": ("GUIDER",), "sampler": ("SAMPLER",),
            "sigmas": ("SIGMAS",), "latent_image": ("LATENT",), "video_vae": ("VAE",),
            "preview_steps": ("INT", {"default":3, "min":1, "max":999,
                "tooltip":"Number of sampling transitions before review. Must leave at least one transition in the supplied SIGMAS."}),
        }, "hidden": {"prompt":"PROMPT", "extra_pnginfo":"EXTRA_PNGINFO", "unique_id":"UNIQUE_ID"}}

    def preview(self, noise, guider, sampler, sigmas, latent_image, video_vae, preview_steps=3,
                prompt=None, extra_pnginfo=None, unique_id=""):
        engine = SamplerEngine()
        result = engine.draft_external(noise, guider, sampler, sigmas, latent_image,
            video_vae, preview_steps, prompt, unique_id)
        image = result.state.preview.clone()
        ui = engine.backend.preview_ui(image, prompt, extra_pnginfo)
        ui["h3_draft"] = [result.report]
        return {"ui":ui, "result":(image, result.state, json.dumps(result.report, ensure_ascii=False, indent=2))}


class H3ContinueSampler:
    CATEGORY = CATEGORY
    RETURN_TYPES = ("LATENT", "LATENT", "STRING")
    RETURN_NAMES = ("output", "denoised_output", "report")
    FUNCTION = "continue_latent"
    OUTPUT_NODE = True
    DESCRIPTION = ("Continue the reviewed H3 sampler state with zero new noise. Standard LATENT outputs "
                   "connect to your existing video/audio VAEDecode, upscale/refine and save branches. No decoder or saver is built in.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "draft_state": ("H3_SAMPLER_DRAFT_STATE", {"lazy":True}),
            "go": ("BOOLEAN", {"default":False, "label_on":"GO", "label_off":"Review first"}),
            "approved_state_id": ("STRING", {"default":"", "tooltip":"Filled by GO after Preview. API clients use the reviewed state.state_id."}),
        }, "hidden":{"prompt":"PROMPT"}}

    def check_lazy_status(self, go=False, approved_state_id="", draft_state=None, **kwargs):
        return ["draft_state"] if go and approved_state_id and draft_state is None else []

    def continue_latent(self, go=False, approved_state_id="", draft_state=None, prompt=None):
        if not go or not approved_state_id:
            from comfy_execution.graph import ExecutionBlocker
            report = {"status":"awaiting_approval", "operation":"sampler_continue", "new_noise":False}
            return {"ui":{"h3_draft":[report]},
                    "result":(ExecutionBlocker(None), ExecutionBlocker(None), json.dumps(report))}
        result = SamplerEngine().continue_external(draft_state, approved_state_id, prompt)
        return {"ui":{"h3_draft":[result.report]},
                "result":(result.latent, result.denoised, json.dumps(result.report, ensure_ascii=False, indent=2))}


NODE_CLASS_MAPPINGS = {"H3DraftSampler":H3DraftSampler, "H3ContinueSampler":H3ContinueSampler}
NODE_DISPLAY_NAME_MAPPINGS = {"H3DraftSampler":"H3 Draft Sampler", "H3ContinueSampler":"H3 Continue Sampler"}
