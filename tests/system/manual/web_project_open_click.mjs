// SPDX-License-Identifier: BSD-3-Clause
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { waitControlGeometry } from './web_control_geometry.mjs';

const load = 'project.load';
const folder = 'project.load.folder';
const cases = [['routing_initial', 100], ['routing_a', 300], ['routing_b', 600]];
const readControl = `name => {
  try { return window.ediControlGeometry(name); }
  catch (error) {
    if (/^ediControlGeometry: no (?:visible )?item is named /.test(error.message)) return null;
    throw error;
  }
}`;

export async function checkProjectOpenClick({ send, evaluate, frame, output, mode, chooseProject }) {
  const waitForMenuToClose = async () => {
    const deadline = performance.now() + 45000;
    do {
      if (!await evaluate(`(${readControl})(${JSON.stringify(folder)})`)) return;
      await frame();
    } while (performance.now() < deadline);
    assert.fail('The setup Load menu must be closed before measuring a new opening');
  };
  const observations = [];
  for (const [name, delayMs] of cases) {
    const upload = await chooseProject(name);
    await waitForMenuToClose();
    await upload();
    const target = await waitControlGeometry(evaluate, frame, load, { enabled: false, waitInViewport: true });
    const shownAt = performance.now();
    // Observe the real menu from before pointer input so even a brief opening is recorded.
    const baselineOpen = await evaluate(`(() => {
      const read = ${readControl};
      const probe = window.projectOpenClickProbe = { changes: [], baselineOpen: !!read(${JSON.stringify(folder)}) };
      window.addEventListener('pointerdown', event => {
        if (event.isTrusted && event.button === 0) probe.pressedAt = performance.now();
      }, { capture: true, once: true });
      window.addEventListener('pointerup', event => {
        if (event.isTrusted && event.button === 0) probe.releasedAt = performance.now();
      }, { capture: true, once: true });
      let open = probe.baselineOpen;
      const sample = () => {
        if (probe.done) return;
        const item = read(${JSON.stringify(folder)});
        const visible = item?.visible === true && item.width > 0 && item.height > 0;
        if (visible !== open) {
          open = visible;
          probe.changes.push({ open, at: performance.now() });
        }
        probe.open = open;
        probe.project = read('project.name')?.text;
        probe.opening = !!read('statusBar.opening');
        requestAnimationFrame(sample);
      };
      sample();
      return probe.baselineOpen;
    })()`);
    assert.equal(baselineOpen, false, 'The folder chooser must dismiss the setup Load menu before the timed click');

    await delay(Math.max(0, shownAt + delayMs - performance.now()));
    const sentAfterMs = Math.round(performance.now() - shownAt);
    const point = { x: target.x + target.width / 2, y: target.y + target.height / 2 };
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, ...point, button: 'left', clickCount: 1 });
    }
    const immediateWindowEnds = shownAt + sentAfterMs + 1500;
    const deadline = performance.now() + 45000;
    let state;
    do {
      await frame();
      state = await evaluate('window.projectOpenClickProbe');
    } while (performance.now() < deadline &&
      (performance.now() < immediateWindowEnds || state.project !== name || state.opening));
    await evaluate('window.projectOpenClickProbe.done = true');

    const result = { name, delayMs, sentAfterMs, targetEnabled: target.enabled, ...state };
    observations.push(result);
    console.log(`browser ${mode}: early Load click ${JSON.stringify(result)}`);
    await writeFile(join(output, `${mode}-project-open-click.json`), JSON.stringify(observations, null, 2));
    assert.equal(state.project, name, 'The requested project must be displayed after its folder was accepted');
    assert.equal(state.opening, false, 'The menu must be observed through the end of project opening');
    assert(sentAfterMs < 1000, 'The single pointer press must be sent in the first second of control visibility');
    assert(Number.isFinite(state.pressedAt) && state.releasedAt >= state.pressedAt,
      'The page must receive the one trusted pointer press and release');

    if (state.open) {
      for (const type of ['keyDown', 'keyUp']) {
        await send('Input.dispatchKeyEvent', { type, key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
      }
      await waitForMenuToClose();
    }
  }

  assert.deepEqual(observations.map(result => result.changes.map(change => change.open)),
    cases.map(() => [true]), 'Each first-second Load click must open its own menu once and leave it open until dismissed');
  assert(observations.every(result => result.changes[0].at >= result.pressedAt),
    'The menu must first open after the corresponding trusted press');
}
