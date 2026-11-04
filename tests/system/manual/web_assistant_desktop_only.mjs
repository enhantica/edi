// Owner election a518699ea: exercise the packed app's real WASM controls.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {restoreCanvasViewport, waitControlGeometry} from './web_control_geometry.mjs';

export async function checkDesktopOnlyAssistant({send, evaluate, frame, click, output, mode}) {
  const facts = [];
  const read = name => evaluate(`window.ediControlGeometry(${JSON.stringify(name)})`);
  const retain = async (stage, value) => {
    facts.push({stage, value});
    await writeFile(join(output, `${mode}-assistant-platform.json`), JSON.stringify(facts, null, 2));
  };
  const pointer = async item => {
    await restoreCanvasViewport(evaluate);
    for (const type of ['mousePressed', 'mouseReleased'])
      await send('Input.dispatchMouseEvent', {
        type, x:item.x + item.width / 2, y:item.y + item.height / 2,
        button:'left', clickCount:1,
      });
    await frame();
  };
  const messageHidden = () => evaluate(`(() => {
    try {return window.ediControlGeometry('assistant.desktopOnly.message').visible === false;}
    catch(error) {
      if (error.message === "ediControlGeometry: no visible item is named 'assistant.desktopOnly.message'") return true;
      throw error;
    }
  })()`);
  const until = async (predicate, reason) => {
    const deadline = Date.now() + 45000;
    do {
      if (await predicate()) return;
      await frame();
    } while (Date.now() < deadline);
    assert.fail(reason);
  };

  // A disabled AI tab must not become selected through real pointer input.
  await click(/^Application preferences$/, 'button', 'appBar.button.preferences');
  await pointer(await waitControlGeometry(evaluate, frame, 'preferences.tab.prompts'));
  await until(async () => (await read('preferences.tab.prompts')).checked === true,
    'The actual Prompts tab must finish physical selection');
  const tab = await waitControlGeometry(
    evaluate, frame, 'preferences.tab.aiAssistance', {enabled:false});
  await retain('ai-tab-before-click', {tab, ax:await send('Accessibility.getFullAXTree')});
  assert.equal(tab.enabled, false, 'WASM AI preferences are disabled');
  assert.equal(tab.checked, false, 'The disabled AI tab starts outside the selected Prompts page');
  await pointer(tab);
  const after = await read('preferences.tab.aiAssistance');
  const prompts = await read('preferences.tab.prompts');
  await retain('ai-tab-after-click', {after, prompts, ax:await send('Accessibility.getFullAXTree')});
  assert.equal(after.enabled, false, 'Clicking cannot enable the WASM AI tab');
  assert.equal(after.checked, false, 'Clicking a disabled AI tab cannot select it');
  assert.equal(prompts.checked, true, 'The ordinary previously selected preferences page survives');
  await click(/^OK$/, 'button');

  // Exercise both Home and an ordinary empty Project workflow, without a provider.
  for (const context of ['home', 'project']) {
    if (context === 'project') {
      await click(/^Start$/);
      await click(/^Project$/);
    }
    const robot = await waitControlGeometry(evaluate, frame, 'assistant.toggle');
    await retain(context + '-robot-before-click', robot);
    await pointer(robot);
    const message = await waitControlGeometry(evaluate, frame, 'assistant.desktopOnly.message');
    const composer = await evaluate(`(() => {
      try {return window.ediControlGeometry('assistant.composer');}
      catch(error) {
        if (["ediControlGeometry: no visible item is named 'assistant.composer'",
             "ediControlGeometry: no item is named 'assistant.composer'"].includes(error.message))
          return {visible:false, absence:error.message};
        throw error;
      }
    })()`);
    await retain(context + '-desktop-only-popup', {
      message, composer, ax:await send('Accessibility.getFullAXTree'),
    });
    assert.equal(typeof message.text, 'string', 'The real popup exposes its visible message text');
    assert(/desktop/i.test(message.text) && /only|available/i.test(message.text),
      'The visible availability popup explains that the assistant requires the desktop version');
    assert.equal(composer.visible, false, 'The WASM robot does not enter the assistant editor flow');
    for (const type of ['keyDown', 'keyUp'])
      await send('Input.dispatchKeyEvent', {type, key:'Escape', code:'Escape', windowsVirtualKeyCode:27});
    await until(messageHidden, 'The real availability popup must finish its ordinary close transition');
    await retain(context + '-popup-dismissed', {
      robot:await read('assistant.toggle'), hidden:await messageHidden(),
    });
  }
  await click(/^Home$/, 'tab', 'appBar.tab.home');
}
