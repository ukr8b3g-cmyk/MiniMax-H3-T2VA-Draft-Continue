import types, unittest, torch
from h3draft.contracts import DraftError
from h3draft.sampler_backend import resolve_registered_sampler_bindings
from h3draft.sampler_engine import SamplerEngine
from sampler_fakes import setup, GuiderBasic, GuiderCFG, GuiderDual, Noise

class SamplerInteropTest(unittest.TestCase):
    def setUp(self):
        self.b,self.n,self.g,self.s,self.sig,self.lat,self.vae=setup();self.e=SamplerEngine(self.b)

    def draft(self):
        return self.e.draft_external(
            self.n,self.g,self.s,self.sig,self.lat,self.vae,preview_steps=3
        ).state

    def refs(self):
        return self.g.original_conds["positive"][0].get("minimax_refs", [])

    def set_refs(self, refs):
        self.g.original_conds["positive"][0]["minimax_refs"] = refs

    @staticmethod
    def image_ref(value=1.0):
        return {
            "kind":"image",
            "latent_h":2,
            "latent_w":2,
            "latent":torch.full((1,24,1,2,2),value),
        }

    @staticmethod
    def audio_ref(value=1.0):
        return {
            "kind":"audio",
            "ref_audio_t":7,
            "audio_latent":torch.full((1,32,2,7),value),
        }

    @staticmethod
    def video_ref(value=1.0, with_audio=False):
        ref={
            "kind":"video_audio" if with_audio else "video",
            "latent_t":7,
            "latent_h":2,
            "latent_w":2,
            "ref_audio_t":7 if with_audio else 0,
            "latent":torch.full((1,24,7,2,2),value),
            "audio_latent":torch.full((1,32,2,7),value+.5) if with_audio else None,
        }
        return ref

    def test_preview_continue_numeric_parity_host_double(self):
        full,_=self.b.sample_external(Noise(self.n.seed),self.g,self.s,self.lat,self.sig)
        state=self.draft();out=self.e.continue_external(state,state.state_id)
        for a,b in zip(full["samples"].unbind(),out.latent["samples"].unbind()):
            self.assertTrue(torch.allclose(a,b,atol=2e-7,rtol=2e-7))
        self.assertEqual(self.n.calls,1)

    def test_registered_loader_module_identity_is_used(self):
        loaded=types.ModuleType("D:/ComfyUI/comfy_extras/nodes_custom_sampler")
        loaded.Guider_Basic=type("Guider_Basic",(GuiderBasic,),{})
        loaded.Guider_DualCFG=type("Guider_DualCFG",(GuiderBasic,),{})
        BasicNode=type("BasicGuider",(),{});BasicNode.__module__=loaded.__name__
        DualNode=type("DualCFGGuider",(),{});DualNode.__module__=loaded.__name__
        SamplerNode=type("SamplerCustomAdvanced",(),{"execute":staticmethod(lambda **kwargs:None)})
        DisableNode=type("DisableNoise",(),{"execute":staticmethod(lambda:None)})
        mappings={"SamplerCustomAdvanced":SamplerNode,"DisableNoise":DisableNode,
                  "BasicGuider":BasicNode,"CFGGuider":type("CFGGuiderNode",(),{}),
                  "DualCFGGuider":DualNode}
        bindings=resolve_registered_sampler_bindings(
            mappings,types.SimpleNamespace(CFGGuider=GuiderCFG),{loaded.__name__:loaded})
        self.assertIs(bindings.guider_types[0],loaded.Guider_Basic)
        self.assertIs(bindings.guider_types[1],GuiderCFG)
        self.assertIs(bindings.guider_types[2],loaded.Guider_DualCFG)
        self.assertIs(bindings.sampler_custom,SamplerNode)
        self.assertIs(bindings.disable_noise,DisableNode)

    def test_duplicate_reimport_class_is_rejected(self):
        registered=type("Guider_Basic",(GuiderBasic,),{})
        duplicate=type("Guider_Basic",(GuiderBasic,),{})
        self.b.guider_types=(registered,GuiderCFG,GuiderDual)
        g=registered(self.g.model_patcher);g.cfg=self.g.cfg;g.original_conds=self.g.original_conds;self.g=g
        self.assertEqual(type(self.draft().guider).__name__,"Guider_Basic")
        bad=duplicate(self.g.model_patcher);bad.cfg=self.g.cfg;bad.original_conds=self.g.original_conds;self.g=bad
        with self.assertRaisesRegex(DraftError,"GUIDER"):self.draft()

    def test_dual_model_guider_remains_fail_closed(self):
        Bad=type("Guider_DualModel",(GuiderBasic,),{})
        g=Bad(self.g.model_patcher);g.original_conds=self.g.original_conds;g.uncond_model_patcher=self.g.model_patcher;self.g=g
        with self.assertRaisesRegex(DraftError,"GUIDER"):self.draft()
        self.assertEqual(self.n.calls,0)

    def test_instance_sample_override_is_rejected(self):
        self.g.sample=lambda *a,**k:None
        with self.assertRaisesRegex(DraftError,"overrides sample"):self.draft()
        self.assertEqual(self.n.calls,0)

    # R0 — no native Reference must preserve the current baseline.
    def test_r0_no_reference_baseline(self):
        self.g.original_conds["positive"][0].pop("minimax_refs",None)
        state=self.draft()
        self.assertFalse(state.reference_manifest["present"])
        self.assertEqual(state.reference_manifest["count"],0)
        out=self.e.continue_external(state,state.state_id)
        self.assertEqual(out.report["reference_count"],0)

    # R1 — one image Reference is snapshotted and reused without re-encoding.
    def test_r1_one_native_image_reference_preserved(self):
        self.set_refs([self.image_ref(1.25)])
        state=self.draft()
        manifest=state.reference_manifest
        self.assertTrue(manifest["present"])
        self.assertEqual(manifest["count"],1)
        self.assertEqual(manifest["kinds"],{"image":1})
        self.assertEqual(manifest["items"][0]["latent"]["shape"],[1,24,1,2,2])
        stored=state.guider.original_conds["positive"][0]["minimax_refs"][0]["latent"]
        self.assertTrue(torch.equal(stored,torch.full((1,24,1,2,2),1.25)))
        self.assertEqual(stored.device.type,"cpu")
        out=self.e.continue_external(state,state.state_id)
        self.assertTrue(out.report["native_reference_passthrough"])
        self.assertFalse(out.report["reference_reencoded"])
        self.assertEqual(out.report["reference_count"],1)

    # R2 — mixed/multiple Core Reference blocks keep exact ordering.
    def test_r2_multiple_native_references_keep_order_and_kinds(self):
        refs=[
            self.image_ref(.5),
            self.video_ref(1.0,False),
            self.video_ref(1.5,True),
            self.audio_ref(2.0),
        ]
        self.set_refs(refs)
        state=self.draft()
        manifest=state.reference_manifest
        self.assertEqual(manifest["count"],4)
        self.assertEqual(
            [item["kind"] for item in manifest["items"]],
            ["image","video","video_audio","audio"],
        )
        self.assertEqual(
            manifest["kinds"],
            {"audio":1,"image":1,"video":1,"video_audio":1},
        )
        self.assertEqual(manifest["items"][2]["audio_latent"]["shape"],[1,32,2,7])
        self.assertEqual(manifest["items"][3]["audio_latent"]["shape"],[1,32,2,7])

    # R3 — any content/count/order change after Preview invalidates GO.
    def test_r3_reference_content_change_invalidates_review(self):
        self.set_refs([self.image_ref(1.0)])
        state=self.draft()
        self.refs()[0]["latent"].add_(.25)
        with self.assertRaisesRegex(DraftError,"Native H3 reference conditioning changed"):
            state.verify(state.state_id)

    def test_r3_reference_count_change_invalidates_review(self):
        self.set_refs([self.image_ref(1.0),self.audio_ref(2.0)])
        state=self.draft()
        self.refs().pop()
        with self.assertRaisesRegex(DraftError,"Native H3 reference conditioning changed"):
            state.verify(state.state_id)

    def test_r3_reference_order_change_invalidates_review(self):
        self.set_refs([self.image_ref(1.0),self.image_ref(2.0)])
        state=self.draft()
        self.refs().reverse()
        with self.assertRaisesRegex(DraftError,"Native H3 reference conditioning changed"):
            state.verify(state.state_id)

    def test_external_cfg_reference_and_metadata_preserved(self):
        state=self.draft()
        self.assertEqual(state.guider.cfg,2.5)
        self.assertIn("minimax_refs",state.guider.original_conds["positive"][0])
        self.assertEqual(state.latent_metadata["batch_index"],[0])
        self.assertTrue(torch.equal(state.sigmas,self.sig))

    def test_changed_source_is_rejected(self):
        state=self.draft();self.g.cfg=3.0
        with self.assertRaisesRegex(DraftError,"External GUIDER"):state.verify(state.state_id)

    def test_stale_approval_is_rejected(self):
        state=self.draft()
        with self.assertRaisesRegex(DraftError,"reviewed"):self.e.continue_external(state,"0"*32)

    def test_multistep_sampler_not_silently_replaced(self):
        self.s.sampler_function=lambda:None
        with self.assertRaisesRegex(DraftError,"Euler"):self.draft()

if __name__=="__main__":unittest.main()
