// The actual browser download boundary. Inputs are bundled files, checked against
// independent example sources by the companion recipe gate.
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

async function bundled(name, folder = fileURLToPath(new URL('../../../app/', import.meta.url))) {
  const found = [];
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    const path = join(folder, entry.name);
    if (entry.isDirectory()) found.push(...await bundled(name, path));
    else if (entry.isFile() && entry.name === name) found.push(path);
  }
  return found;
}

export async function checkTutorialFileDownloads({ click, event, output, evaluate, send, mode }) {
  const names = ['lbco.cif', 'hrpt.xye'];
  const expected = new Map();
  for (const name of names) {
    const paths = await bundled(name);
    assert.equal(paths.length, 1, `The app bundles exactly one tutorial file named ${name}`);
    expected.set(name, await readFile(paths[0]));
  }
  await send('Network.setBlockedURLs', { urls: ['http://*', 'https://*'] });
  try {
    await click(/^Tutorials$/, 'button');
    await click(/^(?:Start )?Fitting(?:\b|$)/, 'button', 'tutorials.row.fitting');
    const downloads = names.map(name => event('Browser.downloadWillBegin', value => value.suggestedFilename === name)
      .then(async started => {
        await event('Browser.downloadProgress', value => value.guid === started.guid && value.state === 'completed');
        assert.deepEqual(await readFile(join(output, started.guid)), expected.get(name),
          `Save tutorial files downloads the original bundled ${name} bytes`);
        return name;
      }));
    for (const download of downloads) download.catch(() => {});
    await click(/^Save tutorial files$/, 'button');
    assert.deepEqual((await Promise.all(downloads)).sort(), [...names].sort(),
      'One Save tutorial files action downloads both named inputs without a network fetch');
    await click(/^Stop$/, 'button', 'tutorial.stop');
    assert.equal(await evaluate("window.ediControlGeometry('appBar.tab.analysis').enabled"), false,
      'Stopping the from-files tutorial restores the initially project-free browser session');
    await click(/^Home$/, 'tab', 'appBar.tab.home');
  } finally {
    await send('Network.setBlockedURLs', { urls: mode === 'singlethread' ? ['*coi-serviceworker.js*'] : [] });
  }
}
