/** Executes the real extension body against a 1.52.7-style host WITHOUT new
 * beforeLoadGraph/afterLoadGraph hooks. This is a mocked host, not a GPU gate. */
import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFile} from "node:fs/promises";
import * as H3Logic from "../web/logic.mjs";
import {installLoadGraphDataLifecycleBridge} from "../web/lifecycle.mjs";
import {installFrontendGuard,UI_BUILD} from "../web/frontend_guard.mjs";

function stripImports(source){return source.replace(/^import .*;\r?\n/gm,'');}

class Element {
  constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.style={};this.listeners={};this.disabled=false;}
  appendChild(el){this.children.push(el);return el;}
  append(...els){els.forEach(x=>this.appendChild(x));}
  addEventListener(name,cb){this.listeners[name]=cb;}
  querySelector(s){return this.children.find(x=>s.startsWith('.')?x.className===s.slice(1):x.tag===s)??null;}
}
async function host() {
  let extension;
  const wfA={changeTracker:{}},wfB={changeTracker:{}};
  const graph={_nodes:[],links:{17:{origin_id:15,target_id:20,origin_slot:1,target_slot:0}},getNodeById(id){return this._nodes.find(n=>String(n.id)===String(id));}};
  const store={activeWorkflow:wfA};
  let makeNodes=()=>{};
  const app={rootGraph:graph,graph,extensionManager:{workflow:store},
    registerExtension(ext){extension=ext;},
    async graphToPrompt(){return {output:{},workflow:{nodes:[]}};},
    async loadGraphData(_data,clean=true,_view=true,wf){
      if(clean){graph._nodes.forEach(n=>{n.graph=null;});graph._nodes=[];}
      makeNodes(); // ComfyUI graph.configure() resets runtime on the new nodes.
      store.activeWorkflow=wf; // Workflow activation occurs before load resolves.
      return true;
    },
  };
  const apiListeners=new Map();
  const api={
    addEventListener(name,callback){const list=apiListeners.get(name)??[];list.push(callback);apiListeners.set(name,list);},
    dispatch(name,detail={}){for(const callback of apiListeners.get(name)??[])callback({detail});},
    async fetchApi(route){
      if(route==='/h3draft/ui-build')return Response.json({protocol:1,ui_build:UI_BUILD,assets_available:true,server_session:'a'.repeat(32)});
      throw new Error('No generation/queue allowed in this host test');
    }
  };
  const document={head:new Element('head'),createElement:tag=>new Element(tag),getElementById:()=>null};
  const context=vm.createContext({app,api,H3Logic,installLoadGraphDataLifecycleBridge,installFrontendGuard,
    document,window:{addEventListener(){}},console:{info(){},warn(){},error(){}},
    setTimeout,clearTimeout,queueMicrotask});
  const source=stripImports(await readFile(new URL('../web/draft.js',import.meta.url),'utf8'))+
    '\nglobalThis.__H3_TEST__={pending};';
  vm.runInContext(source,context,{filename:'web/draft.js'});
  class Node {
    constructor(id,type){this.id=id;this.type=type;this.comfyClass=type;this.graph=graph;
      this.widgets=[{name:'go',value:false},{name:'approved_state_id',value:''}];
      this.inputs=type==='H3ContinueSampler'?[{name:'draft_state',link:17}]:[];
      this.outputs=type==='H3DraftSampler'?[
        {name:'preview_image',links:[]},{name:'draft_state',links:[17]},{name:'report',links:[]}
      ]:[];
    }
    addDOMWidget(){return {};}
    setDirtyCanvas(){}
  }
  class Draft extends Node {}
  class Continue extends Node {}
  await extension.beforeRegisterNodeDef(Draft,{name:'H3DraftSampler'});
  await extension.beforeRegisterNodeDef(Continue,{name:'H3ContinueSampler'});
  makeNodes=()=>{
    graph.links={17:{origin_id:15,target_id:20,origin_slot:1,target_slot:0}};
    const d=new Draft(15,'H3DraftSampler'),c=new Continue(20,'H3ContinueSampler');
    graph._nodes=[d,c];d.onNodeCreated();c.onNodeCreated();d.onConfigure();c.onConfigure();
  };
  makeNodes();extension.setup();
  await context.__H3_DRAFT_CONTINUE_UI__.checkFrontend();
  return {app,api,context,graph,wfA,wfB,extension,Draft,Continue};
}
async function settle(){await new Promise(r=>queueMicrotask(r));await new Promise(r=>queueMicrotask(r));}
function disconnectPair(h,id=17){const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20),i={origin_id:15,target_id:20,origin_slot:1,target_slot:0};delete h.graph.links[id];d.outputs[1].links=[];c.inputs[0].link=null;c.onConnectionsChange?.(1,0,false,i,c.inputs[0]);d.onConnectionsChange?.(2,0,false,i,d.outputs[0]);}
function connectPair(h,did,id){const d=h.graph.getNodeById(did),c=h.graph.getNodeById(20),i={origin_id:did,target_id:20,origin_slot:1,target_slot:0};h.graph.links[id]=i;d.outputs[1].links=[id];c.inputs[0].link=id;d.onConnectionsChange?.(2,1,true,i,d.outputs[1]);c.onConnectionsChange?.(1,0,true,i,c.inputs[0]);}
function ready(h,{pending=true}={}) {
  const draft=h.graph.getNodeById(15);
  if(pending)draft._h3Pending=true;
  draft.onExecuted({h3_draft:[{status:'ready',total_wall_s:1,
    state:{state_id:'b'.repeat(32),graph_hash:'test',current_step:3,settings:{total_steps:6,width:512,height:768,frame_count:124}}}]});
}

