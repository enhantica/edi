// The running control and live status-bar grammar, independent of fit results.
export function fittingObservationKind(value) {
  const record = value !== null && typeof value === 'object' && !Array.isArray(value);
  const text = typeof value === 'string' ? value.trim() : record && typeof value.text === 'string' ? value.text.trim() : '';
  // The new one-word caption needs actual owner/DOM evidence; arbitrary Stop text
  // cannot stand in for the production status action. Legacy grammar is retained.
  if (record) {
    const rects = [value.nativeRect, value.actionRect, value.domRect];
    const finite = rects.every(rect => rect && ['x','y','width','height'].every(key => Number.isFinite(rect[key])) && rect.width > 0 && rect.height > 0);
    // Qt6.11.2 qSaturateRound: signed half bias, int saturation, truncation.
    // The finite guard excludes NaN/infinity before this integer conversion.
    const qtRound = number => Math.trunc(Math.max(-2147483648,
      Math.min(2147483647, number + (number < 0 ? -0.5 : 0.5)))) || 0;
    const same = finite && ['x','y','width','height'].every(key =>
      qtRound(value.nativeRect[key]) === qtRound(value.actionRect[key]) &&
      qtRound(value.nativeRect[key]) === value.domRect[key]);
    return /^(?:stop-circle\s*)?Stop$/i.test(text) && value.control === 'statusBar.fit.button' &&
      value.action === 'statusBar.fit.button.accessibleAction' && value.role === 'button' &&
      value.running === true && value.visible === true && value.enabled === true &&
      value.actionVisible === true && value.actionEnabled === true &&
      value.connected === true && value.domVisible === true && same ? 'control' : null;
  }
  if (/^(?:stop-circle\s*)?(?:stop|cancel) fitting$/i.test(text)) return 'control';
  if (/^fitting\s*·\s*it\s+\d+$/i.test(text)) return 'iteration';
  return null;
}

export function hasRunningProgress(values) {
  return values.some(value => fittingObservationKind(value) === 'control') &&
    values.some(value => fittingObservationKind(value) === 'iteration');
}
