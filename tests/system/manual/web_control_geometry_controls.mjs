// Protocol controls only; these invented snapshots make no real application claim.
import assert from 'node:assert/strict';
import {controlPointer, restoreCanvasViewport, waitControlGeometry} from './web_control_geometry.mjs';

const name='structures.load';
const actual={objectName:name,x:710,y:260,width:270,height:38,visible:true,enabled:true};
const evaluate = state => async expression => expression.startsWith('typeof ') ? 'function' : state;
assert.deepEqual(await controlPointer(evaluate(actual),name),{x:845,y:279},
  'Current native geometry must produce the center for a trusted pointer action');
let count=1;
for (const state of [null,{...actual,objectName:'experiments.create'},
  {...actual,visible:false},{...actual,enabled:false},{...actual,visible:1},
  {...actual,x:NaN},{...actual,y:Infinity},{...actual,width:'270'},
  {...actual,width:0},{...actual,height:-1},{...actual,x:-1},
  {...actual,x:1200},{...actual,y:750}]) {
  await assert.rejects(controlPointer(evaluate(state),name), /actual named|Native control geometry/,
    'Missing, retargeted, hidden, disabled, malformed and outside-viewport controls cannot receive the pointer');
  count++;
}
await assert.rejects(controlPointer(async ()=>'undefined',name), /must expose current native control geometry/,
  'Missing native geometry must refuse rather than click an old accessibility rectangle');
count++;
console.log(`${count} geometry protocol controls green; no real picker green claimed`);

const rowName='examples.open.pd-neut-cwl_lbco-hrpt_start-4';
const listName='examples.list';
const list={objectName:listName,x:710,y:260,width:270,height:400,visible:true,enabled:true};
const row={...list,objectName:rowName,height:80};
const inList = (item, container=list) => async expression => expression.startsWith('typeof ') ? 'function' :
  expression.includes(JSON.stringify(rowName)) ? item : container;
assert.deepEqual(await controlPointer(inList(row),rowName,listName),{x:845,y:300},
  'A materialised catalogue row must receive real input at its fresh native center');
for (const state of [{...row,y:240},{...row,y:610},{...row,x:700},{...row,width:280},
  {...row,objectName:'examples.open.pd-neut-cwl_cosio-d20_start-1'},{...row,visible:false}])
  await assert.rejects(controlPointer(inList(state),rowName,listName), /actual named|actual catalogue row/,
    'A clipped, recycled, retargeted or hidden catalogue row cannot borrow a stale accessible target');
for (const container of [null,{...list,visible:false},{...list,enabled:false},{...list,height:Infinity},
  {...list,objectName:'other.list'}])
  await assert.rejects(controlPointer(inList(row,container),rowName,listName), /actual named|Native control geometry/,
    'A missing, hidden, disabled or malformed catalogue viewport must refuse row input');
console.log('catalogue clipping and recycled-row geometry refusal controls green');

const viewport={after:{x:0,y:0,width:1280,height:768}};
await restoreCanvasViewport(async()=>viewport);
for (const changed of [null, {}, {x:1}, {y:-10}, {width:1279}, {height:769}, {x:NaN}]) {
  const state=changed === null ? null : {after:{...viewport.after,...changed}};
  if (changed && Object.keys(changed).length === 0) state.after={};
  await assert.rejects(restoreCanvasViewport(async()=>state), /actual fixed canvas/,
    'Unrestored focus scrolling, wrong viewport dimensions and missing geometry must refuse input');
}
await assert.rejects(restoreCanvasViewport(async()=>{throw Error('unreadable canvas');}), /unreadable canvas/,
  'Canvas read errors must propagate without an invented fixed viewport');
console.log('real canvas origin and dimension refusal controls green');

const dialogName='saveAs.zip';
const dialog={...actual,objectName:dialogName,checked:true};
let frames=0;
const pending=[null,{...dialog,visible:false},{...dialog,enabled:false},dialog];
assert.deepEqual(await waitControlGeometry(async()=>pending.shift(),async()=>++frames,dialogName),dialog,
  'A real dialog target must wait through absence, hidden state and disabled state without requiring an AX node');
assert.equal(frames,3,'Readiness must advance frames until the actual native target becomes actionable');
assert.deepEqual(await waitControlGeometry(async()=>({...dialog,enabled:false}),async()=>{},dialogName,{enabled:false}),
  {...dialog,enabled:false},'Passive disabled fit-result labels must remain observable without becoming pointer targets');
for(const state of [{...dialog,objectName:'open.zip'},{...dialog,x:NaN},{...dialog,width:'270'},
  {...dialog,x:1279},{...dialog,enabled:1}])
  await assert.rejects(waitControlGeometry(async()=>state,async()=>{},dialogName,{enabled:false}),
    /Native dialog observations/,'Malformed, retargeted and clipped native observations cannot replace a real dialog witness');
for(const state of [null,{...dialog,visible:false},{...dialog,enabled:false}])
  await assert.rejects(waitControlGeometry(async()=>state,async()=>{},dialogName,{timeoutMs:0}),
    /must expose its declared native control/,'A missing, hidden or disabled dialog must refuse without an AX fallback');
await assert.rejects(waitControlGeometry(async()=>{throw Error('2 visible items are named saveAs.zip');},async()=>{},dialogName),
  /2 visible items/,'Ambiguous native controls must propagate their error rather than time out as absent');
await assert.rejects(waitControlGeometry(async()=>{throw Error('native hook unavailable');},async()=>{},dialogName),
  /native hook unavailable/,'Native hook failures must propagate rather than invent dialog readiness');
console.log('dialog readiness and passive-result protocol controls green; no real dialog run claimed');
