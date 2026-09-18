"""Interoperable SamplerCustomAdvanced adapter. No text encode/scheduler/decode on GO.

Important loader contract:
ComfyUI loads ``comfy_extras/nodes_custom_sampler.py`` through
``spec_from_file_location`` and registers the resulting node classes in
``nodes.NODE_CLASS_MAPPINGS``. Importing ``comfy_extras.nodes_custom_sampler``
again can therefore create a second Python module/class identity for the same
source file. This adapter deliberately binds to the already-registered Core
node classes instead of re-importing that file.
"""
from __future__ import annotations

import copy
import importlib
import inspect
import sys
from dataclasses import dataclass

from .backend import CoreBackend, outputs
from .contracts import DraftError
from .sampler_state import freeze, guider_parameters, native_geometry


@dataclass(frozen=True)
class _RegisteredSamplerBindings:
    sampler_custom: type
    disable_noise: type
    guider_types: tuple[type, ...]


def _registered_module(node_cls, module_registry=None):
    """Return the exact module object ComfyUI used to register ``node_cls``."""
    registry = sys.modules if module_registry is None else module_registry
    module_name = getattr(node_cls, "__module__", "")
    module = registry.get(module_name)
    if module is None:
        raise DraftError(
            f"Registered Core node module {module_name!r} is not loaded. "
            "Restart ComfyUI; do not import a second nodes_custom_sampler copy."
        )
    return module


def resolve_registered_sampler_bindings(node_mappings, samplers, module_registry=None):
    """Resolve sampler/guider classes from ComfyUI's live node registry.

    ``nodes_custom_sampler.py`` is intentionally *not* imported here. The
    registered node classes are the authority because their module instance is
    the one that created the GUIDER objects flowing through the graph.
    """
    required = (
        "SamplerCustomAdvanced", "DisableNoise", "BasicGuider",
        "CFGGuider", "DualCFGGuider",
    )
    missing = [name for name in required if name not in node_mappings]
    if missing:
        raise DraftError(
            "ComfyUI native custom sampler nodes are not registered: "
            + ", ".join(missing)
            + ". Restart after updating Core."
        )

    sampler_custom = node_mappings["SamplerCustomAdvanced"]
    disable_noise = node_mappings["DisableNoise"]
    basic_node = node_mappings["BasicGuider"]
    dual_node = node_mappings["DualCFGGuider"]

    basic_module = _registered_module(basic_node, module_registry)
    dual_module = _registered_module(dual_node, module_registry)
    basic_type = getattr(basic_module, "Guider_Basic", None)
    dual_type = getattr(dual_module, "Guider_DualCFG", None)
    cfg_type = getattr(samplers, "CFGGuider", None)

    if not all(
        isinstance(x, type)
        for x in (sampler_custom, disable_noise, basic_type, cfg_type, dual_type)
    ):
        raise DraftError(
            "ComfyUI registered sampler/guider contract is incomplete. "
            "Restart after updating Core."
        )

    return _RegisteredSamplerBindings(
        sampler_custom=sampler_custom,
        disable_noise=disable_noise,
        guider_types=(basic_type, cfg_type, dual_type),
    )


