import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const [chrome, playwright, shippedPage] = process.argv.slice(2);
assert(chrome && playwright, 'Supply the pinned Chrome executable and the Playwright module');
const { chromium } = await import(pathToFileURL(playwright).href);
const pageSource = await readFile(
  shippedPage || new URL('../../../app/web/index.html', import.meta.url), 'utf8');
const base = 'http://localhost:7432';
const folder = 'multithread-a1b2';
const appRequests = new Set([
  `/${folder}/qtloader.js`,
  `/${folder}/edi_app.js`,
  `/${folder}/edi_app.wasm`,
]);

async function routePage(context) {
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    assert.equal(url.origin, base, 'The ownership test is entirely local');
    if (url.pathname === '/') {
      await route.fulfill({
        contentType: 'text/html',
        headers: {
          'Cross-Origin-Opener-Policy': 'same-origin',
          'Cross-Origin-Embedder-Policy': 'require-corp',
        },
        body: pageSource,
      });
    } else if (url.pathname === '/build.json') {
      await route.fulfill({ json: { multithread: folder } });
    } else if (url.pathname.endsWith('/qtloader.js')) {
      await route.fulfill({
        contentType: 'text/javascript',
        body: 'async function qtLoad(config) { await config.qt.module; window.launches++; config.qt.onLoaded(); }',
      });
    } else if (url.pathname.endsWith('/edi_app.wasm')) {
      await route.fulfill({
        contentType: 'application/wasm',
        body: Buffer.from([0, 97, 115, 109, 1, 0, 0, 0]),
      });
    } else {
      await route.fulfill({ status: 200, body: '' });
    }
  });
  await context.addInitScript(() => { window.launches = 0; });
}

const browser = await chromium.launch({ executablePath: chrome, args: ['--no-sandbox'] });
try {
  for (const colorScheme of ['light', 'dark']) {
    const context = await browser.newContext({ colorScheme, serviceWorkers: 'block' });
    await routePage(context);
    try {
      const owner = await context.newPage();
      await owner.goto(base);
      await owner.waitForFunction(() => window.launches === 1, null, { timeout: 5000 });

      const other = await context.newPage();
      const reachedApp = new Set();
      other.on('request', request => {
        const path = new URL(request.url()).pathname;
        if (appRequests.has(path)) reachedApp.add(path);
      });
      await other.goto(base);
      await other.waitForFunction(() => window.launches === 1 ||
        /open in another tab/i.test(document.body.textContent), null, { timeout: 5000 });
      assert.equal(await other.evaluate(() => window.launches), 0,
        'A second tab must never start the app while the first owns it');
      assert.deepEqual([...reachedApp], [], 'The waiting tab fetches no Qt or app module');
      const held = await owner.evaluate(async () => (await navigator.locks.query()).held);
      assert(held.some(lock => lock.name === 'edi-owner' && lock.mode === 'exclusive'),
        'The owning tab retains the exclusive browser lock for its lifetime');

      const retry = other.getByRole('button', { name: 'Try again' });
      await retry.click();
      assert.equal(await other.evaluate(() => window.launches), 0,
        'Retry while the owner lives cannot start a second app');
      await owner.close();
      await retry.click();
      await other.waitForFunction(() => window.launches === 1, null, { timeout: 5000 });
    } finally {
      await context.close();
    }
  }

  const legacy = await browser.newContext({ serviceWorkers: 'block' });
  await routePage(legacy);
  await legacy.addInitScript(() => { Object.defineProperty(navigator, 'locks', { value: undefined }); });
  const tab = await legacy.newPage();
  await tab.goto(base);
  await tab.waitForFunction(() => window.launches === 1, null, { timeout: 5000 });
} finally {
  await browser.close();
}
