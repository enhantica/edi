import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(new URL('../../fixtures/web_parallel/package.json', import.meta.url));
const {chromium} = require('playwright-core');
const [origin, output] = process.argv.slice(2);
const root = fileURLToPath(new URL('../../../', import.meta.url));
assert.equal(process.platform, 'win32', 'The clipping acceptance requires a Windows browser');
assert(origin && output && process.env.EDI_BROWSER,
  'The actor needs the delivered site, evidence directory and Windows browser');
await mkdir(output, {recursive: true});
const browser = await chromium.launch({
  executablePath: process.env.EDI_BROWSER,
  headless: false,
  args: ['--use-gl=angle', '--use-angle=d3d11'],
});
const receipts = [];
const errors = [];
try {
  const page = await browser.newPage({viewport: {width: 1280, height: 900}, deviceScaleFactor: 1});
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  const response = await page.request.get(`${origin}/clipping-host.json`);
  assert(response.ok(), 'The delivered artifact contains its clipping-host build identity');
  const build = await response.json();
  assert.equal(build.contract, 1, 'The delivered test host implements the declared observation contract');
  for (const name of ['ediCommit', 'guiComponentsCommit'])
    assert.match(build[name] || '', /^[a-f0-9]{40}$/, 'The host records complete source commit identities');
  const expectedHead = process.env.GITHUB_SHA || execFileSync('git', ['rev-parse', 'HEAD'],
    {cwd: root, encoding: 'utf8'}).trim();
  assert.equal(build.ediCommit, expectedHead, 'The web artifact was built from this exact checked-out head');
  const pin = (await readFile(resolve(root, 'cmake/EdiGuiBase.cmake'), 'utf8'))
    .match(/set\(EDI_GUI_COMPONENTS_SHA\s+([a-f0-9]{40})\)/);
  assert(pin, 'The checked-out app declares its full shared-components pin');
  assert.equal(build.guiComponentsCommit, pin[1], "The fixture uses this head's exact shared-components pin");
  assert.deepEqual(build.kits?.slice().sort(), ['multithread', 'singlethread'],
    'The host identity covers both actual Qt kits');
  assert(build.qt && build.emscripten && build.sources && Object.keys(build.sources).length > 0,
    'The host identity records toolchain versions and fixture source hashes');
  for (const [name, hash] of Object.entries(build.sources)) {
    assert(name.startsWith('tests/fixtures/windows_clipping/') && !name.split('/').includes('..') &&
      !name.includes('\\'), 'The host records only source files inside its committed fixture');
    assert.match(hash, /^[a-f0-9]{64}$/, 'Each fixture source has a complete content hash');
    assert.equal(createHash('sha256').update(await readFile(resolve(root, name))).digest('hex'), hash,
      'The delivered fixture source bytes match the checked-out test source');
  }

  for (const mode of ['singlethread', 'multithread']) {
    await page.goto(`${origin}/?build=${mode}&acceptance=clipping`);
    await page.waitForFunction(() => typeof window.ediControlGeometry === 'function', null,
      {timeout: 120000});
    assert.equal(await page.evaluate(() => window.ediBuild), mode,
      'The browser actually loaded the requested Qt kit without falling back');
    assert.equal(await page.evaluate(() => window.crossOriginIsolated), true,
      'The served site retains the isolation needed by its multithread build');
    assert.equal(await page.evaluate(() => typeof window.ediClippingAcceptance), 'function',
      'The real app build loads the native fixture observer before pixels can count');
    const gpu = await page.evaluate(() => {
      const gl = document.createElement('canvas').getContext('webgl2');
      if (!gl) throw Error('The Windows rendering check requires WebGL2');
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      return {
        vendor: gl.getParameter(ext ? ext.UNMASKED_VENDOR_WEBGL : gl.VENDOR),
        renderer: gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
      };
    });
    assert.match(gpu.renderer, /ANGLE.*Direct3D11|ANGLE.*D3D11/i,
      'The receipt proves the Windows ANGLE D3D11 path actually executed');
    for (const theme of ['light', 'dark']) {
      for (const scenario of ['rows', 'antialiased-border', 'outer-off', 'both-clips', 'layer',
        'cover', 'structure-table', 'experiment-table', 'analysis-table', 'sidebar-collapse', 'popup-close']) {
        const prefix = resolve(output, `${mode}-${theme}-${scenario}`);
        const reference = await page.evaluate(args => window.ediClippingAcceptance(...args),
          [scenario, theme, 'background']);
        const background = await page.screenshot({path: `${prefix}-background.png`});
        const facts = await page.evaluate(args => window.ediClippingAcceptance(...args),
          [scenario, theme, 'prepare']);
        for (const name of ['clip', 'region']) {
          assert(facts?.[name] && ['x', 'y', 'width', 'height'].every(key =>
            Number.isFinite(facts[name][key])) && facts[name].width > 0 && facts[name].height > 0,
          'The pixel mask comes from finite, nonempty native scene geometry');
          assert.deepEqual(facts[name], reference[name],
            'The independent empty reference has the identical geometry');
        }
        const {clip, region, action} = facts;
        if (scenario === 'outer-off' || scenario === 'cover')
          assert.equal(facts.outerClip, false, 'The escape and cover controls actually disable outer clipping');
        if (scenario === 'cover')
          assert.equal(facts.coverVisible, true, 'The opaque-cover control actually draws its independent cover');
        if (scenario === 'both-clips')
          assert(facts.innerClip === true && facts.outerClip === true, 'The nested control actually enables both clips');
        if (scenario === 'layer')
          assert.equal(facts.layerEnabled, true, 'The layer case actually exercises an enabled native layer');
        if (scenario === 'antialiased-border')
          assert.equal(facts.antialiasing, true, 'The border case actually enables native antialiasing');
        assert(region.x <= clip.x && region.y <= clip.y &&
          region.x + region.width >= clip.x + clip.width &&
          region.y + region.height >= clip.y + clip.height,
        'The observed overflow region includes the whole clip and all potential escaped child bounds');
        assert(region.width > clip.width || region.height > clip.height,
          'The mask includes possible escaped pixels outside the clip');
        assert(action && Number.isFinite(action.x) && Number.isFinite(action.y),
          'Each real scenario supplies a trusted input target');
        await page.mouse.move(action.x, action.y);
        const visible = await page.screenshot({path: `${prefix}-visible.png`});
        if (action.kind === 'wheel') {
          assert(Number.isFinite(action.dy) && action.dy !== 0,
            'Scrolling uses a nonzero trusted wheel event');
          await page.mouse.wheel(0, action.dy);
        } else {
          assert.equal(action.kind, 'click', 'Only declared trusted click or wheel actions execute');
          await page.mouse.click(action.x, action.y);
        }
        const state = await page.evaluate(args => window.ediClippingAcceptance(...args),
          [scenario, theme, 'read']);
        assert.equal(state?.completed, true,
          'Native contentY, expanded state or popup visibility proves the real action completed');
        if (scenario.endsWith('-table') || scenario === 'rows')
          assert(facts.contentHeight > clip.height && state.contentY !== facts.contentY,
            'A real populated list actually scrolls beyond its initial content position');
        if (scenario === 'sidebar-collapse')
          assert(facts.expanded === true && state.expanded === false,
            'The actual expanded group changes to its collapsed state');
        if (scenario === 'popup-close')
          assert(facts.popupVisible === true && state.popupVisible === false,
            'The actual visible popup changes to its closed state');
        const after = await page.screenshot({path: `${prefix}-after.png`});
        const pixels = await page.evaluate(async ({background, visible, after, clip, region}) => {
          async function read(encoded) {
            const picture = new Image();
            picture.src = 'data:image/png;base64,' + encoded;
            await picture.decode();
            const canvas = new OffscreenCanvas(picture.width, picture.height);
            const context = canvas.getContext('2d');
            context.drawImage(picture, 0, 0);
            return {width: picture.width, height: picture.height,
              data: context.getImageData(0, 0, picture.width, picture.height).data};
          }
          const reference = await read(background), before = await read(visible), result = await read(after);
          if ([before, result].some(frame => frame.width !== reference.width || frame.height !== reference.height))
            throw Error('All compared screenshots must have identical dimensions');
          if (region.x < 0 || region.y < 0 || region.x + region.width > reference.width ||
              region.y + region.height > reference.height)
            throw Error('The complete overflow mask must fit inside the captured viewport');
          const counts = {visibleInside: 0, visibleOutside: 0, afterInside: 0, afterOutside: 0, changed: 0};
          for (let y = Math.floor(region.y); y < Math.ceil(region.y + region.height); y++) {
            for (let x = Math.floor(region.x); x < Math.ceil(region.x + region.width); x++) {
              const at = 4 * (y * reference.width + x);
              const inside = x >= clip.x && x < clip.x + clip.width && y >= clip.y && y < clip.y + clip.height;
              if ([0, 1, 2, 3].some(c => before.data[at + c] !== reference.data[at + c]))
                counts[inside ? 'visibleInside' : 'visibleOutside']++;
              if ([0, 1, 2, 3].some(c => result.data[at + c] !== reference.data[at + c]))
                counts[inside ? 'afterInside' : 'afterOutside']++;
              if ([0, 1, 2, 3].some(c => result.data[at + c] !== before.data[at + c])) counts.changed++;
            }
          }
          return counts;
        }, {background: background.toString('base64'), visible: visible.toString('base64'),
          after: after.toString('base64'), clip, region});
        assert(pixels.visibleInside > 0 && pixels.changed > 0,
          'Visible content and changed pixels prove that a populated scene received the action');
        if (scenario === 'outer-off') {
          assert(pixels.afterOutside > 0,
            'Disabling outer clipping must reach the outside-pixel escape control');
        } else {
          assert.equal(pixels.visibleOutside, 0, 'The visible clipped scene matches the independent outside background');
          assert.equal(pixels.afterOutside, 0, 'No escaped or stale content survives outside its native clip');
          if (scenario === 'popup-close' || scenario === 'sidebar-collapse')
            assert.equal(pixels.afterInside, 0, 'Vacated content also matches the independent empty background');
        }
        receipts.push({mode, theme, scenario, status: "passed", build, gpu, pixels, geometry: facts, state,
          screenshots: Object.fromEntries(Object.entries({background, visible, after}).map(([key, data]) => [key, createHash("sha256").update(data).digest("hex")]))});
        await writeFile(resolve(output, 'receipt.json'),
          JSON.stringify({browser: await browser.version(), receipts, errors}, null, 2) + '\n');
      }
    }
  }
  await writeFile(resolve(output, "receipt.json"), JSON.stringify({complete: true, platform: process.platform, browser: await browser.version(), receipts, errors}, null, 2) + "\n");
  assert.deepEqual(errors, [], 'A clipping result cannot hide browser or Qt console errors');
} finally {
  await writeFile(resolve(output, 'browser-errors.json'), JSON.stringify(errors, null, 2) + '\n');
  await browser.close();
}
