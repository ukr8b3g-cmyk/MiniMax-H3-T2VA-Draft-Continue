import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import * as H3Logic from "./logic.mjs?v=1.7.1";

const {
  branch, signature, continueRequest, safeWorkflow, newSeed,
  DRAFT_CLASSES, CONTINUE_CLASSES, externalSeedTarget,
} = H3Logic;

const sessionPhaseRestorable = H3Logic.sessionPhaseRestorable ?? (phase =>
  phase === "ready" || phase === "stale" || phase === "complete");
const copyReviewRuntime = H3Logic.copyReviewRuntime ?? (runtime => {
  if(!sessionPhaseRestorable(runtime?.phase)) return null;
  return {
    phase:runtime.phase,
    ready:runtime.ready??null,
    message:runtime.message??"",
    previewWall:Number.isFinite(runtime.previewWall)?runtime.previewWall:null,
    approvedStateId:typeof runtime.approvedStateId==="string"?runtime.approvedStateId:null,
  };
});

const acceptDraftReadyReport = H3Logic.acceptDraftReadyReport ?? ((phase) => {
  if (phase === "continue_queued" || phase === "complete") return false;
  return true;
});

const reviewUiState = H3Logic.reviewUiState ?? ((input = {}) => {
  const phase = input.phase ?? "preview_required";
  const current = Number.isInteger(input.currentStep) ? input.currentStep : 0;
  const total = Number.isInteger(input.totalSteps) ? input.totalSteps : 0;
  const remaining = Math.max(0, total - current);
  const locked = {
    state: phase, kind: "idle",
    draft: { title: "PREVIEW REQUIRED", detail: "Review Frame 0 before GO." },
    continue: { title: "WAITING FOR PREVIEW", detail: "Generate and review a Preview first." },
    canPreview: true, canReroll: true, canGo: false,
  };
  if (phase === "ready") return {
    ...locked, kind: "ready", canGo: true,
    draft: { title: total ? `READY · ${current}/${total}` : "READY", detail: "Frame 0 preview · estimate" },
    continue: { title: "READY TO GO", detail: total ? `${remaining} sampling steps remaining` : "Continue the reviewed Draft State" },
  };
  if (phase === "preview_queued") return {
    ...locked, kind: "busy", canPreview: false, canReroll: false,
    draft: { title: "PREVIEW RUNNING", detail: "Generating Frame 0 from the full-length H3 latent." },
    continue: { title: "WAITING", detail: "GO unlocks after Preview completes." },
  };
  if (phase === "stale") return {
    ...locked, kind: "warning",
    draft: { title: "PREVIEW STALE", detail: input.message || "Settings changed after Preview." },
    continue: { title: "NEW PREVIEW REQUIRED", detail: "GO is locked until Preview is regenerated." },
  };
  if (phase === "continue_queued") return {
    ...locked, kind: "busy", canPreview: false, canReroll: false,
    draft: { title: "REVIEWED", detail: "The approved Draft State is continuing." },
    continue: { title: "CONTINUING", detail: total ? `Resume ${current}/${total} · ${remaining} steps remaining` : "Continuing reviewed state" },
  };
  if (phase === "complete") return {
    ...locked, kind: "ready",
    draft: { title: "REVIEWED", detail: "Preview/approval cycle completed." },
    continue: { title: "COMPLETE", detail: input.message || "Reviewed Draft State completed." },
  };
  if (phase === "error") return {
    ...locked, kind: "error",
    draft: { title: "REVIEW ERROR", detail: input.message || "Preview/Continue failed." },
    continue: { title: "NOT READY", detail: "Generate a new Preview before GO." },
  };
  return locked;
});

const DRAFT="H3T2VADraft";
const outputTypes=new Set(["SaveVideo","SaveImage","PreviewImage","SaveAnimatedWEBP","PreviewAny"]);
const isDraft=node=>DRAFT_CLASSES.has(node?.comfyClass??node?.type);
const isContinue=node=>CONTINUE_CLASSES.has(node?.comfyClass??node?.type);
const pending=new Map();
const workflowRuntime=new Map();
let activeWorkflowPath=null;
let staleCheckTimer=null;
let staleCheckRunning=false;
const widget=(node,name)=>node?.widgets?.find(w=>w.name===name);

function errorText(error){
  return error?.response?.error?.message??error?.message??String(error);
}

