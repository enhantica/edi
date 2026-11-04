// Saved native metadata binds the scientific comparison independently of row labels and geometry.
import assert from 'node:assert/strict';

export function assertSavedProject(name, fitCase) {
  const names = {lbco:'pd-neut-cwl_lbco-hrpt', ncaf:'pd-neut-tof_ncaf-wish'};
  assert(Object.hasOwn(names, fitCase), 'Saved browser project must have a declared independent reference');
  assert.equal(name, names[fitCase],
    'The actual saved browser project must match the chosen committed native reference');
}

export function assertNativeChi(chi, reference, tolerance) {
  assert(Number.isFinite(chi) && Number.isFinite(reference) &&
    Number.isFinite(tolerance) && tolerance >= 0 && Math.abs(chi-reference) <= tolerance,
    'Browser saved fit must agree with the independent committed native CLI chi square: ' +
    `browser=${chi}, native=${reference}, tolerance=${tolerance}`);
}

// ADR-0092 section7: computed file values use six shortest-decimal significant
// digits, half away from zero. Integer decimal digits avoid binary tie/scale drift.
export function sixSignificantFileValue(value) {
  assert(Number.isFinite(value), 'A file projection requires a finite numeric operand');
  if (value === 0) return value;
  const [mantissa, exponent = '0'] = Math.abs(value).toString().toLowerCase().split('e');
  const [whole, fraction = ''] = mantissa.split('.');
  const digits = (whole + fraction).replace(/^0+/, '');
  if (digits.length <= 6) return value;
  const cut = digits.length - 6;
  let kept = BigInt(digits.slice(0, 6));
  if (digits[6] >= '5') ++kept;
  const shift = Number(exponent) - fraction.length + cut;
  return Number((value < 0 ? '-' : '') + kept.toString() + 'e' + shift);
}

export function assertSavedNativeChi(chi, reference, tolerance) {
  const writtenReference = sixSignificantFileValue(reference);
  assert.equal(chi, sixSignificantFileValue(chi),
    'Saved computed chi must obey its declared six-significant-digit file boundary');
  // The independent CLI quantity is projected, not the tolerance widened.
  // Unrounded wasm/native backend parity remains in test_e04_t11_wasm_fit.py.
  assertNativeChi(chi, writtenReference, tolerance);
  return writtenReference;
}
