// The running control and live status-bar grammar, independent of fit results.
export function fittingObservationKind(value) {
  const text = typeof value === 'string' ? value.trim() : '';
  if (/^(?:stop-circle\s*)?(?:stop|cancel) fitting$/i.test(text)) return 'control';
  if (/^fitting\s*·\s*it\s+\d+$/i.test(text)) return 'iteration';
  return null;
}

export function hasRunningProgress(values) {
  return values.some(value => fittingObservationKind(value) === 'control') &&
    values.some(value => fittingObservationKind(value) === 'iteration');
}
