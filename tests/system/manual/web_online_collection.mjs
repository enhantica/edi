// Run against the packed app: node <driver> <site> <mode> <output> <chrome>.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {resolve, join, extname, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {controlPointer, waitControlGeometry, restoreCanvasViewport} from './web_control_geometry.mjs';

const [site, mode, output, chrome] = process.argv.slice(2);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const fixture = join(root, 'tests/fixtures/online_sources/easydiffraction');
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
await mkdir(output, {recursive:true});
const receipts = [];
const headers = mode === 'multithread' ? {'Cross-Origin-Opener-Policy':'same-origin',
  'Cross-Origin-Embedder-Policy':'require-corp'} : {};
const server = createServer(async (req,res) => {
  try {
    const path = new URL(req.url, 'http://localhost').pathname;
    const file = resolve(site, '.' + (path === '/' ? '/index.html' : path));
    assert(file.startsWith(resolve(site) + '/'), 'The fixture server serves only the packed app');
    const data = await readFile(file);
    res.writeHead(200, {...headers, 'Content-Type': ({'.html':'text/html', '.js':'text/javascript',
      '.json':'application/json', '.wasm':'application/wasm'})[extname(file)] || 'application/octet-stream'});
    res.end(data);
  } catch {res.writeHead(404); res.end();}
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({executablePath:chrome, headless:true,
  args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
let page;
try {
  const context = await browser.newContext({viewport:{width:1280,height:768}, serviceWorkers:'block'});
  await context.addInitScript(() => {
    for (const name of ['showDirectoryPicker','showOpenFilePicker'])
      Object.defineProperty(window, name, {value:undefined, configurable:true});
  });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    if (url.pathname.endsWith('/index.json')) {
      receipts.push({path:url.pathname, kind:'index'});
      return route.fulfill({status:200, contentType:'application/json',
        headers:{'Access-Control-Allow-Origin':'*'}, body:await readFile(join(fixture,'index.json'))});
    }
    if (url.pathname.endsWith('/structures/lbco.cif')) {
      receipts.push({path:url.pathname, kind:'file'});
      return route.fulfill({status:200, headers:{'Access-Control-Allow-Origin':'*'},
        body:await readFile(join(fixture,'structures/lbco.cif'))});
    }
    return route.abort();
  });
  page = await context.newPage();
  page.on('console', message => console.log('wasm:', message.text()));
  page.on('pageerror', error => console.log('wasm page error:', error.message));
  await page.goto(origin + '/?build=' + mode);
  await page.waitForFunction(() => typeof window.ediControlGeometry === 'function', null, {timeout:90000});
  const evaluate = text => page.evaluate(text);
  const frame = () => page.evaluate(() => new Promise(ok => requestAnimationFrame(ok)));
  const cdp = await context.newCDPSession(page);
  await cdp.send('Accessibility.enable');
  const activationTree = await cdp.send('Accessibility.getFullAXTree');
  const activation = activationTree.nodes.find(node => node.role?.value === 'button' &&
    /(?:activate|enable) screen reader/i.test(node.name?.value || ''));
  assert(activation?.backendDOMNodeId, 'Qt must expose its documented accessibility activation button');
  const activationNode = await cdp.send('DOM.resolveNode', {backendNodeId:activation.backendDOMNodeId});
  await cdp.send('Runtime.callFunctionOn', {objectId:activationNode.object.objectId,
    functionDeclaration:'function() { this.click(); }'});
  const click = async name => {
    console.log("collection HTTP: click", name);
    await restoreCanvasViewport(evaluate);
    let point;
    if (name.startsWith('group.')) {
      const label = name === 'group.examples' ? /Examples$/ : /Structures$/;
      const {nodes} = await cdp.send('Accessibility.getFullAXTree');
      const header = nodes.find(node => !node.ignored && node.role?.value === 'button' && label.test(node.name?.value || ''));
      assert(header?.backendDOMNodeId, 'A real group header must exist before expanding the collection UI');
      const {model} = await cdp.send('DOM.getBoxModel', {backendNodeId:header.backendDOMNodeId});
      const rect = await evaluate(`window.ediControlGeometry(${JSON.stringify(name)})`);
      point = {x:rect.x + Math.min(rect.width,model.width)/2,
        y:rect.y + Math.min(rect.height,model.height)/2};
      assert(rect.visible && rect.enabled && Number.isFinite(point.x) && Number.isFinite(point.y) &&
        point.x >= 0 && point.x < 1280 && point.y >= 0 && point.y < 768,
        'The group header pointer must lie inside the actual browser viewport');
    } else {
      await waitControlGeometry(evaluate, frame, name);
      point = await controlPointer(evaluate, name);
    }
    await page.mouse.click(point.x, point.y);
    await frame();
  };
  await click('home.start');
  await click('appBar.tab.project');
  const chooser = page.waitForEvent('filechooser', {timeout:10000});
  await click('project.open');
  await click('open.zip');
  let previous, stable = 0;
  const deadline = Date.now() + 10000;
  while (stable < 2 && Date.now() < deadline) {
    await frame();
    const current = (await cdp.send('Page.captureScreenshot', {format:'png'})).data;
    stable = current === previous ? stable + 1 : 0;
    previous = current;
  }
  assert(stable >= 2, 'The real open-project dialog must finish its entry transition before default Enter');
  await page.keyboard.press('Enter');
  await (await chooser).setFiles(join(root,
    'tests/fixtures/project_archive/sc-neut-cwl_tb2ti2o7-heidi_basic.zip'));
  await click('appBar.tab.structure');
  const structureControls = await evaluate(`(() => {try {
    return window.ediControlGeometry('structures.load').visible;
  } catch {return false;}})()`);
  if (!structureControls) await click('group.structures');
  await click('structures.load');
  await click('structures.load.web');
  await click('onlineLoad.source');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await click('onlineLoad.field.id');
  await page.keyboard.type('lbco');
  const before = receipts.filter(r => r.kind === 'index').length;
  await click('onlineLoad.search');
  await waitControlGeometry(evaluate, frame, 'onlineLoad.load.0');
  assert(receipts.filter(r => r.kind === 'index').length > before,
    'The actual WebAssembly search must fetch the shared index over HTTP');
  const id = await evaluate("window.ediControlGeometry('onlineLoad.id.0')");
  assert.equal(id.text, 'lbco', 'The WebAssembly result must identify the independent fixture entry');
  await click('onlineLoad.load.0');
  await page.waitForFunction(() => {
    try {return !window.ediControlGeometry('onlineLoad.load.0').visible;}
    catch (error) {
      if (/no visible item|no item is named/.test(error.message)) return true;
      throw error;
    }
  }, null, {timeout:10000});
  await waitControlGeometry(evaluate, frame, 'structures.load');
  assert(receipts.some(r => r.kind === 'file'), 'The WebAssembly loader must fetch the selected CIF over HTTP');
  await page.screenshot({path:join(output,'loaded.png')});
  await writeFile(join(output,'http-receipts.json'), JSON.stringify(receipts,null,2));
} finally {
  await writeFile(join(output,'http-receipts.json'), JSON.stringify(receipts,null,2));
  if (page && !page.isClosed()) {
    try {
      await page.screenshot({path:join(output,'final.png')});
      const state = await page.evaluate(() => Object.fromEntries(
        ['onlineLoad.message','onlineLoad.load.0','onlineLoad.id.0','structures.load'].map(name => {
          try {return [name, window.ediControlGeometry(name)];}
          catch (error) {return [name, {error:error.message}];}
        })));
      await writeFile(join(output,'final-state.json'), JSON.stringify(state,null,2));
    } catch (error) {console.warn('Browser diagnostic capture failed:', error.message);}
  }
  await browser.close();
  await new Promise(ok => server.close(ok));
}