function draftRuntime(node){
  return copyReviewRuntime({
    phase:node?._h3Phase,
    ready:node?._h3Ready,
    message:node?._h3Message,
    previewWall:node?._h3PreviewWall,
    approvedStateId:node?._h3ApprovedStateId,
  });
}

function captureRuntime(){
  const snapshots={};
  for(const node of app.rootGraph?._nodes??[]){
    if(!isDraft(node))continue;
    const runtime=draftRuntime(node);
    if(runtime)snapshots[String(node.id)]=runtime;
  }
  return snapshots;
}

function selectedWorkflowPath(){
  const selectors=[
    ".p-togglebutton-checked [data-workflow-path]",
    ".p-togglebutton-checked[data-workflow-path]",
    "[aria-pressed=true] [data-workflow-path]",
    "[data-p-highlight=true] [data-workflow-path]",
  ];
  for(const selector of selectors){
    const el=document.querySelector(selector);
    const path=el?.dataset?.workflowPath;
    if(path)return path;
  }
  return null;
}

function openWorkflowPaths(){
  return new Set(Array.from(document.querySelectorAll("[data-workflow-path]"))
    .map(el=>el?.dataset?.workflowPath)
    .filter(path=>typeof path==="string"&&path.length));
}

function pruneClosedWorkflowRuntime(){
  const open=openWorkflowPaths();
  if(!open.size)return;
  for(const path of workflowRuntime.keys()){
    if(!open.has(path))workflowRuntime.delete(path);
  }
}

function rememberActiveRuntime(){
  const path=activeWorkflowPath??selectedWorkflowPath();
  if(!path)return;
  const snapshots=captureRuntime();
  if(Object.keys(snapshots).length)workflowRuntime.set(path,snapshots);
}

function restoreRuntime(path){
  if(!path)return false;
  const snapshots=workflowRuntime.get(path);
  if(!snapshots)return false;
  let restored=false;
  for(const [id,runtime] of Object.entries(snapshots)){
    const node=app.rootGraph?.getNodeById?.(isNaN(+id)?id:+id)??app.rootGraph?.getNodeById?.(id);
    if(!isDraft(node)||!runtime)continue;
    node._h3Phase=runtime.phase;
    node._h3Ready=runtime.ready;
    node._h3Message=runtime.message;
    node._h3PreviewWall=runtime.previewWall;
    node._h3ApprovedStateId=runtime.approvedStateId;
    syncDraft(node);
    restored=true;
  }
  return restored;
}

async function validateReadyDrafts(){
  if(staleCheckRunning||app.configuringGraph)return;
  const drafts=(app.rootGraph?._nodes??[]).filter(node=>isDraft(node)&&node._h3Phase==="ready"&&node._h3Ready?.graph_hash);
  if(!drafts.length)return;
  staleCheckRunning=true;
  try{
    const p=await app.graphToPrompt();
    for(const draft of drafts){
      if(draft._h3Phase!=="ready"||!draft._h3Ready?.graph_hash)continue;
      let changed=false;
      try{
        changed=(await signature(p.output,String(draft.id)))!==draft._h3Ready.graph_hash;
      }catch{
        changed=true;
      }
      if(changed){
        setDraftPhase(draft,"stale",{clearReady:true,message:"Settings changed after Preview."});
      }
    }
    rememberActiveRuntime();
  }finally{
    staleCheckRunning=false;
  }
}

function scheduleReadyValidation(){
  if(staleCheckTimer)clearTimeout(staleCheckTimer);
  staleCheckTimer=setTimeout(()=>{
    staleCheckTimer=null;
    void validateReadyDrafts();
  },80);
}

function graphLink(graph,id){
  if(id==null||!graph)return null;
  return graph.links?.[id]??graph.links?.get?.(id)??null;
}

function directDraftForContinue(node){
  const graph=node?.graph??app.graph;
  const input=node?.inputs?.find?.(item=>item?.name==="draft_state");
  const link=graphLink(graph,input?.link);
  const origin=link?.origin_id;
  const draft=origin!=null?graph?.getNodeById?.(origin):null;
  return isDraft(draft)?draft:null;
}

function linkedContinues(draft){
  const graph=draft?.graph??app.graph;
  const nodes=graph?._nodes??graph?.nodes??[];
  return Array.from(nodes).filter(node=>isContinue(node)&&directDraftForContinue(node)===draft);
}