class CoreSamplerBackend(CoreBackend):
    def __init__(self):
        try:
            self.nodes = importlib.import_module("nodes")
            self.nt = importlib.import_module("comfy.nested_tensor")
            self.mm = importlib.import_module("comfy.model_management")
            self.samplers = importlib.import_module("comfy.samplers")
            self.kd = importlib.import_module("comfy.k_diffusion.sampling")
            self.mp = importlib.import_module("comfy.model_patcher")
        except ImportError as exc:
            raise DraftError(
                "ComfyUI native custom sampler support is required. "
                "Restart after updating Core."
            ) from exc

        mappings = getattr(self.nodes, "NODE_CLASS_MAPPINGS", None)
        if not isinstance(mappings, dict):
            raise DraftError("ComfyUI node registry is unavailable. Restart ComfyUI.")

        bindings = resolve_registered_sampler_bindings(mappings, self.samplers)
        self.sampler_custom_node = bindings.sampler_custom
        self.disable_noise_node = bindings.disable_noise
        self.guider_types = bindings.guider_types

    def _is_supported_guider(self, guider):
        # Exact type identity is now safe: allowed classes were resolved from
        # the same live module instance that ComfyUI registered.
        return guider is not None and type(guider) in self.guider_types

    def validate_external(self, noise, guider, sampler, latent, video_vae):
        if not self._is_supported_guider(guider):
            raise DraftError(
                "Use Core BasicGuider, CFGGuider or DualCFGGuider. "
                "Custom/multi-model GUIDER requires a resume adapter."
            )
        if "sample" in getattr(guider, "__dict__", {}):
            raise DraftError(
                "GUIDER instance overrides sample; custom resume behavior "
                "requires a dedicated adapter."
            )
        if type(getattr(guider.model_patcher, "model", None)).__name__ != "MiniMaxH3":
            raise DraftError(
                "H3 Draft Sampler accepts MiniMax H3 models only; "
                "its ports are standard, not model-agnostic."
            )
        if type(getattr(video_vae, "first_stage_model", None)).__name__ != "MiniMaxH3VideoVAE":
            raise DraftError(
                "Connect the MiniMax H3 video VAE for the one-image Preview."
            )
        if (
            type(sampler) is not self.samplers.KSAMPLER
            or sampler.sampler_function is not self.kd.sample_euler
        ):
            raise DraftError(
                "Exact split support currently requires Core Euler. "
                "Other samplers are not silently replaced; multistep solvers need history capture."
            )
        if (
            not callable(getattr(noise, "generate_noise", None))
            or type(getattr(noise, "seed", None)) is not int
            or not 0 <= noise.seed < 2**64
        ):
            raise DraftError(
                "NOISE must expose generate_noise(latent) and an unsigned 64-bit integer seed."
            )
        opts = getattr(sampler, "extra_options", {})
        if not isinstance(opts, dict) or opts.get("s_churn", 0) != 0:
            raise DraftError(
                "Euler with stochastic churn cannot resume without RNG state; use s_churn=0."
            )
        allowed = set(inspect.signature(self.kd.sample_euler).parameters) - {
            "model", "x", "sigmas", "extra_args", "callback", "disable",
        }
        if (
            not set(opts) <= allowed
            or getattr(sampler, "inpaint_options", {}).get("random", False)
        ):
            raise DraftError(
                "Unsupported stochastic/custom sampler options. No option was discarded."
            )
        if not isinstance(latent, dict) or latent.get("noise_mask") is not None:
            raise DraftError(
                "Use a native H3 AV LATENT without a noise_mask. "
                "Image keyframes/references belong in CONDITIONING; "
                "masked inpainting needs separate resume validation."
            )

        geometry = native_geometry(self.av_parts(latent))
        if (
            not isinstance(getattr(guider, "original_conds", None), dict)
            or not guider.original_conds.get("positive")
        ):
            raise DraftError("GUIDER has no positive conditioning.")

        guider_parameters(guider)
        freeze(guider.original_conds, "GUIDER conditioning")
        freeze(
            {k: v for k, v in latent.items() if k != "samples"},
            "LATENT metadata",
        )
        freeze(opts, "SAMPLER options")
        return geometry

    def snapshot_guider(self, guider):
        if not self._is_supported_guider(guider):
            raise DraftError("Unsupported GUIDER snapshot contract.")

        owned = copy.copy(guider)
        owned.model_patcher = guider.model_patcher.clone()
        owned.model_patcher.model_options = self.mp.create_model_options_clone(
            guider.model_options
        )
        owned.model_options = owned.model_patcher.model_options
        owned.original_conds = freeze(
            guider.original_conds, "GUIDER conditioning"
        )
        for name, value in guider_parameters(guider).items():
            setattr(owned, name, value)
        for name in ("conds", "inner_model", "loaded_models"):
            owned.__dict__.pop(name, None)
        return owned

    def snapshot_sampler(self, sampler):
        out = copy.copy(sampler)
        out.extra_options = freeze(sampler.extra_options, "SAMPLER options")
        out.inpaint_options = freeze(
            sampler.inpaint_options, "SAMPLER inpaint options"
        )
        return out

    def pack(self, av, metadata):
        out = freeze(metadata, "LATENT metadata")
        out["samples"] = self.nt.NestedTensor(tuple(av))
        return out

    def sample_external(self, noise, guider, sampler, latent, sigmas):
        self.interrupt()
        out, x0 = outputs(
            self.sampler_custom_node.execute(
                noise=noise,
                guider=guider,
                sampler=sampler,
                sigmas=sigmas,
                latent_image=latent,
            )
        )
        self.interrupt()
        return out, x0

    def zero_noise(self, seed):
        noise, = outputs(self.disable_noise_node.execute())
        noise.seed = seed
        return noise

    def copy_latent(self, latent):
        return self.pack(
            freeze(self.av_parts(latent), "AV latent"),
            {k: v for k, v in latent.items() if k != "samples"},
        )