test('actual extension runtime verifies build and locks GO before Preview',async()=>{
  const h=await host();
  assert.equal(h.context.__H3_DRAFT_CONTINUE_UI__.version,UI_BUILD);
  assert.equal(h.context.__H3_DRAFT_CONTINUE_UI__.frontendGuard.status,'verified');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
});
test('actual extension READY round-trip via loadGraphData without modern hooks',async()=>{
  const h=await host();ready(h);
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,false);
  await h.app.loadGraphData({},true,true,h.wfB);
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
  await h.app.loadGraphData({},true,true,h.wfA);
  assert.equal(h.graph.getNodeById(15)._h3Phase,'ready');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,false);
});
test('actual extension COMPLETE round-trip remains terminal and close/reopen resets',async()=>{
  const h=await host();ready(h);
  const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20);
  d._h3Phase='continue_queued';d._h3ApprovedStateId='b'.repeat(32);c._h3Pending=true;
  h.context.__H3_TEST__.pending.set('roundtrip',{node:c,draft:d});
  c.onExecuted({h3_draft:[{status:'complete',operation:'sampler_continue',sampling_transitions:3,total_wall_s:2}]});
  assert.equal(d._h3Phase,'continue_queued');assert.equal(c._h3Pending,true);
  h.api.dispatch('execution_success',{prompt_id:'roundtrip'});await settle();
  assert.equal(d._h3Phase,'complete');assert.equal(c._h3Pending,false);
  await h.app.loadGraphData({},true,true,h.wfB);await h.app.loadGraphData({},true,true,h.wfA);
  assert.equal(h.graph.getNodeById(15)._h3Phase,'complete');
  await h.app.loadGraphData({},true,true,h.wfB);h.wfA.changeTracker={};await h.app.loadGraphData({},true,true,h.wfA);
  assert.equal(h.graph.getNodeById(15)._h3Phase,'preview_required');
});

test('page boot ignores historical READY/COMPLETE reports without current-session execution',async()=>{
  const h=await host();
  ready(h,{pending:false});
  assert.equal(h.graph.getNodeById(15)._h3Phase,'preview_required');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
  h.graph.getNodeById(20).onExecuted({h3_draft:[{status:'complete',operation:'sampler_continue',sampling_transitions:3,total_wall_s:2}]});
  assert.equal(h.graph.getNodeById(15)._h3Phase,'preview_required');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
});

test('simulated full page reload starts PREVIEW REQUIRED even if prior page was READY',async()=>{
  const oldPage=await host();
  ready(oldPage);
  assert.equal(oldPage.graph.getNodeById(15)._h3Phase,'ready');

  // A new host/context models a new evaluated document: no WeakMap/session owner survives.
  const reloaded=await host();
  ready(reloaded,{pending:false}); // historical output replay during startup
  assert.equal(reloaded.graph.getNodeById(15)._h3Phase,'preview_required');
  assert.equal(reloaded.graph.getNodeById(20)._h3Buttons.go.disabled,true);
});
test('host import stripping accepts Windows CRLF',()=>{assert.equal(stripImports('import { app } from "x";\r\nconst value=1;\r\n'),'const value=1;\r\n');});
test('C5 disconnect and reconnect never reuse approval',async()=>{const h=await host();ready(h);await settle();const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20);disconnectPair(h);await settle();assert.equal(d._h3Phase,'preview_required');assert.equal(d._h3Ready,null);assert.equal(c._h3Buttons.go.disabled,true);connectPair(h,15,18);await settle();assert.equal(d._h3Phase,'preview_required');assert.equal(c._h3Buttons.go.disabled,true);});
test('C7 execution_error clears approval',async()=>{const h=await host();ready(h);await settle();const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20);d._h3ApprovedStateId='b'.repeat(32);d._h3Phase='continue_queued';c._h3Pending=true;h.context.__H3_TEST__.pending.set('err',{node:c,draft:d});h.api.dispatch('execution_error',{prompt_id:'err',exception_message:'forced'});await settle();assert.equal(d._h3Phase,'error');assert.equal(d._h3Ready,null);assert.equal(d._h3ApprovedStateId,null);assert.equal(c._h3Pending,false);});
test('C8 COMPLETE waits for execution_success',async()=>{const h=await host();ready(h);await settle();const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20);d._h3ApprovedStateId='b'.repeat(32);d._h3Phase='continue_queued';c._h3Pending=true;h.context.__H3_TEST__.pending.set('ok',{node:c,draft:d});c.onExecuted({h3_draft:[{status:'complete',operation:'sampler_continue',sampling_transitions:3,total_wall_s:24.8}]});assert.equal(d._h3Phase,'continue_queued');assert.equal(c._h3Pending,true);h.api.dispatch('execution_success',{prompt_id:'ok'});await settle();assert.equal(d._h3Phase,'complete');assert.equal(c._h3Pending,false);});
test('C8 downstream error never displays COMPLETE',async()=>{const h=await host();ready(h);await settle();const d=h.graph.getNodeById(15),c=h.graph.getNodeById(20);d._h3ApprovedStateId='b'.repeat(32);d._h3Phase='continue_queued';c._h3Pending=true;h.context.__H3_TEST__.pending.set('down',{node:c,draft:d});c.onExecuted({h3_draft:[{status:'complete',operation:'sampler_continue',sampling_transitions:3,total_wall_s:24.8}]});assert.equal(d._h3Phase,'continue_queued');h.api.dispatch('execution_error',{prompt_id:'down',exception_message:'downstream'});await settle();assert.equal(d._h3Phase,'error');assert.equal(d._h3ApprovedStateId,null);assert.equal(c._h3Pending,false);});