function reviewInput(draft){
  const ready=draft?._h3Ready;
  const settings=ready?.settings??{};
  return {
    phase:draft?._h3Phase??"preview_required",
    currentStep:ready?.current_step,
    totalSteps:settings.total_steps,
    width:settings.width,
    height:settings.height,
    frameCount:settings.frame_count,
    wallSeconds:draft?._h3PreviewWall,
    message:draft?._h3Message??"",
  };
}

function applyPanel(node,role,ui){
  if(!node?._h3Panel)return;
  const block=role==="draft"?ui.draft:ui.continue;
  node._h3Panel.dataset.kind=ui.kind;
  node._h3Panel.querySelector("strong").textContent=block.title;
  node._h3Panel.querySelector("small").textContent=block.detail;
  const buttons=node._h3Buttons??{};
  if(role==="draft"){
    if(buttons.preview){
      buttons.preview.disabled=!ui.canPreview;
      buttons.preview.textContent=ui.state==="preview_queued"?"Preview running…":"Preview";
    }
    if(buttons.reroll){
      buttons.reroll.disabled=!ui.canReroll;
      buttons.reroll.textContent=ui.state==="preview_queued"?"Please wait…":"New seed + Preview";
    }
  }else if(buttons.go){
    buttons.go.disabled=!ui.canGo;
    buttons.go.textContent=
      ui.state==="ready"?"GO · Continue this draft":
      ui.state==="continue_queued"?"Continuing…":
      ui.state==="stale"?"GO · New Preview required":
      ui.state==="complete"?"COMPLETE":
      "GO · Preview required";
  }
  node.setDirtyCanvas?.(true,true);
}

function syncDraft(draft){
  if(!isDraft(draft))return;
  const ui=reviewUiState(reviewInput(draft));
  applyPanel(draft,"draft",ui);
  for(const node of linkedContinues(draft))applyPanel(node,"continue",ui);
}

function setDraftPhase(draft,phase,{ready,message,wall,clearReady=false}={}){
  if(!isDraft(draft))return;
  draft._h3Phase=phase;
  if(clearReady)draft._h3Ready=null;
  if(ready!==undefined)draft._h3Ready=ready;
  if(message!==undefined)draft._h3Message=message;
  if(wall!==undefined)draft._h3PreviewWall=wall;
  syncDraft(draft);
  rememberActiveRuntime();
}

function standalonePhase(node,phase,message=""){
  const ui=reviewUiState({phase,message});
  applyPanel(node,isDraft(node)?"draft":"continue",ui);
}

function markError(node,message){
  const draft=isDraft(node)?node:directDraftForContinue(node);
  if(draft)setDraftPhase(draft,"error",{clearReady:true,message});
  else standalonePhase(node,"error",message);
}

function actionButton(label,callback){
  const button=document.createElement("button");
  button.type="button";
  button.className="h3-draft-action";
  button.textContent=label;
  button.addEventListener("pointerdown",event=>event.stopPropagation());
  button.addEventListener("click",event=>{
    event.preventDefault();
    event.stopPropagation();
    if(!button.disabled)callback();
  });
  return button;
}

function buildPanel(node,draftRole){
  const panel=document.createElement("div");
  panel.className="h3-draft-status";
  panel.appendChild(document.createElement("strong"));
  panel.appendChild(document.createElement("small"));
  const actions=document.createElement("div");
  actions.className="h3-draft-actions";
  panel.appendChild(actions);
  node._h3Buttons={};
  if(draftRole){
    const preview=actionButton("Preview",()=>queue(node,"preview"));
    const reroll=actionButton("New seed + Preview",()=>queue(node,"reroll"));
    actions.append(preview,reroll);
    node._h3Buttons.preview=preview;
    node._h3Buttons.reroll=reroll;
  }else{
    const go=actionButton("GO · Preview required",()=>queue(node,"continue"));
    actions.append(go);
    node._h3Buttons.go=go;
  }
  node._h3Panel=panel;
  const dom=node.addDOMWidget("h3_status","h3_status",panel,{serialize:false});
  dom.computeSize=()=>[0,draftRole?110:104];
  return panel;
}

