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
