"""Interoperable SamplerCustomAdvanced adapter. No text encode/scheduler/decode on GO."""
from __future__ import annotations

import copy
import importlib
import inspect
import torch
from .backend import CoreBackend, outputs
from .contracts import DraftError
from .sampler_state import freeze, guider_parameters, native_geometry


class CoreSamplerBackend(CoreBackend):
    def __init__(self):
        try:
            self.custom = importlib.import_module("comfy_extras.nodes_custom_sampler")
            self.nodes = importlib.import_module("nodes")
            self.nt = importlib.import_module("comfy.nested_tensor")
            self.mm = importlib.import_module("comfy.model_management")
            self.samplers = importlib.import_module("comfy.samplers")
            self.kd = importlib.import_module("comfy.k_diffusion.sampling")
            self.mp = importlib.import_module("comfy.model_patcher")
        except ImportError as exc:
            raise DraftError("ComfyUI native custom sampler support is required. Restart after updating Core.") from exc
        self.guider_types = tuple(x for x in (
            getattr(self.custom, "Guider_Basic", None), self.samplers.CFGGuider,
            getattr(self.custom, "Guider_DualCFG", None)) if x is not None)

    def _core_guider_kind(self, guider):
        if guider is None:
            return None
        names = {cls.__name__ for cls in type(guider).__mro__}
        if "Guider_DualModel" in names or hasattr(guider, "uncond_model_patcher"):
            return None
        if not hasattr(guider, "model_patcher") or not hasattr(guider, "original_conds"):
            return None
        if any(isinstance(guider, cls) for cls in self.guider_types):
            if hasattr(guider, "cfg1") or hasattr(guider, "cfg2") or "Guider_DualCFG" in names:
                return "dual_cfg"
            return "basic_or_cfg"
        if "Guider_DualCFG" in names:
            return "dual_cfg"
        if "Guider_Basic" in names:
            return "basic"
        if type(guider).__name__ == "CFGGuider" and "CFGGuider" in names:
            return "cfg"
        return None

    def validate_external(self, noise, guider, sampler, latent, video_vae):
        if self._core_guider_kind(guider) is None:
            raise DraftError("Use Core BasicGuider, CFGGuider or DualCFGGuider. Custom/multi-model GUIDER requires a resume adapter.")
        if type(getattr(guider.model_patcher, "model", None)).__name__ != "MiniMaxH3":
            raise DraftError("H3 Draft Sampler accepts MiniMax H3 models only; its ports are standard, not model-agnostic.")
        if type(getattr(video_vae, "first_stage_model", None)).__name__ != "MiniMaxH3VideoVAE":
            raise DraftError("Connect the MiniMax H3 video VAE for the one-image Preview.")
        if type(sampler) is not self.samplers.KSAMPLER or sampler.sampler_function is not self.kd.sample_euler:
            raise DraftError("Exact split support currently requires Core Euler. Other samplers are not silently replaced; multistep solvers need history capture.")
        if (not callable(getattr(noise, "generate_noise", None)) or type(getattr(noise, "seed", None)) is not int or not 0 <= noise.seed < 2**64):
            raise DraftError("NOISE must expose generate_noise(latent) and an unsigned 64-bit integer seed.")
        opts = getattr(sampler, "extra_options", {})
        if not isinstance(opts, dict) or opts.get("s_churn", 0) != 0:
            raise DraftError("Euler with stochastic churn cannot resume without RNG state; use s_churn=0.")
        allowed = set(inspect.signature(self.kd.sample_euler).parameters) - {"model", "x", "sigmas", "extra_args", "callback", "disable"}
        if not set(opts) <= allowed or getattr(sampler, "inpaint_options", {}).get("random", False):
            raise DraftError("Unsupported stochastic/custom sampler options. No option was discarded.")
        if not isinstance(latent, dict) or latent.get("noise_mask") is not None:
            raise DraftError("Use a native H3 AV LATENT without a noise_mask. Image keyframes/references belong in CONDITIONING; masked inpainting needs separate resume validation.")
        g = native_geometry(self.av_parts(latent))
        if not isinstance(getattr(guider, "original_conds", None), dict) or not guider.original_conds.get("positive"):
            raise DraftError("GUIDER has no positive conditioning.")
        guider_parameters(guider)
        freeze(guider.original_conds, "GUIDER conditioning")
        freeze({k:v for k,v in latent.items() if k != "samples"}, "LATENT metadata")
        freeze(opts, "SAMPLER options")
        return g

    def snapshot_guider(self, guider):
        if self._core_guider_kind(guider) is None:
            raise DraftError("Unsupported GUIDER snapshot contract.")
        owned = copy.copy(guider)
        owned.model_patcher = guider.model_patcher.clone()
        owned.model_patcher.model_options = self.mp.create_model_options_clone(guider.model_options)
        owned.model_options = owned.model_patcher.model_options
        owned.original_conds = freeze(guider.original_conds, "GUIDER conditioning")
        for name, value in guider_parameters(guider).items():
            setattr(owned, name, value)
        for name in ("conds", "inner_model", "loaded_models"):
            owned.__dict__.pop(name, None)
        return owned

    def snapshot_sampler(self, sampler):
        out = copy.copy(sampler)
        out.extra_options = freeze(sampler.extra_options, "SAMPLER options")
        out.inpaint_options = freeze(sampler.inpaint_options, "SAMPLER inpaint options")
        return out

    def pack(self, av, metadata):
        out = freeze(metadata, "LATENT metadata")
        out["samples"] = self.nt.NestedTensor(tuple(av))
        return out

    def sample_external(self, noise, guider, sampler, latent, sigmas):
        self.interrupt()
        out, x0 = outputs(self.custom.SamplerCustomAdvanced.execute(noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent))
        self.interrupt()
        return out, x0

    def zero_noise(self, seed):
        noise, = outputs(self.custom.DisableNoise.execute())
        noise.seed = seed
        return noise

    def copy_latent(self, latent):
        return self.pack(freeze(self.av_parts(latent), "AV latent"), {k:v for k,v in latent.items() if k != "samples"})
