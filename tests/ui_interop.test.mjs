import test from 'node:test';import assert from 'node:assert/strict';import {webcrypto} from 'node:crypto';
import {branch,continueRequest,downstreamOutputs,signature,externalSeedTarget} from '../web/logic.mjs';
const fixture=()=>({'1':{class_type:'Loader',inputs:{file:'H3'}},'2':{class_type:'RandomNoise',inputs:{noise_seed:17}},'3':{class_type:'H3DraftSampler',inputs:{model:['1',0],noise:['2',0],preview_steps:3}},'4':{class_type:'H3ContinueSampler',inputs:{draft_state:['3',1],go:false,approved_state_id:''}},'5':{class_type:'VAEDecode',inputs:{samples:['4',0],vae:['1',0]}},'6':{class_type:'CreateVideo',inputs:{images:['5',0]}},'7':{class_type:'SaveVideo',inputs:{video:['6',0]}},'90':{class_type:'SaveVideo',inputs:{video:['1',0]}}});
const outputs=new Set(['SaveVideo']);
test('GO traverses downstream saver',()=>{const r=continueRequest(fixture(),'4','a'.repeat(32),outputs);assert.ok(r['5']&&r['6']&&r['7']);assert.ok(!r['90']);});
test('direct RandomNoise reroll target',()=>assert.deepEqual(externalSeedTarget(fixture(),'3'),{nodeId:'2',name:'noise_seed'}));
test('preview queues upstream only',()=>assert.deepEqual(Object.keys(branch(fixture(),['3'])),['1','2','3']));
test('postprocess does not change draft signature',async()=>{const f=fixture(),a=await signature(f,'3',webcrypto);f['5'].inputs.foo=.1;assert.equal(a,await signature(f,'3',webcrypto));});
test('upstream change invalidates signature',async()=>{const f=fixture(),a=await signature(f,'3',webcrypto);f['1'].inputs.file='other';assert.notEqual(a,await signature(f,'3',webcrypto));});
