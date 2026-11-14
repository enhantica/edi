// Independent protocol controls. These are harness checks, never app-view evidence.
import assert from 'node:assert/strict';
import { runInNewContext } from 'node:vm';
import { inspectDevelopDiagnostics } from './web_develop_diagnostics.mjs';
const fields = ['Threads (ideal): 4', 'Threads (OpenMP team): no OpenMP',
  'Browser cores (hardwareConcurrency): 4'];
const text = mode => [...fields, `Engine backend: ${mode === 'serial-control' ? 'serial' : 'std::thread pool'}`,
  `Engine workers: ${mode === 'serial-control' ? 1 : 4}`,
  'WebAssembly SIMD: on'].join('\n');
async function exercise(mode, change = value => value, missing = false, brokenClose = false, oneWorker = false) {
  let visible = false;
  const calls = [];
  const window = missing ? {} : {ediDevelopDiagnostics: async action => {
    calls.push(action);
    if (action === 'open') visible = true;
    if (action === 'close' && !brokenClose) visible = false;
    return change({preferencesVisible: visible, developSelected: visible,
      diagnosticsVisible: visible, textVisible: visible, text: text(mode), providerText: text(mode)}, visible);
  }};
  const evidence = [];
  const realClock = Date.now;
  let clock = 0;
  // Exhaust the readiness bound without wall-clock waiting, then exercise the view assertion.
  Date.now = () => (clock += 10001);
  try {
    await inspectDevelopDiagnostics(expression => runInNewContext(expression, {window}),
      async () => {}, mode,
      async value => evidence.push(value), async () => calls.push('capture'), oneWorker);
  } finally { Date.now = realClock; }
  assert(calls.includes('capture') && calls.includes('close') && !visible,
    'A valid dialog protocol must capture actual visibility and close before subsequent workflow');
  assert.equal(evidence.at(-1).diagnostics, oneWorker?text(mode).replace('workers: 4','workers: 1'):text(mode),
    'A valid dialog protocol must retain the complete displayed diagnostic text');
}
let count = 0;
for (const mode of ['multithread', 'shim']) { await exercise(mode); count++; }
await exercise('multithread', v=>{const text=v.text.replace('workers: 4','workers: 1');return {...v,text,providerText:text};}, false, false, true);count++;
const controls = [
  ['wrong one-worker selection',()=>exercise('multithread',undefined,false,false,true),/actual worker selection/],
  ['missing bridge', () => exercise('multithread', undefined, true), /must expose ediDevelopDiagnostics/],
  ['unselected Develop', () => exercise('multithread', (v, shown) => ({...v, developSelected: shown ? false : v.developSelected})), /must be visible/],
  ['hidden TextArea', () => exercise('multithread', (v, shown) => ({...v, textVisible: shown ? false : v.textVisible})), /must be visible/],
  ['provider drift', () => exercise('multithread', v => ({...v, providerText: v.text + '\nstale'})), /must equal the actual/],
  ['missing old line', () => exercise('multithread', v => { const text = v.text.replace(fields[1], ''); return {...v, text, providerText: text}; }), /retain the existing/],
  ['missing backend', () => exercise('multithread', v => { const text = v.text.replace(/Engine backend:[^\n]+/, ''); return {...v, text, providerText: text}; }), /must show engine backend/],
  ['serial advertised as threaded', () => exercise('multithread', v => ({...v, text: text('serial-control'), providerText: text('serial-control')})), /active thread backend and SIMD/],
  ['one threaded worker', () => exercise('multithread', v => { const text = v.text.replace('workers: 4', 'workers: 1'); return {...v, text, providerText: text}; }), /active thread backend and SIMD/],
  ['threaded SIMD off', () => exercise('shim', v => { const text = v.text.replace('SIMD: on', 'SIMD: off'); return {...v, text, providerText: text}; }), /active thread backend and SIMD/],
  ['broken close', () => exercise('multithread', undefined, false, true), /close both actual Qt dialogs/],
];
for (const [name, run, reason] of controls) {
  await assert.rejects(run, reason, 'The Develop protocol must refuse each independent invalid view or backend state');
  console.log(`refused ${name}`); count++;
}
console.log(`${count} protocol controls green; no application or scientific fit green claimed`);
