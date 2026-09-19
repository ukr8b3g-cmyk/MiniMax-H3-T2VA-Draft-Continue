import json
from pathlib import Path
import unittest
from h3draft.structured import canonical_start_layout

ROOT = Path(__file__).resolve().parents[1]

class StructuredWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((ROOT / 'examples/H3-START-Layout-Draft.json').read_text(encoding='utf-8'))
        self.nodes = {n['id']:n for n in self.w['nodes']}
        self.links = {e[0]:e for e in self.w['links']}

    def node(self, kind):
        return next(n for n in self.w['nodes'] if n['type']==kind)

    def source(self,node,name):
        link=next(i['link'] for i in node['inputs'] if i['name']==name)
        e=self.links[link]
        return e[1],e[2]

    def test_links_and_slots_consistent(self):
        self.assertEqual(len(self.nodes),len(self.w['nodes']))
        self.assertEqual(len(self.links),len(self.w['links']))
        for lid,sid,ss,did,ds,typ in self.w['links']:
            s=self.nodes[sid]['outputs'][ss];d=self.nodes[did]['inputs'][ds]
            self.assertEqual(d['link'],lid)
            self.assertIn(lid,s['links'])
            self.assertEqual(s['type'],typ);self.assertIn(typ,d['type'].split(','))

    def test_exact_prompt_and_layout_wiring(self):
        audit=self.node('H3StructuredLayoutAudit');cond=self.node('MiniMaxH3ImageToVideo')
        prompter=self.node('H3StructuredPrompter');canvas=self.node('H3StructuredCanvas')
        self.assertEqual(self.source(audit,'compiled_prompt'),self.source(cond,'prompt'))
        self.assertEqual(self.source(audit,'layout'),self.source(prompter,'layout'))
        self.assertEqual(self.source(cond,'width'),(canvas['id'],1))
        self.assertEqual(self.source(cond,'height'),(canvas['id'],2))
        self.assertEqual(self.source(self.node('BasicGuider'),'conditioning'),(audit['id'],0))

    def test_example_scope_and_approval(self):
        c=self.node('H3StructuredCanvas')
        data=json.loads(c['widgets_values_named']['layout_json'])
        self.assertEqual(len(canonical_start_layout(data)['boxes']),2)
        self.assertFalse(self.node('H3ContinueSampler')['widgets_values_named']['go'])
        self.assertEqual(self.node('H3ContinueSampler')['widgets_values_named']['approved_state_id'],'')
        self.assertEqual(self.node('H3DraftSampler')['widgets_values_named']['preview_steps'],3)
        self.assertEqual(self.node('BasicScheduler')['widgets_values_named']['steps'],6)
        self.assertEqual(self.node('KSamplerSelect')['widgets_values_named']['sampler_name'],'euler')

if __name__=='__main__':unittest.main()