async function queue(node,action){
  if(node._h3Pending)return;
  node._h3Pending=true;
  try{
    const p=await app.graphToPrompt();
    const id=String(node.id);
    let output;
    let draft=node;

    if(isDraft(node)){
      if(action==="reroll"){
        const external=externalSeedTarget(p.output,id);
        const provider=(node.comfyClass==="H3DraftSampler"||node.type==="H3DraftSampler")
          ?(external?app.graph.getNodeById(external.nodeId):null):node;
        const w=provider&&widget(provider,provider===node?"seed":external.name);
        if(!w)throw new Error("Change the upstream NOISE seed, then press Preview. This button rerolls only a directly connected Core RandomNoise node.");
        w.value=newSeed();
        w.callback?.(w.value);
        const fresh=await app.graphToPrompt();
        Object.assign(p,fresh);
      }
      output=branch(p.output,[id]);
      node._h3ApprovedStateId=null;
      setDraftPhase(node,"preview_queued",{clearReady:true,message:"",wall:null});
    }else{
      const link=p.output[id]?.inputs?.draft_state;
      const wanted=p.output[id]?.class_type==="H3ContinueSampler"?"H3DraftSampler":DRAFT;
      if(!Array.isArray(link)||p.output[link[0]]?.class_type!==wanted)
        throw new Error("Connect the matching Draft node directly to draft_state. Place the review pair outside subgraphs; upstream subgraphs may be expanded by Core.");
      draft=app.graph.getNodeById(link[0]);
      const ready=draft?._h3Ready;
      if(!ready?.state_id||draft._h3Pending){
        if(draft)setDraftPhase(draft,"preview_required",{clearReady:true});
        throw new Error("Wait for a Preview and review it before pressing GO.");
      }
      if(await signature(p.output,link[0])!==ready.graph_hash){
        setDraftPhase(draft,"stale",{clearReady:true,message:"Settings changed after Preview."});
        throw new Error("Draft settings or model/LoRA changed. Preview again; the old image is not approval of the new settings.");
      }
      output=continueRequest(p.output,id,ready.state_id,outputTypes);
      draft._h3ApprovedStateId=ready.state_id;
      setDraftPhase(draft,"continue_queued",{message:""});
    }

    const response=await api.queuePrompt(0,{output,workflow:safeWorkflow(p.workflow)});
    pending.set(response.prompt_id,{node,draft});
  }catch(error){
    node._h3Pending=false;
    const linked=isDraft(node)?node:directDraftForContinue(node);
    const message=errorText(error);
    if(linked&&linked._h3Phase==="stale"){
      linked._h3Message=linked._h3Message||message;
      syncDraft(linked);
    }else if(linked&&linked._h3Phase==="preview_required"){
      linked._h3Message=message;
      syncDraft(linked);
    }else{
      markError(node,message);
    }
    console.error("[H3 Draft Continue]",error);
  }
}

