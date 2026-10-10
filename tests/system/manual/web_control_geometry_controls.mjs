// Protocol controls only; these invented snapshots make no real application claim.
import assert from 'node:assert/strict';
import {controlPointer} from './web_control_geometry.mjs';

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
