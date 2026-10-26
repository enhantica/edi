// Invented counterfactual records exercise the refusal seam, without claiming a browser result.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {assertSavedProject, assertNativeChi} from './web_saved_fit.mjs';

for (const [fitCase, name] of [['lbco','pd-neut-cwl_lbco-hrpt'], ['ncaf','pd-neut-tof_ncaf-wish']]) {
  assertSavedProject(name, fitCase);
  for (const wrong of ['cosio_d20_s1', 'lbco_hrpt_s3', '', undefined,
    fitCase === 'lbco' ? 'pd-neut-tof_ncaf-wish' : 'pd-neut-cwl_lbco-hrpt'])
    assert.throws(() => assertSavedProject(wrong, fitCase), /actual saved browser project/,
      'A stale label, adjacent starting model, missing name or other fitted project must refuse');
}
assert.throws(() => assertSavedProject('pd-neut-cwl_lbco-hrpt', 'unknown'), /declared independent reference/,
  'An undeclared case cannot select an independent scientific reference');
const oracle = JSON.parse(await readFile(new URL('../../fixtures/e04_t11_wasm/native.json', import.meta.url)));
const native = oracle.reduced_chi_square;
const tolerance = oracle.absolute_tolerance + oracle.relative_tolerance * Math.abs(native);
assertNativeChi(native, native, tolerance);
assertNativeChi(native + tolerance / 2, native, tolerance);
for (const chi of [NaN, Infinity, -Infinity, 75.61970581633145, native + 2*tolerance, native - 2*tolerance]) {
  assert.throws(() => assertNativeChi(chi, native, tolerance), /browser=.*native=.*tolerance=/,
    'Nonfinite, wrong-project and out-of-tolerance results must refuse and print both scientific operands');
}
for (const [reference, tol] of [[NaN,tolerance], [Infinity,tolerance], [native,NaN], [native,-tolerance]])
  assert.throws(() => assertNativeChi(native, reference, tol), /independent committed native CLI/,
    'An unreadable independent reference or invalid tolerance cannot accept a saved fit');
console.log('saved-project identity and unchanged native parity refusal controls green');
