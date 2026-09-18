import unittest, torch
from h3draft.contracts import DraftError
from h3draft.sampler_engine import SamplerEngine
from sampler_fakes import setup, GuiderBasic, Noise

class SamplerInteropTest(unittest.TestCase):
    def setUp(self):
        self.b,self.n,self.g,self.s,self.sig,self.lat,self.vae=setup();self.e=SamplerEngine(self.b)
    def draft(self):
        return self.e.draft_external(self.n,self.g,self.s,self.sig,self.lat,self.vae,preview_steps=3).state
    def test_preview_continue_numeric_parity_host_double(self):
        full,_=self.b.sample_external(Noise(self.n.seed),self.g,self.s,self.lat,self.sig)
        state=self.draft();out=self.e.continue_external(state,state.state_id)
        for a,b in zip(full["samples"].unbind(),out.latent["samples"].unbind()):
            self.assertTrue(torch.allclose(a,b,atol=2e-7,rtol=2e-7))
        self.assertEqual(self.n.calls,1)
    def test_separately_loaded_core_basic_guider_is_accepted(self):
        AltBasic=type("Guider_Basic",(GuiderBasic,),{})
        g=AltBasic(self.g.model_patcher);g.cfg=self.g.cfg;g.original_conds=self.g.original_conds;self.g=g
        state=self.draft();self.assertEqual(type(state.guider).__name__,"Guider_Basic")
        self.e.continue_external(state,state.state_id)
    def test_separately_loaded_cfg_guider_name_is_accepted(self):
        AltCFG=type("CFGGuider",(GuiderBasic,),{})
        g=AltCFG(self.g.model_patcher);g.cfg=self.g.cfg;g.original_conds=self.g.original_conds;self.g=g
        self.assertEqual(type(self.draft().guider).__name__,"CFGGuider")
    def test_dual_model_guider_remains_fail_closed(self):
        Bad=type("Guider_DualModel",(GuiderBasic,),{})
        g=Bad(self.g.model_patcher);g.original_conds=self.g.original_conds;g.uncond_model_patcher=self.g.model_patcher;self.g=g
        with self.assertRaisesRegex(DraftError,"GUIDER"):self.draft()
        self.assertEqual(self.n.calls,0)
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
