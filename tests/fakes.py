"""Host doubles, not H3 model weights."""
from types import SimpleNamespace
import copy, torch

class Model:
    def __init__(self):
        self.model=SimpleNamespace()
        self.patches_uuid="turbo-four-step"; self.patches={"lora":[(1.0,"fixture")]}
        self.object_patches={}; self.model_options={}
        self.ms=SimpleNamespace(shift=12.0,audio_shift=3.0,noise_scale=1.0,multiplier=1000)
    def clone(self):
        m=copy.copy(self);m.model_options=copy.deepcopy(self.model_options);return m
    def get_model_object(self,name):
        assert name=="model_sampling";return self.ms
