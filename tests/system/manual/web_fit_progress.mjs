import assert from 'node:assert/strict';

export function isLiveFitProgress(state) {
  return state?.running === true && state?.visible === true && typeof state?.text === 'string' &&
    /^fitting\s*·\s*it\s+[1-9]\d*$/i.test(state.text);
}

export function advancesLiveFitProgress(states, finalIteration) {
  if (!Array.isArray(states) || !Number.isSafeInteger(finalIteration) || finalIteration < 3) return false;
  let previous = 0;
  let advances = 0;
  for (const state of states) {
    if (!isLiveFitProgress(state)) continue;
    const iteration = Number(state.text.match(/it\s+(\d+)$/i)[1]);
    if (iteration > finalIteration || iteration < previous) return false;
    if (iteration < finalIteration && iteration > previous) ++advances;
    previous = iteration;
  }
  return advances >= 2;
}

function validate(state) {
  assert(state && typeof state.running === 'boolean' && typeof state.visible === 'boolean' &&
    typeof state.text === 'string',
    'The native progress hook must return actual running, effective bar visibility and live text');
}

export async function beginFitProgress(evaluate) {
  assert.equal(await evaluate('typeof window.ediFitProgress'), 'function',
    'The web app must expose ediFitProgress to read the actual native fit and its progress bar');
  const initial = await evaluate('window.ediFitProgress()');
  validate(initial);
  assert.equal(initial.running, false,
    'Native progress sampling must begin before the real fitting action starts');
  await evaluate(`(() => {
    window.__e04NativeProgress = [];
    window.__e04NativeProgressError = null;
    window.__e04NativeProgressActive = true;
    window.__e04NativeProgressDone = (async () => {
      try {
        while (window.__e04NativeProgressActive) {
          const state = await window.ediFitProgress();
          window.__e04NativeProgress.push({...state, sampledAt:performance.now()});
          await new Promise(resolve => requestAnimationFrame(resolve));
        }
      } catch (error) {
        window.__e04NativeProgressError = String(error);
      }
    })();
  })()`);
  return initial;
}

export async function endFitProgress(evaluate) {
  const result = await evaluate(`(async () => {
    window.__e04NativeProgressActive = false;
    await window.__e04NativeProgressDone;
    return {states:window.__e04NativeProgress, error:window.__e04NativeProgressError};
  })()`);
  assert.equal(result.error, null,
    'Every live native progress sample must complete without a page-hook exception');
  assert(Array.isArray(result.states) && result.states.length > 0,
    'The native progress observer must record actual hook samples during the browser workflow');
  for (const state of result.states) validate(state);
  return result.states;
}
