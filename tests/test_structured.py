"""Phase 3A: schema/hash contracts and mocked-host Draft/Continue lifecycle."""
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
import torch

from h3draft.contracts import DraftError, digest_json, graph_signature
from h3draft.structured import (KEY, LAYOUT_SCHEMA, SCHEMA, attach_source,
                               canonical_start_layout, make_source,
                               structured_manifest, validate_source)
from h3draft.sampler_engine import SamplerEngine
from sampler_fakes import setup, Noise


def layout(n=1, size=32):
    return {"schema": LAYOUT_SCHEMA,
            "canvas": {"width": size, "height": size, "aspect_ratio": "1:1",
                       "coordinate_space": "normalized_0_1000", "bbox_format": "xyxy",
                       "grid": "thirds", "show_boxes": True, "active_slot": "a"},
            "boxes": [{"slot": s, "bbox_2d": [20 + i*300, 100, 280+i*300, 900], "ui_color": s}
                      for i, s in enumerate("abc"[:n])]}


def timeline_wrapped(base=None, version=3):
    a = copy.deepcopy(base if base is not None else layout())
    a["transition"] = {
        "end_canvas": copy.deepcopy(a["canvas"]),
        "end_boxes": copy.deepcopy(a["boxes"]),
    }
    timeline = {
        "version": version,
        "slots": ["a", "b", "c"],
        "duration_seconds": 5.0,
        "interpolation": "piecewise_linear",
        "canonical_time": "normalized_0_1",
        "mid_time": 0.5,
        "mid_boxes": [],
        "coordinate_space": "normalized_0_1000_with_offscreen_overscan",
    }
    if version >= 4:
        timeline["max_intermediate_keys"] = 7
        timeline["keyframes"] = {}
    a["timeline_experimental"] = timeline
    return a


