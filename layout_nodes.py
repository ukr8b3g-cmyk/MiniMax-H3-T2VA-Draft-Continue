"""Optional upstream audit bridge. No model loading or Canvas dependency."""
from __future__ import annotations
from .h3draft.structured import attach_source


class H3StructuredLayoutAudit:
    CATEGORY = "MiniMax H3/Draft Continue"
    FUNCTION = "attach"
    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("positive",)
    DESCRIPTION = ("Attach START, START→END, or Multi-Key layout provenance to existing H3 conditioning. "
                   "Connect Canvas layout and the same exact Prompter string used by the text encoder. "
                   "No text rewrite, encoding, BBOX interpolation, enforcement or latent modification.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "positive": ("CONDITIONING",),
            "layout": ("H3_LAYOUT",),
            "compiled_prompt": ("STRING", {"forceInput": True}),
        }}

    def attach(self, positive, layout, compiled_prompt):
        return (attach_source(positive, layout, compiled_prompt),)


NODE_CLASS_MAPPINGS = {"H3StructuredLayoutAudit": H3StructuredLayoutAudit}
NODE_DISPLAY_NAME_MAPPINGS = {"H3StructuredLayoutAudit": "H3 Structured Layout Audit"}
