import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { branch, signature, continueRequest, safeWorkflow, newSeed, DRAFT_CLASSES, CONTINUE_CLASSES, externalSeedTarget } from "./logic.mjs";
const DRAFT="H3T2VADraft";
const outputTypes=new Set(["SaveVideo","SaveImage","PreviewImage","SaveAnimatedWEBP","PreviewAny"]);
const isDraft=node=>DRAFT_CLASSES.has(node.comfyClass??node.type);
const pending=new Map(); const widget=(node,name)=>node.widgets?.find(w=>w.name===name);
function status(node,title,detail="",kind="idle"){if(!node._h3Panel)return;node._h3Panel.dataset.kind=kind;
 node._h3Panel.querySelector("strong").textContent=title;node._h3Panel.querySelector("small").textContent=detail;node.setDirtyCanvas?.(true,true);}
function errorText(error){return error?.response?.error?.message??error?.message??String(error);}
async function queue(node,action){if(node._h3Pending)return;node._h3Pending=true;try{
 const p=await app.graphToPrompt();const id=String(node.id);let output;
 if(isDraft(node)){if(action==="reroll"){const external=externalSeedTarget(p.output,id);
   const provider=(node.comfyClass==="H3DraftSampler"||node.type==="H3DraftSampler")?(external?app.graph.getNodeById(external.nodeId):null):node;
   const w=provider&&widget(provider,provider===node?"seed":external.name);
   if(!w)throw new Error("Change the upstream NOISE seed, then press Preview. This button rerolls only a directly connected Core RandomNoise node.");
   w.value=newSeed();w.callback?.(w.value);node._h3Ready=null;const fresh=await app.graphToPrompt();Object.assign(p,fresh);}
   output=branch(p.output,[id]);status(node,"Queued · Preview","Same full-length H3 latent → one x0 Frame 0","busy");
 }else{const link=p.output[id]?.inputs?.draft_state;
   const wanted=p.output[id]?.class_type==="H3ContinueSampler"?"H3DraftSampler":DRAFT;
   if(!Array.isArray(link)||p.output[link[0]]?.class_type!==wanted)throw new Error("Connect the matching Draft node directly to draft_state. Place the review pair outside subgraphs; upstream subgraphs may be expanded by Core.");
   const draft=app.graph.getNodeById(link[0]),ready=draft?._h3Ready;
   if(!ready?.state_id||draft._h3Pending)throw new Error("Wait for a Preview and review it before pressing GO.");
   if(await signature(p.output,link[0])!==ready.graph_hash){status(draft,"Settings changed","Generate a new Preview before GO.","warning");throw new Error("Draft settings or model/LoRA changed. Preview again; the old image is not approval of the new settings.");}
   output=continueRequest(p.output,id,ready.state_id,outputTypes);status(node,"Queued · Continue",`Resume ${ready.current_step}/${ready.settings.total_steps} → ${ready.remaining_steps} remaining steps`,"busy");
 }
 const response=await api.queuePrompt(0,{output,workflow:safeWorkflow(p.workflow)});pending.set(response.prompt_id,node);
}catch(error){node._h3Pending=false;status(node,"Not queued",errorText(error),"error");console.error("[H3 Draft Continue]",error);}}
app.registerExtension({name:"MiniMax.H3.DraftContinue",setup(){
 if(!document.getElementById("h3-draft-style")){const css=document.createElement("style");css.id="h3-draft-style";
 css.textContent=`.h3-draft-status{box-sizing:border-box;width:100%;padding:9px 12px;background:#152029;border:1px solid #31525d;border-radius:8px;color:#e7eef1;font:13px/1.45 system-ui,sans-serif;overflow:hidden}.h3-draft-status strong{display:block;font-weight:650}.h3-draft-status small{display:block;font-size:11px;color:#b1c5ce;white-space:normal;overflow-wrap:anywhere}.h3-draft-status[data-kind=ready]{border-color:#2c9f93}.h3-draft-status[data-kind=busy]{border-color:#b98740}.h3-draft-status[data-kind=error],.h3-draft-status[data-kind=warning]{border-color:#bc7469}`;document.head.appendChild(css);}
 for(const event of ["execution_error","execution_interrupted","execution_success"])api.addEventListener(event,e=>{const id=e.detail?.prompt_id,node=pending.get(id);if(!node)return;pending.delete(id);node._h3Pending=false;if(event!=="execution_success")status(node,event==="execution_interrupted"?"Interrupted":"Execution failed",e.detail?.exception_message??"The draft was not approved. See the Core execution error.","error");});
},async beforeRegisterNodeDef(nodeType,nodeData){if(nodeData.output_node===true)outputTypes.add(nodeData.name);if(!DRAFT_CLASSES.has(nodeData.name)&&!CONTINUE_CLASSES.has(nodeData.name))return;
 const draft=DRAFT_CLASSES.has(nodeData.name),oldCreate=nodeType.prototype.onNodeCreated;
 nodeType.prototype.onNodeCreated=function(){const result=oldCreate?.apply(this,arguments);this._h3Ready=null;this._h3Pending=false;
 const panel=document.createElement("div");panel.className="h3-draft-status";panel.appendChild(document.createElement("strong"));panel.appendChild(document.createElement("small"));this._h3Panel=panel;
 const dom=this.addDOMWidget("h3_status","h3_status",panel,{serialize:false});dom.computeSize=()=>[0,74];
 if(draft){this.color="#203c42";this.bgcolor="#18282d";this.addWidget("button","Preview",null,()=>queue(this,"preview"),{serialize:false});this.addWidget("button","New seed + Preview",null,()=>queue(this,"reroll"),{serialize:false});}
 else{this.color="#493323";this.bgcolor="#2b241f";this.addWidget("button","GO · Continue this draft",null,()=>queue(this,"continue"),{serialize:false});}
 status(this,draft?"Preview first":"Review first",draft?"Same model + Turbo LoRA for Preview and Continue.":"GO accepts only the connected, reviewed Draft State.");return result;};
 const oldExecuted=nodeType.prototype.onExecuted;nodeType.prototype.onExecuted=function(message){oldExecuted?.apply(this,arguments);const report=message?.h3_draft?.[0];if(!report)return;this._h3Pending=false;
 if(report.status==="ready"){this._h3Ready=report.state;const s=report.state;status(this,`READY · ${s.current_step}/${s.settings.total_steps} steps`,`${s.settings.width} × ${s.settings.height} · ${s.settings.frame_count}f · ${report.total_wall_s.toFixed(1)}s · Preview is an estimate`,"ready");}
 else if(report.status==="complete"){const samplerMode=report.operation==="sampler_continue",count=report.sampling_transitions??report.denoiser_evaluations;status(this,samplerMode?"COMPLETE · Standard LATENT":"COMPLETE · Same T2VA continued",`${count} remaining steps · ${report.total_wall_s.toFixed(1)}s · ${samplerMode?"LATENT → your Decode / Save branches":"VIDEO → SaveVideo"}`,"ready");}
 else status(this,"Review first","Click GO after reviewing the Preview image.");};
 const oldConfigure=nodeType.prototype.onConfigure;nodeType.prototype.onConfigure=function(){const result=oldConfigure?.apply(this,arguments);this._h3Ready=null;this._h3Pending=false;if(!draft){const go=widget(this,"go"),id=widget(this,"approved_state_id");if(go)go.value=false;if(id)id.value="";}status(this,"Preview required","Approvals are never restored from a saved workflow.");return result;};
}});
