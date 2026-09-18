"""Two nodes. GO is guarded on both browser and backend, not a mute/bypass trick."""
from __future__ import annotations

import json
from .h3draft.contracts import DraftError, MAX_SEED, Settings
from .h3draft.engine import Engine

CATEGORY = "MiniMax H3/Draft Continue"


class H3T2VADraft:
    CATEGORY = CATEGORY
    RETURN_TYPES = ("IMAGE", "H3_DRAFT_STATE", "STRING")
    RETURN_NAMES = ("preview_image", "draft_state", "report")
    FUNCTION = "preview"
    OUTPUT_NODE = True
    DESCRIPTION = "Preview one estimated first frame, then continue the SAME T2VA run. Connect your H3 MODEL after the shared Turbo LoRA loader."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("MODEL",), "clip": ("CLIP",), "video_vae": ("VAE",), "audio_vae": ("VAE",),
            "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Passed to native MiniMax H3 unchanged. No prompt rewriting."}),
            "seed": ("INT", {"default": 1234, "min": 0, "max": MAX_SEED, "control_after_generate": False}),
            "width": ("INT", {"default": 544, "min": 32, "max": 2048, "step": 32}),
            "height": ("INT", {"default": 800, "min": 32, "max": 2048, "step": 32}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 1.0, "max": 15.0, "step": 0.5,
                "tooltip": "Snapped up to H3's 17k+5 frame grid. 5 seconds produces 124 frames at 24 fps."}),
            "total_steps": ("INT", {"default": 6, "min": 2, "max": 100}),
            "preview_steps": ("INT", {"default": 3, "min": 1, "max": 99,
                "tooltip": "Must be less than Total steps. Preview is an x0 estimate, not the final frame."}),
        }, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID"}}

    def preview(self, model, clip, video_vae, audio_vae, text, seed, width, height,
                duration_seconds, total_steps, preview_steps, prompt=None, extra_pnginfo=None, unique_id=""):
        settings = Settings(text, seed, width, height, duration_seconds, total_steps, preview_steps)
        engine = Engine()
        result = engine.draft(settings, model, clip, video_vae, audio_vae, prompt, unique_id)
        image = result.state.preview.clone()
        ui = engine.backend.preview_ui(image, prompt, extra_pnginfo)
        ui["h3_draft"] = [result.report]
        return {"ui": ui, "result": (image, result.state, json.dumps(result.report, ensure_ascii=False, indent=2))}


class H3T2VAContinue:
    CATEGORY = CATEGORY
    RETURN_TYPES = ("VIDEO", "LATENT", "STRING")
    RETURN_NAMES = ("video", "final_av_latent", "report")
    FUNCTION = "continue_video"
    OUTPUT_NODE = True
    DESCRIPTION = "Press GO after reviewing the connected Draft. No image re-encoding, model swap or new noise. Connect VIDEO to Core SaveVideo."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "draft_state": ("H3_DRAFT_STATE", {"lazy": True}),
            "go": ("BOOLEAN", {"default": False, "label_on": "GO", "label_off": "Review first"}),
            "approved_state_id": ("STRING", {"default": "", "tooltip": "Filled by GO. For API use, copy state.state_id from the Draft report."}),
        }, "hidden": {"prompt": "PROMPT"}}

    def check_lazy_status(self, go=False, approved_state_id="", draft_state=None, **kwargs):
        if go and approved_state_id and draft_state is None:
            return ["draft_state"]
        return []

    def continue_video(self, go=False, approved_state_id="", draft_state=None, prompt=None):
        if not go or not approved_state_id:
            from comfy_execution.graph import ExecutionBlocker
            report = {"status": "awaiting_approval", "operation": "continue", "new_noise": False}
            return {"ui": {"h3_draft": [report]},
                    "result": (ExecutionBlocker(None), ExecutionBlocker(None), json.dumps(report))}
        result = Engine().continue_(draft_state, approved_state_id, prompt)
        return {"ui": {"h3_draft": [result.report]},
                "result": (result.video, result.latent, json.dumps(result.report, ensure_ascii=False, indent=2))}


NODE_CLASS_MAPPINGS = {"H3T2VADraft": H3T2VADraft, "H3T2VAContinue": H3T2VAContinue}
NODE_DISPLAY_NAME_MAPPINGS = {"H3T2VADraft": "H3 T2VA Draft", "H3T2VAContinue": "H3 T2VA Continue"}
