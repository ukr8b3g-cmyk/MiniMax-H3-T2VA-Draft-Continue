"""Thin calls into Core; no patched sampler, re-noise, secondary model or planner."""
from __future__ import annotations

import importlib
import torch
from .contracts import DraftError, Settings


def outputs(result):
    if hasattr(result, "result"):
        return result.result
    if isinstance(result, dict):
        return result["result"]
    if isinstance(result, (tuple, list)):
        return result
    raise DraftError("Unsupported Core node return type. Update ComfyUI, then restart.")


class CoreBackend:
    def __init__(self):
        try:
            self.custom = importlib.import_module("comfy_extras.nodes_custom_sampler")
            self.h3 = importlib.import_module("comfy_extras.nodes_minimax_h3")
            self.video = importlib.import_module("comfy_extras.nodes_video")
            self.audio = importlib.import_module("comfy_extras.nodes_audio")
            self.nodes = importlib.import_module("nodes")
            self.nt = importlib.import_module("comfy.nested_tensor")
            self.mm = importlib.import_module("comfy.model_management")
        except (ImportError, AttributeError) as exc:
            raise DraftError("MiniMax H3 Core support is missing. Use ComfyUI 0.36.0 or compatible newer Core and restart.") from exc

    def interrupt(self):
        self.mm.throw_exception_if_processing_interrupted()

    def validate_models(self, model, clip, video_vae, audio_vae):
        name = type(getattr(model, "model", None)).__name__
        if name != "MiniMaxH3":
            raise DraftError(f"Expected a native MiniMaxH3 MODEL, received {name}. Connect the H3 model after its Turbo LoRA loader.")
        te = type(getattr(clip, "cond_stage_model", None)).__name__
        if not te.startswith("MiniMaxH3TEModel"):
            raise DraftError("Expected the MiniMax H3 text encoder. Set CLIPLoader type=minimax.")
        for vae, expected, label in ((video_vae, "MiniMaxH3VideoVAE", "video"),
                                     (audio_vae, "MiniMaxH3AudioVAE", "audio")):
            actual = type(getattr(vae, "first_stage_model", None)).__name__
            if actual != expected:
                raise DraftError(f"Expected the H3 {label} VAE ({expected}); received {actual}.")
        if not hasattr(self.custom.SamplerCustomAdvanced, "execute"):
            raise DraftError("Core SamplerCustomAdvanced.execute is not available.")

    def prepare(self, model, clip, video_vae, settings: Settings):
        positive, latent = outputs(self.h3.MiniMaxH3ImageToVideo.execute(
            clip=clip, vae=video_vae, prompt=settings.prompt,
            width=settings.width, height=settings.height, length=settings.frame_count,
            first_frame=None, last_frame=None))
        sigmas, = outputs(self.custom.BasicScheduler.execute(
            model=model, scheduler=settings.scheduler, steps=settings.total_steps, denoise=1.0))
        return positive, latent, sigmas

    def av_parts(self, latent):
        samples = latent.get("samples")
        if not getattr(samples, "is_nested", False):
            raise DraftError("Core did not return a joint H3 audio/video NestedTensor.")
        parts = tuple(samples.unbind())
        if len(parts) != 2:
            raise DraftError("Expected exactly video + audio latent streams.")
        return parts

    def latent(self, av):
        return {"samples": self.nt.NestedTensor(tuple(av))}

    def sample(self, model, positive, latent, sigmas, settings, *, resume=False):
        self.interrupt()
        guider, = outputs(self.custom.BasicGuider.execute(model=model, conditioning=positive))
        sampler, = outputs(self.custom.KSamplerSelect.execute(sampler_name=settings.sampler))
        if resume:
            noise, = outputs(self.custom.DisableNoise.execute())
            noise.seed = settings.seed
        else:
            noise, = outputs(self.custom.RandomNoise.execute(noise_seed=settings.seed))
        out, denoised = outputs(self.custom.SamplerCustomAdvanced.execute(
            noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent))
        self.interrupt()
        return out, denoised

    def decode_video(self, latent, vae):
        self.interrupt()
        images = self.nodes.VAEDecode().decode(samples=latent, vae=vae)[0]
        if images.ndim != 4 or images.shape[-1] != 3 or not bool(torch.isfinite(images).all()):
            raise DraftError("Video VAE returned an invalid RGB image batch.")
        return images

    def decode_audio(self, latent, vae):
        self.interrupt()
        audio, = outputs(self.audio.VAEDecodeAudio.execute(vae=vae, samples=latent))
        if not isinstance(audio, dict) or not bool(torch.isfinite(audio["waveform"]).all()):
            raise DraftError("Audio VAE returned non-finite or invalid audio.")
        return audio

    def create_video(self, images, audio):
        video, = outputs(self.video.CreateVideo.execute(
            images=images, audio=audio, fps=24, bit_depth=8, color_space="sRGB", codec="none"))
        return video

    def preview_ui(self, image, prompt=None, extra_pnginfo=None):
        return self.nodes.PreviewImage().save_images(
            image, filename_prefix="H3Draft", prompt=prompt, extra_pnginfo=extra_pnginfo)["ui"]