def load_bridge():
    # Test the actual public node, without importing the entire ComfyUI host.
    root = Path(__file__).resolve().parents[1]
    pkg = types.ModuleType("phase3a_node_test")
    pkg.__path__ = [str(root)]
    sys.modules[pkg.__name__] = pkg
    sys.modules[pkg.__name__ + ".h3draft"] = sys.modules["h3draft"]
    sys.modules[pkg.__name__ + ".h3draft.structured"] = sys.modules["h3draft.structured"]
    spec = importlib.util.spec_from_file_location(pkg.__name__ + ".layout_nodes", root / "layout_nodes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.H3StructuredLayoutAudit


class StructuredContractTests(unittest.TestCase):
    def test_real_canvas_schema_and_xyxy_are_preserved(self):
        source = make_source(layout(), "red hair, red jacket")
        self.assertEqual(source["schema"], SCHEMA)
        self.assertEqual(source["layout_schema"], LAYOUT_SCHEMA)
        self.assertEqual(source["ir"]["boxes"][0]["bbox_2d"], [20,100,280,900])
        self.assertEqual(source["compiled_prompt"], "red hair, red jacket")
        self.assertEqual(source, validate_source(source))

    def test_key_order_and_equal_number_notation_hash_equally(self):
        a = layout(); b = dict(reversed(list(copy.deepcopy(a).items())))
        b["boxes"][0]["bbox_2d"] = [20.0,100.,280.,900.]
        b["canvas"]["width"] = 32.0
        self.assertEqual(make_source(a,"same")["ir_hash"],make_source(b,"same")["ir_hash"])

    def test_no_coordinate_rounding(self):
        a = layout(); b = copy.deepcopy(a)
        a["boxes"][0]["bbox_2d"][0] = 20.000001
        b["boxes"][0]["bbox_2d"][0] = 20.000002
        self.assertNotEqual(make_source(a,"same")["ir_hash"],make_source(b,"same")["ir_hash"])

    def test_presentation_fields_ignored(self):
        a=layout(); b=copy.deepcopy(a)
        b["canvas"].update(grid="none", show_boxes=False,active_slot="c",aspect_ratio="visual-only")
        b["boxes"][0]["ui_color"]="other handle"
        b["warnings"]=["upstream notice"]
        self.assertEqual(make_source(a,"same"),make_source(b,"same"))

    def test_image_sidecar_excluded_without_reading_or_cloning(self):
        a=layout(); a["_h3_slot_images"]={"a":object()}
        self.assertEqual(make_source(a,"same"),make_source(layout(),"same"))

    def test_labels_description_id_are_not_discarded(self):
        a=layout(); a["boxes"][0].update(id="woman_a",description="red hair",label="person")
        b=copy.deepcopy(a); b["boxes"][0]["description"]="blue hair"
        self.assertNotEqual(make_source(a,"same")["ir_hash"],make_source(b,"same")["ir_hash"])

    def test_text_only_change_affects_prompt_not_ir_hash(self):
        a=make_source(layout(),"red");b=make_source(layout(),"deep red")
        self.assertEqual(a["ir_hash"],b["ir_hash"])
        self.assertNotEqual(a["prompt_hash"],b["prompt_hash"])

    def test_prompt_is_exact_including_whitespace(self):
        a=make_source(layout(),"red\n");b=make_source(layout(),"red")
        self.assertEqual(a["compiled_prompt"],"red\n")
        self.assertNotEqual(a["prompt_hash"],b["prompt_hash"])

    def test_static_timeline_v3_wrapper_hashes_as_plain_start(self):
        plain = make_source(layout(2), "same")
        wrapped = make_source(timeline_wrapped(layout(2), 3), "same")
        self.assertEqual(wrapped, plain)

    def test_static_timeline_v4_wrapper_hashes_as_plain_start(self):
        plain = make_source(layout(2), "same")
        wrapped = make_source(timeline_wrapped(layout(2), 4), "same")
        self.assertEqual(wrapped, plain)

    def test_real_end_difference_is_not_silently_dropped(self):
        a = timeline_wrapped(layout(), 3)
        a["transition"]["end_boxes"][0]["bbox_2d"][0] += 1
        with self.assertRaisesRegex(DraftError, "END differs from START"):
            make_source(a, "same")

    def test_explicit_mid_is_not_silently_dropped(self):
        a = timeline_wrapped(layout(), 3)
        a["timeline_experimental"]["mid_boxes"] = copy.deepcopy(a["boxes"])
        with self.assertRaisesRegex(DraftError, "Explicit MID"):
            make_source(a, "same")

    def test_multikey_is_not_silently_dropped(self):
        a = timeline_wrapped(layout(), 4)
        a["timeline_experimental"]["keyframes"] = {
            "a": [{"time": 0.5, "bbox_2d": [20, 100, 280, 900]}]
        }
        with self.assertRaisesRegex(DraftError, "Multi-Key"):
            make_source(a, "same")

    def test_top_level_timeline_and_keyframes_still_rejected(self):
        for name in ("timeline", "keyframes"):
            with self.subTest(name=name):
                a = layout()
                a[name] = {}
                with self.assertRaisesRegex(DraftError, "START only"):
                    make_source(a, "same")

    def test_unknown_transition_metadata_is_not_discarded(self):
        a = timeline_wrapped(layout(), 3)
        a["transition"]["future_field"] = True
        with self.assertRaisesRegex(DraftError, "unknown transition metadata"):
            make_source(a, "same")

    def test_overscan_nan_wrong_order_and_boolean_rejected(self):
        for coords in ([-1,100,280,900],[20,100,1001,900],[280,100,20,900],
                       [float("nan"),100,280,900],[True,100,280,900]):
            with self.subTest(coords=coords):
                a=layout();a["boxes"][0]["bbox_2d"]=coords
                with self.assertRaises(DraftError):make_source(a,"same")

    def test_unknown_schema_and_coordinate_system_rejected(self):
        a=layout();a["schema"]="h3_structured_ir_v1"
        with self.assertRaises(DraftError):make_source(a,"same")
        a=layout();a["canvas"]["coordinate_space"]="normalized_0_1"
        with self.assertRaises(DraftError):make_source(a,"same")

    def test_duplicate_slot_d_and_empty_rejected(self):
        for change in (lambda a:a["boxes"].append(copy.deepcopy(a["boxes"][0])),
                       lambda a:a["boxes"][0].update(slot="d"),lambda a:a.update(boxes=[])):
            a=layout();change(a)
            with self.assertRaises(DraftError):make_source(a,"same")

    def test_metadata_live_object_and_limits_rejected(self):
        a=layout();a["custom"]=object()
        with self.assertRaises(DraftError):make_source(a,"same")
        with self.assertRaises(DraftError):make_source(layout(),"x"*128001)
        a=layout();a["extra"]={"x":0}
        for _ in range(15):a["extra"]={"x":a["extra"]}
        with self.assertRaises(DraftError):make_source(a,"same")

    def test_corrupt_hash_and_unknown_metadata_field_rejected(self):
        a=make_source(layout(),"red");a["prompt_hash"]="0"*64
        with self.assertRaises(DraftError):validate_source(a)
        a=make_source(layout(),"red");a["extra"]=1
        with self.assertRaises(DraftError):validate_source(a)

    def test_attach_preserves_tensors_references_and_all_other_metadata(self):
        tensor=torch.randn(1,2,3); ref=torch.ones(1,24,1,2,2)
        p=[[tensor,{"minimax_refs":[{"kind":"image","latent":ref}],"other":{"value":7}}]]
        out=attach_source(p,layout(),"red")
        self.assertIs(out[0][0],tensor)
        self.assertIs(out[0][1]["minimax_refs"],p[0][1]["minimax_refs"])
        self.assertIs(out[0][1]["other"],p[0][1]["other"])
        self.assertNotIn(KEY,p[0][1])
        self.assertIsNot(out[0][1],p[0][1])
        self.assertEqual(out[0][1][KEY]["compiled_prompt"],"red")

    def test_attach_is_idempotent_but_rejects_conflicting_audit(self):
        p=[[torch.ones(1),{}]];p=attach_source(p,layout(),"red")
        self.assertEqual(p[0][1][KEY],attach_source(p,layout(),"red")[0][1][KEY])
        with self.assertRaises(DraftError):attach_source(p,layout(),"blue")

    def test_multiple_scheduled_entries_and_negative_preserved(self):
        p=[[torch.ones(1),{"timestep_start":0}], [torch.ones(1),{"timestep_start":.5}]]
        out=attach_source(p,layout(3),"red")
        manifest=structured_manifest({"positive":[x[1] for x in out],"negative":[{}]})
        self.assertEqual(len(manifest["items"]),2)
        self.assertEqual(manifest["items"][1]["slots"],["a","b","c"])

    def test_geometry_mismatch_rejected(self):
        c={"positive":[{KEY:make_source(layout(),"red")}]}
        with self.assertRaisesRegex(DraftError,"size differs"):structured_manifest(c,{"width":64,"height":32})

    def test_public_audit_node_ports(self):
        node=load_bridge()
        self.assertEqual(set(node.INPUT_TYPES()["required"]),{"positive","layout","compiled_prompt"})
        self.assertEqual(node.RETURN_TYPES,("CONDITIONING",))
        out=node().attach([[torch.ones(1),{}]],layout(),"red")[0]
        self.assertIn(KEY,out[0][1])


class StructuredLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.b,self.n,self.g,self.s,self.sig,self.lat,self.vae=setup()
        self.e=SamplerEngine(self.b)

    def install(self,n=1,text="red hair"):
        self.g.original_conds["positive"][0][KEY]=make_source(layout(n),text)

    def draft(self):
        return self.e.draft_external(self.n,self.g,self.s,self.sig,self.lat,self.vae,3).state

    def sample_calls(self):
        return len([x for x in self.b.calls if x[0]=="sample"])

    def test_b0_no_marker_preserves_existing_path(self):
        state=self.draft();self.assertFalse(state.summary()["structured_layout"]["present"])
        out=self.e.continue_external(state,state.state_id)
        self.assertFalse(out.report["structured_layout"]["present"])
        self.assertFalse(out.report["new_noise"])

    def test_b1_single_slot_preview_continue_and_snapshot(self):
        self.install();state=self.draft()
        audit=state.summary()["structured_layout"]
        self.assertTrue(audit["present"])
        self.assertEqual(audit["items"][0]["slot_count"],1)
        self.assertIsNot(state.guider.original_conds["positive"][0][KEY],self.g.original_conds["positive"][0][KEY])
        out=self.e.continue_external(state,state.state_id)
        self.assertEqual(out.report["structured_layout"],audit)
        self.assertEqual(self.n.calls,1)
        self.assertFalse(out.report["conditioning_reencoded"])

    def test_b2_three_slots(self):
        self.install(3);state=self.draft()
        out=self.e.continue_external(state,state.state_id)
        self.assertEqual(out.report["structured_layout"]["items"][0]["slots"],["a","b","c"])

    def test_b3_bbox_changed_stale_go_rejected_before_sampling(self):
        self.install();state=self.draft();a=layout();a["boxes"][0]["bbox_2d"][0]+=1
        self.g.original_conds["positive"][0][KEY]=make_source(a,"red hair")
        before=self.sample_calls()
        with self.assertRaisesRegex(DraftError,"Structured layout changed"):self.e.continue_external(state,state.state_id)
        self.assertEqual(self.sample_calls(),before)
        self.assertFalse(state._lock.locked())

    def test_prompt_changed_stale_go_rejected(self):
        self.install();state=self.draft();self.install(text="blue hair")
        with self.assertRaisesRegex(DraftError,"Structured layout changed"):self.e.continue_external(state,state.state_id)

    def test_metadata_removed_stale_go_rejected(self):
        self.install();state=self.draft();self.g.original_conds["positive"][0].pop(KEY)
        with self.assertRaisesRegex(DraftError,"Structured layout changed"):state.verify(state.state_id)

    def test_metadata_added_after_preview_rejected(self):
        state=self.draft();self.install()
        with self.assertRaisesRegex(DraftError,"Structured layout changed"):state.verify(state.state_id)

    def test_stored_and_source_both_mutated_fail_whole_payload_check(self):
        self.install();state=self.draft();new=make_source(layout(),"changed")
        state.guider.original_conds["positive"][0][KEY]=copy.deepcopy(new)
        self.g.original_conds["positive"][0][KEY]=copy.deepcopy(new)
        with self.assertRaises(DraftError):state.verify(state.state_id)

    def test_fresh_guider_isolated_and_has_identical_layout_metadata(self):
        self.install();state=self.draft();fresh=state.fresh_guider()
        self.assertEqual(fresh.original_conds["positive"][0][KEY],state.guider.original_conds["positive"][0][KEY])
        fresh.original_conds["positive"][0][KEY]["scope"]="invalid"
        state.verify(state.state_id)

    def test_bad_metadata_fails_before_draft_sampling(self):
        self.install();self.g.original_conds["positive"][0][KEY]["prompt_hash"]="0"*64
        with self.assertRaises(DraftError):self.draft()
        self.assertEqual(self.sample_calls(),0)

    def test_metadata_cannot_change_numerical_result_host_double(self):
        full,_=self.b.sample_external(Noise(self.n.seed),self.g,self.s,self.lat,self.sig)
        self.install();state=self.draft();out=self.e.continue_external(state,state.state_id)
        for a,b in zip(full["samples"].unbind(),out.latent["samples"].unbind()):
            self.assertTrue(torch.allclose(a,b,atol=2e-7,rtol=2e-7))

    def test_native_reference_fingerprint_not_changed(self):
        from h3draft.sampler_state import native_reference_manifest
        before=native_reference_manifest(self.g.original_conds)[1]
        self.install();state=self.draft()
        self.assertEqual(state.reference_hash,before)
        self.e.continue_external(state,state.state_id)

    def test_reference_change_still_rejected_with_layout(self):
        self.install();state=self.draft()
        self.g.original_conds["positive"][0]["minimax_refs"][0]["latent"].add_(1)
        with self.assertRaisesRegex(DraftError,"reference conditioning changed"):state.verify(state.state_id)

    def test_upstream_layout_json_change_invalidates_existing_graph_fingerprint(self):
        graph={"1":{"class_type":"H3StructuredCanvas","inputs":{"layout_json":"A"}},
               "2":{"class_type":"H3StructuredLayoutAudit","inputs":{"layout":["1",0]}},
               "3":{"class_type":"H3DraftSampler","inputs":{"guider":["2",0]}}}
        a=graph_signature(graph,"3");graph["1"]["inputs"]["layout_json"]="B"
        self.assertNotEqual(a,graph_signature(graph,"3"))


if __name__ == "__main__":
    unittest.main()
