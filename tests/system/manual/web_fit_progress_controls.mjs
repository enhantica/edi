// Protocol controls only; synthetic states are never application evidence.
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {roundedStatusActionRect} from './web_status_action_lifetime.mjs';
import {fittingObservationKind,hasRunningProgress} from '../../fixtures/e04_t11_wasm/browser_observations.mjs';
import {beginFitProgress,endFitProgress,isLiveFitProgress,advancesLiveFitProgress,observesOrderedFitProgress} from './web_fit_progress.mjs';

const idle={running:false,visible:false,text:''};
const live={running:true,visible:true,text:'fitting · it 3'};
let count=0;
const iterations = values => values.map(value => ({...live,text:`fitting · it ${value}`}));
for (const values of [[0,4],[0,1],[0]]) {
  assert(observesOrderedFitProgress(iterations(values),8),
    'A fast fit retains genuine running-counter observations without promising a frame per iteration');count++;
  assert(!advancesLiveFitProgress(iterations(values),8),
    'Coalesced fast-fit counters cannot impersonate the sustained frame-liveness proof');count++;
}
for (const [states,final] of [[iterations([4,1]),8],[iterations([9]),8],
  [iterations([0]),NaN],[iterations([0]),0],[[],8],
  [[idle],8],[[{...live,visible:false}],8],[[{...live,text:'Success · it 4'}],8]]) {
  assert(!observesOrderedFitProgress(states,final),
    'Fast-fit sampling still refuses reversed, out-of-range, absent, hidden and completed counters');count++;
}
for (const values of [[0,1,1,2,5],[1,3,4,5]]) {
  assert(advancesLiveFitProgress(iterations(values),5),
    'The indicator must advance through distinct intermediate values while actually running');count++;
}
for (const [states,final] of [[iterations([0,5]),5],[iterations([1,1,5]),5],
  [iterations([1,5,2]),5],[iterations([1,2,6]),5],
  [iterations([3,2,5]),5],[iterations([1,2]),2],[iterations([1,2]),NaN],
  [iterations([1,2]).map(state=>({...state,running:false})),5],
  [iterations([1,2]).map(state=>({...state,visible:false})),5],
  [iterations([1,2]).map(state=>({...state,text:'Success · it 3'})),5]]) {
  assert(!advancesLiveFitProgress(states,final),
    'Only zero/final, repeated or reversed counts, malformed completion and idle/hidden reports cannot impersonate live advancement');count++;
}
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

// Authored protocol operands: no application evidence or sampled runtime values.
const ownedStop = {text:'Stop',control:'statusBar.fit.button',
  action:'statusBar.fit.button.accessibleAction',role:'button',running:true,
  visible:true,enabled:true,actionVisible:true,actionEnabled:true,connected:true,domVisible:true,
  nativeRect:{x:10.25,y:20.25,width:30.25,height:10.25},
  actionRect:{x:10.25,y:20.25,width:30.25,height:10.25},
  domRect:{x:10,y:20,width:30,height:10}};
assert.equal(fittingObservationKind(ownedStop),'control',
  'The real declared Stop grammar needs the exact native/child/DOM owner rectangle');
assert(hasRunningProgress([ownedStop,'fitting · it 2']),
  'An owned active Stop and real running iteration grammar form the two-part witness');
assert(hasRunningProgress(['stop-circle Stop fitting','fitting · it 2']) &&
  hasRunningProgress(['Cancel fitting','fitting · it 2']),
  'Both original explicit running-control spellings retain their prior grammar');
for (const value of ['Stop','Cancel','Stop now','Stop fitting soon','Stopped','Fit','Refit',
  'Continue','Maximum iterations 400',null,undefined,{},[]])
  assert.equal(fittingObservationKind(value),null,
    'Unowned one-word, unrelated, terminal and malformed text cannot impersonate the status action');
for (const mutate of [
  x=>x.control='assistant.stopVisibleAction',x=>x.action='other.accessibleAction',
  x=>x.role='generic',x=>x.running=false,x=>x.visible=false,x=>x.enabled=false,
  x=>x.actionVisible=false,x=>x.actionEnabled=false,x=>x.connected=false,x=>x.domVisible=false,
  x=>x.text='Cancel',x=>x.domRect.x++,x=>x.actionRect.width++,
  x=>x.nativeRect.width=0,x=>x.nativeRect.x=NaN,x=>delete x.domRect,
]) {
  const damaged=structuredClone(ownedStop);mutate(damaged);
  assert.equal(fittingObservationKind(damaged),null,
    'Every wrong-owner, geometry, role, unavailable, stale or malformed ownership channel refuses');
  assert(!hasRunningProgress([damaged,'fitting · it 2']),
    'A valid iteration cannot rescue a damaged control ownership witness');
}
assert(!hasRunningProgress([ownedStop]) && !hasRunningProgress(['Stop','fitting · it 2']),
  'Neither actual control alone nor unrelated Stop text completes running progress');
console.log('closed Stop ownership grammar controls green; original frame/counter controls retained');

