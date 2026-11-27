// SPDX-License-Identifier: BSD-3-Clause
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { waitControlGeometry } from './web_control_geometry.mjs';

const emptyDescription = 'A project with no data';
const read = `name => {
  try { return window.ediControlGeometry(name); }
  catch (error) {
    if (/^ediControlGeometry: no (?:visible )?item is named /.test(error.message)) return null;
    throw error;
  }
}`;
const loadItem = 'project.load.folder';
const saveItem = 'project.saveAs.zip';
const createField = 'createProject.name';
const createDraft = {
  'createProject.name': 'UnsubmittedProjectDraft',
  'createProject.title': 'Retired project draft title',
  'createProject.authors': 'Retired project draft authors',
  'createProject.description': 'Retired project draft description',
};

export async function checkProjectReplacement({ send, evaluate, frame, output, mode, chooseProject, inputs }) {
  const marker = await readFile(join(inputs, 'routing_b', 'project.edi'), 'utf8');
  const description = marker.match(/^_metadata\.description\s+(".*")$/m);
  assert(description, 'The source project fixture must declare its original description');
  const fullDescription = JSON.parse(description[1]);
  const control = name => evaluate(`(${read})(${JSON.stringify(name)})`);
  const until = async (observe, matches, requirement) => {
    const deadline = performance.now() + 45000;
    do {
      const value = await observe();
      if (matches(value)) return value;
      await frame();
    } while (performance.now() < deadline);
    assert.fail(requirement);
  };
  const closed = name => until(() => control(name), value => value === null,
    'The dismissed setup control must finish closing before the next input');
  const pointer = async item => {
    const point = { x: item.x + item.width / 2, y: item.y + item.height / 2 };
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, ...point, button: 'left', clickCount: 1 });
    }
  };
  const dismiss = async name => {
    if (!await control(name)) return;
    for (const type of ['keyDown', 'keyUp']) {
      await send('Input.dispatchKeyEvent', { type, key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    }
    await closed(name);
  };
  const picked = async (name, fast = false) => {
    const upload = await chooseProject(name, fast ? pointer : null);
    await closed(loadItem);
    return upload;
  };
  const visibleProject = name => until(() => control('project.name'), item => item?.text === name,
    'The selected folder must become the visible Project page');
  const observe = async ({ project, effect, description, empty = false }) => {
    const baseline = await evaluate(`(() => {
      const read = ${read};
      const show = name => !!read(name);
      const effect = ${JSON.stringify(effect)};
      const state = window.projectReplacementProbe = { events: [], mismatches: [] };
      window.addEventListener('pointerdown', event => {
        if (event.isTrusted && event.button === 0) {
          state.down = performance.now();
          state.projectAtPress = read('project.name')?.text;
          state.openingAtPress = show('statusBar.opening');
        }
      }, { capture: true, once: true });
      window.addEventListener('pointerup', event => {
        if (event.isTrusted && event.button === 0) state.up = performance.now();
      }, { capture: true, once: true });
      let visible = show(effect);
      const sample = () => {
        if (state.done) return;
        const current = show(effect);
        if (current !== visible) state.events.push({ visible: current, at: performance.now() });
        visible = state.visible = current;
        state.name = read('project.name')?.text;
        state.opening = show('statusBar.opening');
        if (state.name === ${JSON.stringify(project)}) {
          const shown = read('project.description')?.text;
          if (shown !== ${JSON.stringify(description)} && !state.mismatches.includes('description')) state.mismatches.push('description');
          if (show(${JSON.stringify(createField)}) && !state.mismatches.includes('dialog')) state.mismatches.push('dialog');
          for (const label of ${JSON.stringify(empty ? ['experiment', 'analysis', 'report'] : [])}) {
            const tab = read('appBar.tab.' + label);
            if ((tab?.enabled || tab?.checked) && !state.mismatches.includes(label)) state.mismatches.push(label);
          }
        }
        requestAnimationFrame(sample);
      };
      sample();
      return visible;
    })()`);
    return {
      baseline,
      async finish(project, through) {
        const state = await until(() => evaluate('window.projectReplacementProbe'),
          value => value.name === project && !value.opening && performance.now() >= through,
          'The replacement must finish and expose the selected project after the observation window');
        await evaluate('window.projectReplacementProbe.done = true');
        return state;
      },
    };
  };

  const results = [];
  const record = async (passed, detail) => {
    results.push({ index: results.length + 1, passed, detail });
    await writeFile(join(output, `${mode}-project-replacement.json`), JSON.stringify(results, null, 2));
  };
  const timed = async (project, button, effect, offset, context = {}) => {
    const needsSelectedProject = effect === saveItem;
    if (needsSelectedProject) await visibleProject(project);
    const observation = await observe({ project, effect, description: fullDescription });
    assert.equal(observation.baseline, false, 'The replacement action must start without its popup open');
    const target = await waitControlGeometry(evaluate, frame, button, { enabled: false, waitInViewport: true });
    const shown = performance.now();
    await delay(offset);
    const sent = performance.now();
    await pointer(target);
    const state = await observation.finish(project, sent + 1500);
    assert(sent - shown < 1500 && Number.isFinite(state.down) && state.up >= state.down,
      'The browser must receive the one scheduled trusted click in the early window');
    if (needsSelectedProject) {
      assert.equal(state.projectAtPress, project,
        'The one timed Save As press must act on the selected project');
    }
    await record(state.events.length === 1 && state.events[0].visible &&
      state.events[0].at >= state.down && state.mismatches.length === 0, { offset, ...context, state });
    await dismiss(effect);
  };

  await (await picked('routing_initial'))();
  await timed('routing_initial', 'project.saveAs', saveItem, 165);

  // As soon as the first replacement is visible, start another using the same real pointer and chooser route.
  await (await picked('routing_a'))();
  await visibleProject('routing_a');
  const firstShownAt = performance.now();
  await (await picked('routing_b', true))();
  await timed('routing_b', 'project.load', loadItem, 815, {
    replacementGapMs: Math.round(performance.now() - firstShownAt),
  });

  await (await picked('routing_a'))();
  await timed('routing_a', 'project.saveAs', saveItem, 1270);

  // Deliver the chooser selection, then hold its file read while the old project still accepts input.
  const uploadEmpty = await picked('routing_empty');
  const old = await control('project.description');
  assert.equal(old?.text, fullDescription, 'The previous project must visibly carry a different description');
  assert.equal((await control('appBar.tab.analysis'))?.enabled, true,
    'The old project must actually offer the analysis tab before replacement');
  await evaluate(`(() => {
    const original = File.prototype.arrayBuffer;
    const descriptor = Object.getOwnPropertyDescriptor(File.prototype, 'arrayBuffer');
    File.prototype.arrayBuffer = function() {
      if (this.webkitRelativePath !== 'routing_empty/project.edi') return original.call(this);
      if (descriptor) Object.defineProperty(File.prototype, 'arrayBuffer', descriptor);
      else delete File.prototype.arrayBuffer;
      return new Promise((resolve, reject) => {
        window.releaseReplacementRead = () => original.call(this).then(resolve, reject);
      });
    };
    return true;
  })()`);
  await uploadEmpty();
  await until(() => evaluate('typeof window.releaseReplacementRead === "function"'), Boolean,
    'The chooser must deliver the real replacement file before the old project is clicked');
  let retiring;
  try {
    await pointer(await waitControlGeometry(evaluate, frame, 'project.create'));
    await waitControlGeometry(evaluate, frame, createField);
    for (const [field, text] of Object.entries(createDraft)) {
      await pointer(await waitControlGeometry(evaluate, frame, field));
      for (const type of ['keyDown', 'keyUp']) {
        await send('Input.dispatchKeyEvent', {
          type, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2,
        });
      }
      await send('Input.insertText', { text });
      await until(() => control(field), item => item?.text === text,
        'The old project must hold the entered Create draft before file reading resumes');
    }
    retiring = await observe({ project: 'routing_empty', effect: createField, description: emptyDescription, empty: true });
    assert.equal(retiring.baseline, true, 'The dialog must be visible in the project that owns it');
  } finally {
    await evaluate('window.releaseReplacementRead(); delete window.releaseReplacementRead; true');
  }
  const empty = await retiring.finish('routing_empty', performance.now());
  await record(empty.mismatches.every(mismatch => mismatch === 'dialog'), empty);
  await record(!empty.visible && !empty.mismatches.includes('dialog'), empty);

  await pointer(await waitControlGeometry(evaluate, frame, 'project.create'));
  const reopened = {};
  const stale = [];
  for (const [field, text] of Object.entries(createDraft)) {
    const item = await waitControlGeometry(evaluate, frame, field);
    assert.equal(typeof item.text, 'string', 'Each reopened Create field exposes its actual value');
    reopened[field] = item.text;
    if (item.text.includes(text)) stale.push(field);
  }
  await record(stale.length === 0, { project: 'routing_empty', reopened, stale });
  await dismiss(createField);

  assert(results.every(result => result.passed),
    'Each replacement must retire the previous project UI and preserve the new project’s clicked action exactly once');
}
