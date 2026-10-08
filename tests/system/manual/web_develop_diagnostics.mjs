// Gate 7 reads the real QML view through the app bridge, outside Qt popup AX trees.
import assert from 'node:assert/strict';

export async function inspectDevelopDiagnostics(evaluate, frame, mode, record, capture) {
  assert.equal(await evaluate('typeof window.ediDevelopDiagnostics'), 'function',
    'The web app must expose ediDevelopDiagnostics to operate and inspect the real Develop dialog');
  const call = action => evaluate(`window.ediDevelopDiagnostics(${JSON.stringify(action)})`);
  const closed = snapshot => snapshot?.preferencesVisible === false && snapshot?.diagnosticsVisible === false;
  assert(closed(await call('read')), 'Develop inspection must start with both actual Qt dialogs closed');
  try {
    await call('open');
    let snapshot;
    const deadline = Date.now() + 10000;
    do {
      snapshot = await call('read');
      if (snapshot?.preferencesVisible === true && snapshot?.developSelected === true &&
          snapshot?.diagnosticsVisible === true && snapshot?.textVisible === true) break;
      await frame();
    } while (Date.now() < deadline);
    await record(snapshot);
    assert(snapshot?.preferencesVisible === true && snapshot?.developSelected === true &&
      snapshot?.diagnosticsVisible === true && snapshot?.textVisible === true,
      'The real Preferences Develop tab and its displayed diagnostics TextArea must be visible');
    assert(typeof snapshot.text === 'string' && snapshot.text.length > 0 &&
      snapshot.text === snapshot.providerText,
      'The displayed QML diagnostics text must equal the actual ApplicationInfo diagnostics provider');
    const diagnostics = snapshot.text;
    for (const prior of ['Threads (ideal)', 'Threads (OpenMP team)', 'Browser cores (hardwareConcurrency)'])
      assert(diagnostics.includes(prior), 'Develop diagnostics must retain the existing thread and browser lines');
    const backend = diagnostics.match(/(?:parallel|engine) backend:\s*([^\n]+)/i)?.[1];
    const workerCount = Number(diagnostics.match(/(?:parallel|engine) workers:\s*(\d+)/i)?.[1]);
    const simd = diagnostics.match(/(?:WebAssembly |wasm )?SIMD:\s*(yes|no|on|off|enabled|disabled)/i)?.[1];
    assert(backend && Number.isInteger(workerCount) && simd,
      'Develop must show engine backend, actual worker count and SIMD state');
    if (mode === 'singlethread') {
      assert(/serial/i.test(backend) && workerCount === 1 && /^(no|off|disabled)$/i.test(simd),
        'The serial browser route must report its serial scalar engine');
    } else {
      assert(/std.?thread|thread.?pool/i.test(backend) && workerCount > 1 && /^(yes|on|enabled)$/i.test(simd),
        'Both isolated browser routes must report the active thread backend and SIMD');
    }
    await record({...snapshot, backend, workerCount, simd, diagnostics});
    await capture();
  } finally {
    await call('close');
    assert(closed(await call('read')), 'Develop inspection must close both actual Qt dialogs before the scientific workflow');
  }
}