// Closed Qt-primary conversion operands; no browser output is used as an oracle.
const qtSignedCoordinateCases = [
  [-0.5,-1],[-1.5,-2],[-10.5,-11],[-0.499999999999,0],[-0,0],
  [0.5,1],[1.5,2],[10.5,11],[0.499999999999,0],
  [2147483647,2147483647],[2147483647.5,2147483647],
  [2147483648,2147483647],[Number.MAX_VALUE,2147483647],
  [-2147483648,-2147483648],[-2147483648.5,-2147483648],
  [-2147483649,-2147483648],[-Number.MAX_VALUE,-2147483648],
];
for (const [coordinate,integer] of qtSignedCoordinateCases) {
  const truthful=structuredClone(ownedStop);
  truthful.nativeRect.x=truthful.nativeRect.y=coordinate;
  truthful.actionRect.x=truthful.actionRect.y=coordinate;
  truthful.domRect.x=truthful.domRect.y=integer;
  assert.equal(fittingObservationKind(truthful),'control',
    'Signed half ties and finite int overflow follow the pinned Qt saturating rectangle conversion');
  const wrongDom=structuredClone(truthful);wrongDom.domRect.x=integer+1;
  assert.equal(fittingObservationKind(wrongDom),null,
    'The adjacent wrong DOM pixel cannot match the same signed or saturated Qt rectangle');
  const wrongChild=structuredClone(truthful);
  wrongChild.actionRect.x=integer===2147483647?integer-1:integer+1;
  assert.equal(fittingObservationKind(wrongChild),null,
    'A child in the adjacent integer pixel cannot borrow the outer signed or saturated rectangle');
}
for (const [size,integer] of [[0.5,1],[1.5,2],[2147483648,2147483647],
  [Number.MAX_VALUE,2147483647]]) {
  const truthful=structuredClone(ownedStop);
  truthful.nativeRect.width=truthful.actionRect.width=size;truthful.domRect.width=integer;
  truthful.nativeRect.height=truthful.actionRect.height=size;truthful.domRect.height=integer;
  assert.equal(fittingObservationKind(truthful),'control',
    'QSizeF positive half ties and finite overflow use the same pinned conversion as position');
  const wrong=structuredClone(truthful);wrong.domRect.width=integer-1;
  assert.equal(fittingObservationKind(wrong),null,
    'A mismatched converted QSize dimension cannot impersonate the current native rectangle');
}
const negativeTieMismatch=structuredClone(ownedStop);
negativeTieMismatch.nativeRect.x=-0.5;negativeTieMismatch.actionRect.x=-0.499999999999;
negativeTieMismatch.domRect.x=-1;
assert.equal(fittingObservationKind(negativeTieMismatch),null,
  'Native and child values on opposite sides of a negative half boundary remain distinct');
for (const coordinate of [NaN,Infinity,-Infinity]) {
  const damaged=structuredClone(ownedStop);damaged.nativeRect.y=coordinate;
  assert.equal(fittingObservationKind(damaged),null,
    'Nonfinite geometry refuses before Qt integer conversion rather than producing a matching pixel');
}
console.log('signed/saturating Qt rectangle controls green; no application geometry pass claimed');

// This companion runs only when the actual341 module is installed/composed.
for (const [coordinate,integer] of qtSignedCoordinateCases) {
  assert.deepEqual(roundedStatusActionRect({x:coordinate,y:coordinate,width:30.25,height:10.25}),
    {x:integer,y:integer,width:30,height:10},
    'The actual lifetime helper shares the independently anchored signed and saturated Qt domain');
}
assert.deepEqual(roundedStatusActionRect({x:-0.5,y:0.5,width:1.5,height:2147483648}),
  {x:-1,y:1,width:2,height:2147483647},
  'The actual lifetime helper uses the same conversion for position and size');
for (const coordinate of [NaN,Infinity,-Infinity])
  assert.throws(()=>roundedStatusActionRect({x:coordinate,y:0,width:30,height:10}),
    /finite before Qt integer conversion/,
    'The lifetime helper refuses nonfinite native geometry rather than silently producing a rectangle');

for (const text of ['Stop','stop-circle Stop']) {
  const observed = {...ownedStop,text};
  assert.equal(fittingObservationKind(observed),'control',
    'The owned status-bar running button exposes Stop, with or without its icon text');
  assert(hasRunningProgress([observed,'fitting · it 2']),
    'The owned current Stop label and a live iteration together satisfy progress observation');
}
for (const text of ['Fit','Continue','Refit','Start fitting','Stop fitting','Cancel fitting','Stop search','Unstoppable']) {
  const observed = {...ownedStop,text};
  assert.equal(fittingObservationKind(observed),null,
    'Idle actions, retired labels and unrelated text on the current owner cannot impersonate running progress');
  assert(!hasRunningProgress([observed,'fitting · it 2']),
    'Live iteration text alone cannot replace the actual running fit control');
}
assert(!hasRunningProgress([ownedStop,'Success','Iterations 20']),
  'The current Stop control without a live iteration cannot impersonate running progress');
console.log('status-bar fitting label controls green; no application fit green claimed');
