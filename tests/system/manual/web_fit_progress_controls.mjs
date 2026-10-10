// Protocol controls only; synthetic states are never application evidence.
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {beginFitProgress,endFitProgress,isLiveFitProgress} from './web_fit_progress.mjs';

const idle={running:false,visible:false,text:''};
const live={running:true,visible:true,text:'fitting · it 3'};
let count=0;
for(const text of ['fitting · it 1','fitting · it 12']) {
  assert(isLiveFitProgress({...live,text}),
    'Actual running and visible iteration text must satisfy the live progress contract');
  count++;
}
for(const state of [idle,{...live,running:false},{...live,visible:false},
  {...live,running:'true'},{...live,text:'Success · it 3'},
  {...live,text:'Stopped · it 3'},{...live,text:'Maximum iterations 400'},
  {...live,text:'fitting · it 0'},{...live,text:3},null]) {
  assert(!isLiveFitProgress(state),
    'Idle, hidden, stale completed and malformed states cannot impersonate live progress');
  count++;
}
const context={window:{},performance:{now:()=>0},requestAnimationFrame:fn=>setImmediate(fn)};
const evaluate=expression=>runInNewContext(expression,context);
await assert.rejects(beginFitProgress(evaluate),/must expose ediFitProgress/,
  'A missing native progress bridge must refuse the browser workflow');count++;
context.window.ediFitProgress=()=>({running:false,text:''});
await assert.rejects(beginFitProgress(evaluate),/effective bar visibility/,
  'A progress bridge omitting actual visibility must refuse the workflow');count++;
context.window.ediFitProgress=()=>live;
await assert.rejects(beginFitProgress(evaluate),/before the real fitting action/,
  'A stale running fit cannot satisfy a new fitting action');count++;
let call=0;
context.window.ediFitProgress=()=>call++===0?idle:live;
await beginFitProgress(evaluate);
const states=await endFitProgress(evaluate);
assert(states.some(isLiveFitProgress),
  'The observer must sample the actual hook between starting and stopping observation');count++;
context.window.ediFitProgress=()=>++call%2?idle:{running:true,visible:true};
call=0;
await beginFitProgress(evaluate);
await assert.rejects(endFitProgress(evaluate),/live text/,
  'Malformed later samples must not be credited as valid native progress');count++;
call=0;
context.window.ediFitProgress=()=>{if(call++===0)return idle;throw Error('read failed');};
await beginFitProgress(evaluate);
await assert.rejects(endFitProgress(evaluate),/without a page-hook exception/,
  'A failed native progress read must refuse rather than reuse old samples');count++;
console.log(`${count} progress protocol controls green; no application fit green claimed`);
