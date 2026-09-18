"""Core-host doubles for interoperability tests; not real H3 inference."""
from types import SimpleNamespace
import copy, torch, uuid
from fakes import Model
from h3draft.sampler_backend import CoreSamplerBackend
from h3draft.sampler_state import native_geometry

class Nested:
    is_nested=True
    def __init__(self,tensors):self.tensors=tuple(tensors)
    def unbind(self):return self.tensors

class GuiderBasic:
    def __init__(self,model):
        self.model_patcher=model;self.model_options=model.model_options;self.original_conds={};self.cfg=1.0
class GuiderCFG(GuiderBasic):pass
class GuiderDual(GuiderBasic):pass

def sample_euler(model,x,sigmas,extra_args=None,callback=None,disable=None,s_churn=0.,s_tmin=0.,s_tmax=float("inf"),s_noise=1.):pass

class Sampler:
    def __init__(self,fn=sample_euler):
        self.sampler_function=fn;self.extra_options={};self.inpaint_options={}

class Noise:
    def __init__(self,seed=17,zero=False):self.seed=seed;self.zero=zero;self.calls=0
    def generate_noise(self,latent):
        self.calls+=1;parts=latent["samples"].unbind();g=torch.Generator().manual_seed(self.seed)
        return Nested(tuple(torch.zeros_like(x) if self.zero else torch.randn(x.shape,generator=g) for x in parts))

class Backend(CoreSamplerBackend):
    def __init__(self):
        self.calls=[];self.mm=SimpleNamespace(throw_exception_if_processing_interrupted=lambda:None)
        self.nt=SimpleNamespace(NestedTensor=Nested);self.mp=SimpleNamespace(create_model_options_clone=copy.deepcopy)
        self.samplers=SimpleNamespace(KSAMPLER=Sampler);self.kd=SimpleNamespace(sample_euler=sample_euler)
        self.guider_types=(GuiderBasic,GuiderCFG,GuiderDual)
        self.custom=SimpleNamespace(SamplerCustomAdvanced=SimpleNamespace(execute=self.core_sample),
                                    DisableNoise=SimpleNamespace(execute=lambda:(Noise(0,zero=True),)))
    def core_sample(self,noise,guider,sampler,sigmas,latent_image):
        self.calls.append(("sample",noise,guider,sampler,sigmas.clone(),latent_image))
        parts=latent_image["samples"].unbind();generated=noise.generate_noise(latent_image).unbind()
        scale=guider.model_patcher.ms.shift/guider.model_patcher.ms.audio_shift
        x=torch.cat([parts[0].reshape(-1),(parts[1]*scale).reshape(-1)])
        n=torch.cat([generated[0].reshape(-1),generated[1].reshape(-1)])
        x=sigmas[0]*n+(1-sigmas[0])*x
        target=.13+float(guider.original_conds["positive"][0]["cross_attn"].mean())*guider.cfg
        for a,b in zip(sigmas[:-1],sigmas[1:]):
            denoised=torch.tanh(.23*x+target)+.02*a;x=x+(b-a)*(x-denoised)/a
        m=parts[0].numel()
        def pack(y):
            result={k:copy.deepcopy(v) for k,v in latent_image.items() if k!="samples"}
            result["samples"]=Nested((y[:m].reshape(parts[0].shape).clone(),y[m:].reshape(parts[1].shape).clone()/scale))
            return result
        return pack(x/(1-sigmas[-1])),pack(denoised)
    def decode_video(self,latent,vae):
        g=native_geometry(latent["samples"].unbind());return torch.full((g["frame_count"],g["height"],g["width"],3),.3)
    def preview_ui(self,*args):return {"images":[{"filename":"fixture.png","subfolder":"","type":"temp"}]}

def setup():
    model=Model();model.model=type("MiniMaxH3",(),{})()
    guider=GuiderCFG(model);guider.cfg=2.5
    guider.original_conds={
      "positive":[{"cross_attn":torch.tensor([[.12,.24]]),"uuid":uuid.uuid4(),"model_conds":{},
                   "minimax_token_tags":torch.tensor([0,1]),
                   "minimax_refs":[{"kind":"image","latent":torch.ones(1,24,1,2,2)}]}],
      "negative":[{"cross_attn":torch.tensor([[0.,0.]]),"uuid":uuid.uuid4(),"model_conds":{}}]}
    sampler=Sampler();noise=Noise();vae=SimpleNamespace(first_stage_model=type("MiniMaxH3VideoVAE",(),{})())
    latent={"samples":Nested((torch.zeros(1,24,7,2,2),torch.zeros(1,32,2,37))),"batch_index":[0]}
    sigmas=torch.tensor([1.,.93,.79,.60,.34,.12,0.])
    return Backend(),noise,guider,sampler,sigmas,latent,vae
