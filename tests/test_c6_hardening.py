"""Phase 4C C6 ownership hardening."""
import copy, unittest
from dataclasses import replace
from h3draft.contracts import DraftError, verify_continue_source
from h3draft.sampler_engine import SamplerEngine
from sampler_fakes import setup
class C6Hardening(unittest.TestCase):
    def setUp(self):
        self.b,self.n,self.g,self.s,self.sig,self.lat,self.vae=setup();self.e=SamplerEngine(self.b)
        self.p={"15":{"class_type":"H3DraftSampler","inputs":{"preview_steps":3,"marker":"base"}}}
        self.st=self.e.draft_external(self.n,self.g,self.s,self.sig,self.lat,self.vae,3,self.p,"15").state
    def calls(self):return len([x for x in self.b.calls if x[0]=="sample"])
    def cp(self,src="15",slot=1):
        p=copy.deepcopy(self.p)
        if str(src) not in p:p[str(src)]={"class_type":"H3DraftSampler","inputs":{"marker":"other"}}
        p["20"]={"class_type":"H3ContinueSampler","inputs":{"draft_state":[str(src),slot],"go":True,"approved_state_id":self.st.state_id}}
        return p
    def reject(self,fn,msg):
        n=self.calls()
        with self.assertRaisesRegex(DraftError,msg):fn()
        self.assertEqual(self.calls(),n)
    def test_valid(self):self.e.continue_external(self.st,self.st.state_id,self.cp(),"20")
    def test_bad_approval(self):self.reject(lambda:self.e.continue_external(self.st,"0"*32,self.cp(),"20"),"reviewed")
    def test_other_draft(self):self.reject(lambda:self.e.continue_external(self.st,self.st.state_id,self.cp("28"),"20"),"not connected")
    def test_wrong_slot(self):self.reject(lambda:self.e.continue_external(self.st,self.st.state_id,self.cp("15",0),"20"),"not connected")
    def test_old_graph(self):
        p=self.cp();p["15"]["inputs"]["marker"]="changed";self.reject(lambda:self.e.continue_external(self.st,self.st.state_id,p,"20"),"upstream workflow")
    def test_old_session(self):
        x=replace(self.st,process_id="f"*32);self.reject(lambda:self.e.continue_external(x,x.state_id,self.cp(),"20"),"another backend session")
    def test_integrated(self):
        p={"5":{"class_type":"H3T2VADraft","inputs":{}},"6":{"class_type":"H3T2VAContinue","inputs":{"draft_state":["5",1]}}}
        verify_continue_source(p,"6","5","H3T2VAContinue","H3T2VADraft")
if __name__=="__main__":unittest.main()
