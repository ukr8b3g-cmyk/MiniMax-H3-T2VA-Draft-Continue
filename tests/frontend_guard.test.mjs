import test from "node:test";
import assert from "node:assert/strict";
import {installFrontendGuard, isReviewRequest, UI_BUILD} from "../web/frontend_guard.mjs";
import {installLoadGraphDataLifecycleBridge} from "../web/lifecycle.mjs";

const body = JSON.stringify({prompt:{"15":{class_type:"H3DraftSampler",inputs:{preview_steps:3}}}});
function fixture() {
  const requests=[];
  let manifest={protocol:1,ui_build:UI_BUILD,server_session:"a".repeat(32),assets_available:true};
  const runtime={loaded:true,version:UI_BUILD,logicStateContract:"native",lifecycleBridge:"loadGraphData-wrapper"};
  const app={loadGraphData:async()=>true};
  installLoadGraphDataLifecycleBridge(app);
  const api={
    addEventListener(){},
    async fetchApi(route, options, ...extra) {
      requests.push({route,options,extra,self:this});
      if(route==="/h3draft/ui-build")return Response.json(manifest);
      return Response.json({prompt_id:"test"});
    },
  };
  const guard=installFrontendGuard({api,app,runtime});
  return {api,app,runtime,guard,requests,setManifest:v=>{manifest=v;}};
}

test("relevant request detection includes legacy and generic nodes, not other workflows",()=>{
  assert.equal(isReviewRequest("/prompt",{method:"POST",body}),true);
  assert.equal(isReviewRequest("/api/prompt?x=1",{method:"post",body}),true);
  assert.equal(isReviewRequest("/prompt",{method:"POST",body:body.replace('H3DraftSampler','H3T2VADraft')}),true);
  assert.equal(isReviewRequest("/prompt",{method:"POST",body:body.replace('H3DraftSampler','KSampler')}),false);
  assert.equal(isReviewRequest("/upload/image",{method:"POST",body}),false);
  assert.equal(isReviewRequest("/prompt",{method:"POST",body:"invalid"}),false);
});
test("verify and stamp only review requests without changing body or other options",async()=>{
  const f=fixture();
  const options={method:"POST",body,headers:{"X-Other":"keep"},credentials:"include"};
  const extra={signal:"preserved future argument"};
  await f.api.fetchApi("/prompt",options,extra);
  const manifestCall=f.requests[0];
  assert.equal(manifestCall.options.cache,"no-store");
  const last=f.requests.at(-1);
  assert.equal(last.options.body,body);
  assert.equal(last.options.headers.get("X-Other"),"keep");
  assert.equal(last.options.headers.get("X-H3-Draft-UI"),UI_BUILD);
  assert.equal(last.options.headers.get("X-H3-Draft-Session"),"a".repeat(32));
  assert.equal(last.options.credentials,"include");
  assert.equal(last.extra[0],extra);
  assert.equal(last.self,f.api);
  assert.equal(options.headers["X-H3-Draft-UI"],undefined);
  assert.equal(f.runtime.frontendGuard.status,"verified");
});
test("missing/old evaluated runtime never reaches prompt endpoint",async()=>{
  for(const version of [undefined,"1.1.1","1.7.4"]) {
    const f=fixture(); f.runtime.version=version;
    await assert.rejects(f.api.fetchApi("/prompt",{method:"POST",body}),/expected H3 UI/);
    assert.equal(f.requests.length,0);
    assert.equal(f.guard.state.status,"reload_required");
  }
});
test("missing actual lifecycle bridge does not pass on a diagnostic string alone",async()=>{
  const f=fixture();f.app.loadGraphData=async()=>true;
  await assert.rejects(f.guard.verify(),/lifecycle bridge/);
  assert.equal(f.requests.length,0);
});
test("server build mismatch locks old page",async()=>{
  const f=fixture();f.setManifest({protocol:1,ui_build:"0.0.0",server_session:"a".repeat(32),assets_available:true});
  await assert.rejects(f.api.fetchApi("/prompt",{method:"POST",body}),/do not match/);
  assert.equal(f.requests.filter(x=>x.route==="/prompt").length,0);
});
test("backend restart latches reload required, never blesses old approval with new epoch",async()=>{
  const f=fixture();await f.guard.verify();
  f.setManifest({protocol:1,ui_build:UI_BUILD,server_session:"b".repeat(32),assets_available:true});
  await assert.rejects(f.api.fetchApi("/prompt",{method:"POST",body}),/ComfyUI restarted/);
  await assert.rejects(f.guard.verify(),/ComfyUI restarted/);
  assert.equal(f.requests.filter(x=>x.route==="/prompt").length,0);
});
test("unrelated requests pass through unchanged and without manifest IO",async()=>{
  const f=fixture();const options={method:"GET"};
  await f.api.fetchApi("/queue",options);
  assert.equal(f.requests.length,1);
  assert.equal(f.requests[0].options,options);
});
test("installation is idempotent",()=>{
  const f=fixture(), wrapped=f.api.fetchApi;
  assert.equal(installFrontendGuard({api:f.api,app:f.app,runtime:f.runtime}),f.guard);
  assert.equal(f.api.fetchApi,wrapped);
});
test("incomplete asset installation is not certified",async()=>{
  const f=fixture();f.setManifest({protocol:1,ui_build:UI_BUILD,server_session:"a".repeat(32),assets_available:false});
  await assert.rejects(f.guard.verify(),/do not match/);
});