app.registerExtension({
  name:"MiniMax.H3.DraftContinue",
  setup(){
    globalThis.__H3_DRAFT_CONTINUE_UI__ = {
      loaded: true,
      version: "1.7.1",
      logicStateContract: typeof H3Logic.reviewUiState === "function" ? "native" : "fallback",
    };
    console.info("[H3 Draft Continue] Phase 4A UI loaded", globalThis.__H3_DRAFT_CONTINUE_UI__);
    if(!document.getElementById("h3-draft-style")){
      const css=document.createElement("style");
      css.id="h3-draft-style";
      css.textContent=`
.h3-draft-status{box-sizing:border-box;width:100%;padding:9px 12px;background:#152029;border:1px solid #31525d;border-radius:8px;color:#e7eef1;font:13px/1.45 system-ui,sans-serif;overflow:hidden}
.h3-draft-status strong{display:block;font-weight:650}
.h3-draft-status small{display:block;font-size:11px;color:#b1c5ce;white-space:normal;overflow-wrap:anywhere}
.h3-draft-actions{display:flex;gap:7px;margin-top:8px;flex-wrap:wrap}
.h3-draft-action{appearance:none;border:1px solid #45636d;border-radius:6px;background:#20333b;color:#edf5f7;padding:6px 10px;font:600 12px/1.2 system-ui,sans-serif;cursor:pointer}
.h3-draft-action:hover:not(:disabled){background:#29434d}
.h3-draft-action:disabled{cursor:not-allowed;opacity:.46}
.h3-draft-status[data-kind=ready]{border-color:#2c9f93}
.h3-draft-status[data-kind=busy]{border-color:#b98740}
.h3-draft-status[data-kind=error],.h3-draft-status[data-kind=warning]{border-color:#bc7469}
`;
      document.head.appendChild(css);
    }

    api.addEventListener("graphChanged",()=>scheduleReadyValidation());

    for(const eventName of ["input","change","mouseup","keyup"]){
      window.addEventListener(eventName,()=>scheduleReadyValidation(),true);
    }

    if(document.body){
      const observer=new MutationObserver(()=>pruneClosedWorkflowRuntime());
      observer.observe(document.body,{childList:true,subtree:true});
    }

    for(const event of ["execution_error","execution_interrupted","execution_success"]){
      api.addEventListener(event,e=>{
        const id=e.detail?.prompt_id;
        const item=pending.get(id);
        if(!item)return;
        pending.delete(id);
        item.node._h3Pending=false;
        if(event==="execution_success"){
          if(isContinue(item.node)&&item.draft?._h3Phase==="continue_queued"){
            setDraftPhase(item.draft,"complete",{message:"Continue completed successfully."});
          }
        }else{
          const message=e.detail?.exception_message??"The review run failed. Generate a new Preview.";
          markError(item.draft??item.node,message);
        }
      });
    }
  },

  beforeLoadGraph(){
    rememberActiveRuntime();
  },

  afterLoadGraph(){
    requestAnimationFrame(()=>{
      const path=selectedWorkflowPath();
      activeWorkflowPath=path;
      const restored=restoreRuntime(path);
      if(restored)console.info("[H3 Draft Continue] Restored session review state for open workflow tab.",path);
      pruneClosedWorkflowRuntime();
    });
  },

  async beforeRegisterNodeDef(nodeType,nodeData){
    if(nodeData.output_node===true)outputTypes.add(nodeData.name);
    if(!DRAFT_CLASSES.has(nodeData.name)&&!CONTINUE_CLASSES.has(nodeData.name))return;

    const draftRole=DRAFT_CLASSES.has(nodeData.name);
    const oldCreate=nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated=function(){
      const result=oldCreate?.apply(this,arguments);
      this._h3Ready=null;
      this._h3Pending=false;
      this._h3Phase="preview_required";
      this._h3Message="";
      this._h3PreviewWall=null;
      this._h3ApprovedStateId=null;
      buildPanel(this,draftRole);
      if(draftRole){
        this.color="#203c42";
        this.bgcolor="#18282d";
      }else{
        this.color="#493323";
        this.bgcolor="#2b241f";
      }
      standalonePhase(this,"preview_required");
      return result;
    };

    const oldExecuted=nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted=function(message){
      oldExecuted?.apply(this,arguments);
      const report=message?.h3_draft?.[0];
      if(!report)return;
      this._h3Pending=false;

      if(report.status==="ready"){
        const state=report.state;
        const incomingId=state?.state_id??"";
        if(!acceptDraftReadyReport(this._h3Phase,incomingId,this._h3ApprovedStateId??"")){
          console.info("[H3 Draft Continue] Ignored late Draft ready report", {
            phase:this._h3Phase,
            state_id:incomingId,
            approved_state_id:this._h3ApprovedStateId??"",
          });
          return;
        }
        this._h3ApprovedStateId=null;
        setDraftPhase(this,"ready",{ready:state,message:"",wall:report.total_wall_s});
        return;
      }

      if(report.status==="complete"){
        const linked=directDraftForContinue(this);
        const samplerMode=report.operation==="sampler_continue";
        const count=report.sampling_transitions??report.denoiser_evaluations;
        const detail=`${count} resumed steps · ${report.total_wall_s.toFixed(1)}s · ${samplerMode?"Standard LATENT ready":"VIDEO ready"}`;
        if(linked)setDraftPhase(linked,"complete",{message:detail});
        else standalonePhase(this,"complete",detail);
        return;
      }

      if(report.status==="awaiting_approval"){
        const linked=directDraftForContinue(this);
        if(linked?._h3Ready)syncDraft(linked);
        else if(linked)setDraftPhase(linked,"preview_required",{clearReady:true});
        else standalonePhase(this,"preview_required");
      }
    };

    const oldConfigure=nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure=function(){
      const result=oldConfigure?.apply(this,arguments);
      this._h3Ready=null;
      this._h3Pending=false;
      this._h3Phase="preview_required";
      this._h3Message="";
      this._h3PreviewWall=null;
      this._h3ApprovedStateId=null;

      if(!draftRole){
        const go=widget(this,"go");
        const id=widget(this,"approved_state_id");
        if(go)go.value=false;
        if(id)id.value="";
      }
      standalonePhase(this,"preview_required");
      if(draftRole)queueMicrotask(()=>syncDraft(this));
      return result;
    };
  },
});
