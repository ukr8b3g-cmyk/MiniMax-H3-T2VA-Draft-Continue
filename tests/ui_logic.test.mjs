import test from 'node:test';import assert from 'node:assert/strict';import {webcrypto} from 'node:crypto';
import {canonical,branch,signature,continueRequest,safeWorkflow,newSeed,reviewUiState,acceptDraftReadyReport} from '../web/logic.mjs';
const fixture=()=>({'1':{class_type:'Loader',inputs:{name:'model'}},'2':{class_type:'H3T2VADraft',inputs:{model:['1',0],duration:5}},'3':{class_type:'H3T2VAContinue',inputs:{draft_state:['2',1],go:false,approved_state_id:''}},'4':{class_type:'SaveVideo',inputs:{video:['3',0]}}});
test('canonical stable',()=>assert.equal(canonical({z:5,a:'人物'}),'{"a":"人物","z":n:4014000000000000}'));
test('ancestor pruning',()=>assert.deepEqual(Object.keys(branch(fixture(),['2'])),['1','2']));
test('GO selected branch',()=>{const r=continueRequest(fixture(),'3','a'.repeat(32));assert.equal(r['3'].inputs.go,true);assert.ok(r['4']);});
test('invalid approval',()=>assert.throws(()=>continueRequest(fixture(),'3','stale')));
test('signature changes upstream',async()=>{const f=fixture(),a=await signature(f,'2',webcrypto);f['1'].inputs.name='different';assert.notEqual(a,await signature(f,'2',webcrypto));});
test('approval never persists',()=>{const f={nodes:[{type:'H3T2VAContinue',widgets_values:[true,'secret'],widgets_values_named:{go:true,approved_state_id:'secret'}}]};assert.equal(safeWorkflow(f).nodes[0].widgets_values[0],false);});
test('seed safe',()=>{for(let i=0;i<20;i++){const s=newSeed(webcrypto);assert.ok(Number.isSafeInteger(s)&&s>=0&&s<=Number.MAX_SAFE_INTEGER);}});

test('review UI starts locked',()=>{
  const s=reviewUiState();
  assert.equal(s.state,'preview_required');
  assert.equal(s.draft.title,'PREVIEW REQUIRED');
  assert.equal(s.continue.title,'WAITING FOR PREVIEW');
  assert.equal(s.canGo,false);
  assert.equal(s.canPreview,true);
});
test('review UI ready unlocks GO',()=>{
  const s=reviewUiState({phase:'ready',currentStep:3,totalSteps:6,width:512,height:768,frameCount:124,wallSeconds:60.5});
  assert.equal(s.draft.title,'READY · 3/6');
  assert.equal(s.continue.title,'READY TO GO');
  assert.equal(s.continue.detail,'3 sampling steps remaining');
  assert.match(s.draft.detail,/512×768/);
  assert.match(s.draft.detail,/Frame 0 preview · estimate/);
  assert.equal(s.canGo,true);
});
test('review UI stale locks GO',()=>{
  const s=reviewUiState({phase:'stale',message:'Settings changed after Preview.'});
  assert.equal(s.draft.title,'PREVIEW STALE');
  assert.equal(s.continue.title,'NEW PREVIEW REQUIRED');
  assert.equal(s.canGo,false);
});
test('review UI running and complete states',()=>{
  const running=reviewUiState({phase:'continue_queued',currentStep:3,totalSteps:6});
  assert.equal(running.continue.title,'CONTINUING');
  assert.equal(running.canPreview,false);
  assert.equal(running.canGo,false);
  const done=reviewUiState({phase:'complete',message:'Standard LATENT ready'});
  assert.equal(done.continue.title,'COMPLETE');
  assert.equal(done.canGo,false);
  assert.equal(done.canPreview,true);
});

test('only ready phase enables GO',()=>{
  for(const phase of ['preview_required','preview_queued','stale','continue_queued','complete','error']){
    assert.equal(reviewUiState({phase,currentStep:3,totalSteps:6}).canGo,false,phase);
  }
  assert.equal(reviewUiState({phase:'ready',currentStep:3,totalSteps:6}).canGo,true);
});
test('sampler approval never persists',()=>{
  const f={nodes:[{type:'H3ContinueSampler',widgets_values:[true,'a'.repeat(32)],widgets_values_named:{go:true,approved_state_id:'a'.repeat(32)}}]};
  const clean=safeWorkflow(f).nodes[0];
  assert.equal(clean.widgets_values[0],false);
  assert.equal(clean.widgets_values[1],'');
  assert.equal(clean.widgets_values_named.go,false);
  assert.equal(clean.widgets_values_named.approved_state_id,'');
});

test('late Draft ready cannot roll back Continue state',()=>{
  const approved='a'.repeat(32);
  assert.equal(acceptDraftReadyReport('continue_queued',approved,approved),false);
  assert.equal(acceptDraftReadyReport('complete',approved,approved),false);
});
test('fresh Preview ready is accepted only after explicit reset',()=>{
  const old='a'.repeat(32), fresh='b'.repeat(32);
  assert.equal(acceptDraftReadyReport('complete',fresh,old),false);
  assert.equal(acceptDraftReadyReport('preview_queued',fresh,old),true);
});
