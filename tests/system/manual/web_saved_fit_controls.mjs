// Invented counterfactual records exercise the refusal seam, without claiming a browser result.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {assertSavedProject, assertNativeChi, assertSavedNativeChi, sixSignificantFileValue} from './web_saved_fit.mjs';

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

// Independent authored decimal literals, not captured browser output.
for (const [value, expected] of [
  [0,0], [1.5,1.5], [1.234564,1.23456], [1.234565,1.23457],
  [-1.234565,-1.23457], [123456.5,123457], [-123456.5,-123457],
  [0.00001234565,0.0000123457], [-0.00001234565,-0.0000123457],
  [999999.5,1000000], [9.999995e-9,1e-8], [1.234565e12,1.23457e12],
]) assert.equal(sixSignificantFileValue(value), expected,
  'Declared decimal half-away six-digit projection must retain scale/sign/carry, not binary toPrecision ties');
assertSavedNativeChi(1.23457,1.234565,1e-11);
assertSavedNativeChi(-1.23457,-1.234565,1e-11);
for (const chi of [1.234565,1.23456,1.2346,1.2345701,NaN,Infinity])
  assert.throws(() => assertSavedNativeChi(chi,1.234565,1e-11), /six-significant|finite|browser=/,
    'Raw unrounded values, wrong tie/precision, truncation and nonfinite file values must refuse');
for (const value of [NaN,Infinity,-Infinity,'1.234565',null,undefined])
  assert.throws(() => sixSignificantFileValue(value), /finite numeric/,
    'A file projection cannot silently coerce a malformed or nonfinite reference');
console.log('declared saved-file precision controls green; old full-precision controls retained');
