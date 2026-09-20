/** Executes the real extension body against a 1.52.7-style host WITHOUT new
 * beforeLoadGraph/afterLoadGraph hooks. This is a mocked host, not a GPU gate. */
import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFile} from "node:fs/promises";
import * as H3Logic from "../web/logic.mjs";
import {installLoadGraphDataLifecycleBridge} from "../web/lifecycle.mjs";
import {installFrontendGuard,UI_BUILD} from "../web/frontend_guard.mjs";

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
  const graph={_nodes:[],links:{17:{origin_id:15}},getNodeById(id){return this._nodes.find(n=>String(n.id)===String(id));}};
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
  const api={addEventListener(){},async fetchApi(route){
    if(route==='/h3draft/ui-build')return Response.json({protocol:1,ui_build:UI_BUILD,assets_available:true,server_session:'a'.repeat(32)});
    throw new Error('No generation/queue allowed in this host test');
  }};
  const document={head:new Element('head'),createElement:tag=>new Element(tag),getElementById:()=>null};
  const context=vm.createContext({app,api,H3Logic,installLoadGraphDataLifecycleBridge,installFrontendGuard,
    document,window:{addEventListener(){}},console:{info(){},warn(){},error(){}},
    setTimeout,clearTimeout,queueMicrotask});
  const source=(await readFile(new URL('../web/draft.js',import.meta.url),'utf8')).replace(/^import .*;\n/gm,'');
  vm.runInContext(source,context,{filename:'web/draft.js'});
  class Node {
    constructor(id,type){this.id=id;this.type=type;this.comfyClass=type;this.graph=graph;
      this.widgets=[{name:'go',value:false},{name:'approved_state_id',value:''}];
      this.inputs=type==='H3ContinueSampler'?[{name:'draft_state',link:17}]:[];
    }
    addDOMWidget(){return {};}
    setDirtyCanvas(){}
  }
  class Draft extends Node {}
  class Continue extends Node {}
  await extension.beforeRegisterNodeDef(Draft,{name:'H3DraftSampler'});
  await extension.beforeRegisterNodeDef(Continue,{name:'H3ContinueSampler'});
  makeNodes=()=>{
    const d=new Draft(15,'H3DraftSampler'),c=new Continue(20,'H3ContinueSampler');
    graph._nodes=[d,c];d.onNodeCreated();c.onNodeCreated();d.onConfigure();c.onConfigure();
  };
  makeNodes();extension.setup();
  await context.__H3_DRAFT_CONTINUE_UI__.checkFrontend();
  return {app,api,context,graph,wfA,wfB,extension};
}
function ready(h) {
  h.graph.getNodeById(15).onExecuted({h3_draft:[{status:'ready',total_wall_s:1,
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
  h.graph.getNodeById(20).onExecuted({h3_draft:[{status:'complete',operation:'sampler_continue',sampling_transitions:3,total_wall_s:2}]});
  await h.app.loadGraphData({},true,true,h.wfB);
  await h.app.loadGraphData({},true,true,h.wfA);
  assert.equal(h.graph.getNodeById(15)._h3Phase,'complete');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
  await h.app.loadGraphData({},true,true,h.wfB);
  h.wfA.changeTracker={}; // Persisted workflow close/unload then reopen.
  await h.app.loadGraphData({},true,true,h.wfA);
  assert.equal(h.graph.getNodeById(15)._h3Phase,'preview_required');
  assert.equal(h.graph.getNodeById(20)._h3Buttons.go.disabled,true);
});
