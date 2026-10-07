// independent browser acceptance. Run separately for each shipped thread mode.
// node tests/system/manual/e04_t11_browser.mjs <site-dir> <singlethread|multithread|shim> <output-dir> [chrome]
// No delay is a readiness predicate: CDP events, animation frames, AX state and completed downloads are.
import { spawn, spawnSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { resolve, extname, join, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { inflateSync } from 'node:zlib';
import { fittingObservationKind, hasRunningProgress } from '../../fixtures/e04_t11_wasm/browser_observations.mjs';

const [siteArg, mode, outputArg, chromeArg] = process.argv.slice(2);
const fileRequestsOnly = process.argv.includes('--file-requests-only');
const fileRequestCase = process.argv.find(arg => arg.startsWith('--file-request-case='))?.split('=')[1] || 'all';
assert(['all','none','overlap','replacement','cancel-structure','cancel-experiment','load-data'].includes(fileRequestCase),
  'each scoped request case must be declared explicitly');
const reopenControl = process.argv.find(arg => arg.startsWith('--reopen-control='))?.split('=')[1];
assert(!fileRequestsOnly || !reopenControl, 'request-only checks cannot impersonate a reopen control');
assert(!reopenControl || ['noop', 'refuse'].includes(reopenControl),
  'reopen counterfactual must be the explicit no-op or refused-open case');
console.log(`browser ${mode}: starting`);
assert(siteArg && outputArg && ['singlethread', 'multithread', 'shim'].includes(mode),
  'requires the produced site, an explicit thread case and a persistent output directory');
const site = resolve(siteArg), output = resolve(outputArg);
await readFile(join(site, 'index.html')); // A missing product fails before the browser is launched.
await mkdir(output, { recursive: true });
const scratch = await mkdtemp(join(tmpdir(), 'e04-browser-'));
const chrome = chromeArg || process.env.CHROME_HEADLESS_SHELL;
assert(chrome, 'CHROME_HEADLESS_SHELL must identify the pinned headless Chrome executable');
const headers = mode === 'multithread' ? {
  'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp',
} : {};
const mime = { '.wasm': 'application/wasm', '.js': 'text/javascript', '.html': 'text/html',
  '.json': 'application/json', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  try {
    if (mode === 'singlethread' && req.url.includes('coi-serviceworker.js')) {
      res.writeHead(404); res.end(); return;
    }
    const rawPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const pathname = rawPath.startsWith('/webapp/') ? rawPath.slice('/webapp'.length) : rawPath;
    const path = resolve(site, '.' + pathname + (pathname.endsWith('/') ? 'index.html' : ''));
    assert(path.startsWith(site + sep), 'browser server must stay inside the published site');
    const bytes = await readFile(path);
    res.writeHead(200, { ...headers, 'Content-Type': mime[extname(path)] || 'application/octet-stream' });
    res.end(bytes);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;
const child = spawn(chrome, ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  '--disable-blink-features=FileSystemAccessLocal', '--window-size=1280,768', '--remote-debugging-port=0', `--user-data-dir=${scratch}`, 'about:blank'],
{ stdio: ['ignore', 'ignore', 'pipe'] });
let ws, send;
const transcript = [], network = [], errors = [];
try {
  const endpoint = await new Promise((ok, fail) => {
    let stderr = '';
    const timer = setTimeout(() => fail(Error('Chrome did not publish its CDP endpoint')), 10000);
    child.once('error', fail);
    child.once('exit', code => fail(Error(`Chrome exited early: ${code}`)));
    child.stderr.on('data', bytes => {
      stderr += bytes;
      const found = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (found) { clearTimeout(timer); ok(found[1]); }
    });
  });
  ws = new WebSocket(endpoint);
  await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail; });
  let id = 0, session;
  const pending = new Map(), listeners = new Map(), lastEvents = new Map();
  ws.onmessage = message => {
    const item = JSON.parse(message.data);
    if (item.id) {
      const waiter = pending.get(item.id);
      if (!waiter) return;
      pending.delete(item.id); clearTimeout(waiter.timer);
      item.error ? waiter.fail(Error(JSON.stringify(item.error))) : waiter.ok(item.result);
    } else {
      lastEvents.set(item.method, item.params);
      for (const fn of listeners.get(item.method) || []) fn(item.params);
      if (item.method === 'Network.requestWillBeSent') network.push(item.params.request.url);
      if (item.method === 'Runtime.exceptionThrown') errors.push(item.params.exceptionDetails);
      if (item.method === 'Runtime.consoleAPICalled') transcript.push(item.params.args.map(a => a.value ?? a.description));
    }
  };
  send = (method, params = {}, browser = false) => new Promise((ok, fail) => {
    const number = ++id;
    const timer = setTimeout(() => { pending.delete(number); fail(Error(`CDP deadline: ${method}`)); }, 45000);
    pending.set(number, { ok, fail, timer });
    ws.send(JSON.stringify({ id: number, method, params, ...(!browser && session ? { sessionId: session } : {}) }));
  });
  const event = (name, predicate = () => true) => new Promise((ok, fail) => {
    const current = lastEvents.get(name);
    if (current && predicate(current)) { ok(current); return; }
    const functions = listeners.get(name) || new Set(); listeners.set(name, functions);
    const timer = setTimeout(() => { functions.delete(onEvent); fail(Error(`event deadline: ${name}`)); }, 45000);
    const onEvent = value => { if (predicate(value)) { clearTimeout(timer); functions.delete(onEvent); ok(value); } };
    functions.add(onEvent);
  });
  const created = await send('Target.createTarget', { url: 'about:blank' }, true);
  session = (await send('Target.attachToTarget', { targetId: created.targetId, flatten: true }, true)).sessionId;
  for (const method of ['Page.enable', 'Runtime.enable', 'Network.enable', 'Accessibility.enable']) await send(method);
  await send('Browser.setDownloadBehavior', { behavior: 'allowAndName', downloadPath: output, eventsEnabled: true }, true);
  await send('Page.setInterceptFileChooserDialog', { enabled: true });
  if (mode === 'singlethread') await send('Network.setBlockedURLs', { urls: ['*coi-serviceworker.js*'] });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    assert(!result.exceptionDetails, 'page evaluation must execute without a browser exception');
    return result.result.value;
  };
  const frame = async () => {
    try { return await evaluate('new Promise(resolve => requestAnimationFrame(() => resolve(true)))'); }
    catch (error) {
      if (!/navigated|context was destroyed|Cannot find context/.test(error.message)) throw error;
      return false; // A service-worker reload is an observable navigation, not a readiness failure.
    }
  };
  const waitAX = async (regex, enabled = true, role) => {
    const deadline = Date.now() + 45000;
    do {
      const tree = await send('Accessibility.getFullAXTree');
      const matches = tree.nodes.filter(n => !n.ignored && (!role || n.role?.value === role) && regex.test(n.name?.value || '') &&
        (!enabled || !(n.properties || []).some(p => p.name === 'disabled' && p.value.value)));
      for (const found of matches) {
        if (!found.backendDOMNodeId) continue;
        try {
          const model = await send('DOM.getBoxModel', {backendNodeId:found.backendDOMNodeId});
          const q = model.model.content;
          const rawX = (q[0]+q[2]+q[4]+q[6])/4;
          const x = ((rawX % 1280) + 1280) % 1280, y = (q[1]+q[3]+q[5]+q[7])/4;
          if (model.model.width > 0 && model.model.height > 0 && x >= 0 && x < 1280 && y >= 0 && y < 768) return found;
        } catch (error) {
          if (!/Could not|No node|not found|does not belong|Cannot find/.test(error.message)) throw error;
        }
      }
      await frame();
    } while (Date.now() < deadline);
    throw Error(`UI never exposed an enabled accessible control/state matching ${regex}`);
  };
  const settleRenderedPage = async () => {
    const deadline = Date.now() + 15000;
    let previous, stable = 0;
    do {
      await frame();
      const current = (await send('Page.captureScreenshot', {format:'png'})).data;
      stable = current === previous ? stable + 1 : 0;
      previous = current;
      if (stable >= 2) return;
    } while (Date.now() < deadline);
    throw Error('page navigation must finish rendering before the next pointer action');
  };
  const click = async (regex, role) => {
    const node = await waitAX(regex, true, role);
    console.log(`browser ${mode}: click ${node.name?.value}`);
    assert(node.backendDOMNodeId, 'UI actions require a real browser-backed accessible control');
    const model = await send('DOM.getBoxModel', { backendNodeId: node.backendDOMNodeId });
    const q = model.model.content;
    const rawX = (q[0]+q[2]+q[4]+q[6])/4;
    const x = ((rawX % 1280) + 1280) % 1280, y = (q[1]+q[3]+q[5]+q[7])/4;
    console.log(`browser ${mode}: pointer ${x},${y}`);
    for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent',
      {type,x,y,button:'left',clickCount:1});
    await frame();
    if (/^(?:Home|Project|Structure|Experiment|Analysis|Start)$/.test(node.name?.value || '') || /(?:Examples|Get started)$/.test(node.name?.value || '')) await settleRenderedPage();
    if (node.role?.value === 'tab' && /^(?:Home|Project|Structure|Experiment|Analysis|Report)$/.test(node.name?.value || '')) {
      const deadline=Date.now()+45000;
      let selected=false;
      do {
        const tree=await send('Accessibility.getFullAXTree');
        selected=tree.nodes.some(n=>!n.ignored && n.role?.value==='tab' &&
          n.name?.value===node.name.value && (n.properties || []).some(p=>p.name==='selected' && p.value.value));
        if (!selected) await frame();
      } while (!selected && Date.now()<deadline);
      assert(selected,'page navigation must select the requested tab, not reuse labels from a hidden page');
    }

  };
  const modalIsDrawn = async () => {
    const data = Buffer.from((await send('Page.captureScreenshot', {format:'png'})).data, 'base64');
    const width = data.readUInt32BE(16), height = data.readUInt32BE(20);
    const channels = data[25] === 2 ? 3 : data[25] === 6 ? 4 : 0;
    assert(channels && data[24] === 8 && data[28] === 0,
      'modal inspection requires real non-interlaced RGB/RGBA browser pixels');
    const compressed = [];
    for (let offset = 8; offset < data.length;) {
      const size = data.readUInt32BE(offset);
      if (data.toString('ascii',offset+4,offset+8) === 'IDAT') compressed.push(data.subarray(offset+8,offset+8+size));
      offset += size + 12;
    }
    const raw = inflateSync(Buffer.concat(compressed)), stride = width * channels;
    assert.equal(raw.length, (stride+1)*height, 'screenshot rows must be complete');
    let previous = Buffer.alloc(stride);
    const samples = [];
    for (let y = 0; y <= Math.round(height*.74); ++y) {
      const filter = raw[y*(stride+1)], row = Buffer.alloc(stride);
      assert(filter <= 4, 'browser PNG row filters must be supported');
      for (let x = 0; x < stride; ++x) {
        const a = x >= channels ? row[x-channels] : 0, b = previous[x], c = x >= channels ? previous[x-channels] : 0;
        const p = a+b-c, pa = Math.abs(p-a), pb = Math.abs(p-b), pc = Math.abs(p-c);
        const predictor = filter === 0 ? 0 : filter === 1 ? a : filter === 2 ? b : filter === 3 ? Math.floor((a+b)/2) : pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
        row[x] = (raw[y*(stride+1)+x+1] + predictor) & 255;
      }
      if ([Math.round(height*.25),Math.round(height*.74)].includes(y)) {
        for (const fraction of [.28,.5,.72]) {
          const x = Math.round(width*fraction)*channels;
          samples.push([...row.subarray(x,x+3)]);
        }
      }
      previous = row;
    }
    // gui-components v0.9.1 Colors.qml: dialogBackground = contentBackground = #f4f4f4 in the light theme.
    // A broad opaque modal covers both the white plotting canvas and sidebar; the ordinary chart cannot satisfy this.
    return samples.length === 6 && samples.every(rgb => rgb.every(value => Math.abs(value-244) <= 2));
  };
  const waitModal = async shown => {
    const deadline = Date.now()+45000;
    do { if (await modalIsDrawn() === shown) return; await frame(); } while (Date.now()<deadline);
    throw Error(`rendered results modal must be ${shown ? 'visible' : 'closed'}`);
  };
  const shot = async name => {
    await frame();
    const png = await send('Page.captureScreenshot', { format: 'png' });
    await writeFile(join(output, `${mode}-${name}.png`), Buffer.from(png.data, 'base64'));
  };
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `
    window.__e04FolderCompleted = [];
    let pickerSequence = 0;
    const nativeListen = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
      if (this instanceof HTMLInputElement && this.type === 'file' && this.id === 'edi-open-folder' && type === 'change') {
        const original = listener;
        listener = async function(event) {
          try { await original.call(this,event); }
          finally { window.__e04FolderCompleted.push(this.__e04Picker); }
        };
      }
      return nativeListen.call(this,type,listener,options);
    };
    const nativeInputClick = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function() {
      if (this.type === 'file') { this.__e04Picker = ++pickerSequence; window.__e04FileInput = this; }
      return nativeInputClick.call(this);
    };
    const nativeFocus = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function(options) {
      nativeFocus.call(this, { ...options, preventScroll: true });
    };
  ` });
  await send('Page.navigate', { url: origin + '/webapp/' });
  let ready = false;
  const readyDeadline = Date.now() + 90000;
  while (!ready && Date.now() < readyDeadline) {
    try {
      ready = await evaluate(`(() => {
        const roots = [document];
        for (let i = 0; i < roots.length; ++i) {
          for (const element of roots[i].querySelectorAll('*')) {
            if (element.shadowRoot) roots.push(element.shadowRoot);
            if (element.tagName === 'CANVAS' && element.width > 100 && element.height > 100 &&
                element.getBoundingClientRect().width > 100 &&
                document.getElementById('screen')?.style.display === 'block') return true;
          }
        }
        return false;
      })()`);
      if (!ready) await frame();
    } catch (error) {
      if (!/navigated|context was destroyed|Cannot find context/.test(error.message)) throw error;
    }
  }
  assert(ready, 'Qt must initialize and expose a rendered application canvas');
  await shot('startup');

  assert.equal(await evaluate('typeof self.showOpenFilePicker'), 'undefined',
    'this browser case exercises the real zip-download fallback without native filesystem pickers');
  const isolated = await evaluate('self.crossOriginIsolated');
  assert.equal(isolated, mode !== 'singlethread', 'the browser itself must prove the selected isolation case');
  const wasm = network.filter(url => url.endsWith('.wasm'));
  const expected = mode === 'singlethread' ? 'singlethread' : 'multithread';
  assert(wasm.length && wasm.some(url => url.replace(/[-_]/g, '').includes(expected)),
    'automatic start-page selection must load the thread kit the browser can actually run');
  assert(!wasm.some(url => url.replace(/[-_]/g, '').includes(mode === 'singlethread' ? 'multithread' : 'singlethread')),
    'automatic selection must not launch an incompatible second kit');
  await writeFile(join(output, `${mode}-startup.json`), JSON.stringify({ isolated, wasm, errors, transcript }, null, 2));
  assert.equal(errors.length, 0, 'startup must have no uncaught browser exception');
  if (process.argv.includes('--startup-only')) {
    console.log(`${mode}: real canvas, browser isolation and automatic kit selection passed`);
  } else {
  // Qt's documented native activation control populates its browser accessibility shadow tree.
  const activationTree = await send('Accessibility.getFullAXTree');
  const activation = activationTree.nodes.find(n => /(?:activate|enable) screen reader/i.test(n.name?.value || '') && n.role?.value === 'button');
  assert(activation?.backendDOMNodeId, 'Qt exposes its real screen-reader activation button');
  const node = await send('DOM.resolveNode', { backendNodeId: activation.backendDOMNodeId });
  await send('Runtime.callFunctionOn', { objectId: node.object.objectId,
    functionDeclaration: 'function() { this.click(); }' });
  await waitAX(/Get started|Home/);
  await shot('home');
  await click(/^Start$/);
  await click(/^Project$/);
  const beforeExample=await send('Accessibility.getFullAXTree');
  assert(beforeExample.nodes.some(n=> !n.ignored && n.role?.value==='tab' && n.name?.value==='Analysis' &&
    (n.properties || []).some(p=>p.name==='disabled' && p.value.value)),
    'example opening must start without a live project or enabled Analysis tab');
  await click(/Examples$/, 'button');
  await click(/lbco.*hrpt.*(?:start[- ]?)?4/i, 'button');
  await waitAX(/^Analysis$/,true,'tab');
  await waitAX(/^Save project as/, true, 'button');
  await click(/^Structure$/); await waitAX(/Cell|Space group/i); await shot('structure');
  await click(/^Experiment$/); await waitAX(/HRPT|Measured/i); await shot('pattern');
  const saveArchive = async () => {
    // A completed event from the first save cannot satisfy the second save.
    lastEvents.delete('Browser.downloadProgress');
    const download = event('Browser.downloadProgress', item => item.state === 'completed');
    await click(/^Save project as/);
    return join(output, (await download).guid);
  };
  const inspectArchive = archive => {
    const result = spawnSync('python', ['-c', `import hashlib, json, pathlib, re, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    files = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
roots = [name[:-len('project.edi')] for name in files if name.endswith('/project.edi')]
if len(roots) != 1:
    raise SystemExit('saved zip must contain one project root')
root = roots[0]
project = files[root + 'project.edi'].decode()
name = re.search(r'^_metadata.name\\s+(.+)$', project, re.M).group(1)
analysis = files[root + 'analysis/analysis.edi'].decode()
# Prior saved-tree invariant: normalize only the named wall-clock field, keep every other byte.
pattern = r'(?m)^(_metadata\\.last_modified[ \\t]+).+$'
if len(re.findall(pattern, project)) != 1:
    raise SystemExit('saved project needs exactly one last-modified field')
files[root + 'project.edi'] = re.sub(pattern, r'\\1<NORMALIZED-WALL-CLOCK>', project).encode()
scientific = {name[len(root):]: hashlib.sha256(data).hexdigest() for name, data in files.items()
              if name.startswith(root)}
print(json.dumps(dict(name=name, analysis=analysis, scientific=scientific)))`, archive],
      {encoding:'utf8',timeout:10000});
    assert.equal(result.status, 0, 'each browser save must produce a readable scientific project archive');
    return JSON.parse(result.stdout);
  };
  if (!fileRequestsOnly) {
  await click(/^Analysis$/);
  await waitModal(false);
  await evaluate(`(() => {
    window.__e04Progress = [];
    const progressKind = (${fittingObservationKind.toString()});
    const roots = [document];
    for (let i=0;i<roots.length;++i) for (const element of roots[i].querySelectorAll('*')) if (element.shadowRoot) roots.push(element.shadowRoot);
    const observer = new MutationObserver(records => {
      for (const record of records) {
        const values = [record.oldValue,record.target.getAttribute?.('aria-label'),record.target.textContent];
        for (const node of record.addedNodes || []) {
          values.push(node.getAttribute?.('aria-label'), node.textContent);
          for (const child of node.querySelectorAll?.('[aria-label]') || []) values.push(child.getAttribute('aria-label'));
        }
        for (const value of values) if (progressKind(value)) window.__e04Progress.push(value);
      }
    });
    for (const root of roots) observer.observe(root,{subtree:true,attributes:true,attributeOldValue:true,characterData:true,characterDataOldValue:true,childList:true});
    window.__e04ProgressObserver = observer;
  })()`);
  await click(/^Start fitting$/);

  await waitAX(/^Success$/); await waitModal(true); await shot('fit-results');
  const progress = await evaluate('window.__e04Progress');
  // Before: "Fit iterationsN". Now: "fitting · it N", with an optional
  // stop-circle prefix on the real Stop control's accessibility label.
  await writeFile(join(output, `${mode}-progress.json`), JSON.stringify(progress,null,2));
  assert(hasRunningProgress(['stop-circle Stop fitting', 'fitting · it 2']),
    'the current running control and live iteration label must satisfy the progress oracle');
  assert(!hasRunningProgress(['Maximum iterations 400','Success','Iterations', 'it 20 · 2 s']),
    'completed report text and minimizer settings cannot impersonate live fitting progress');
  assert(!hasRunningProgress(['Stop fitting', 'Success', 'Iterations 20']),
    'a running control alone cannot impersonate a live iteration indicator');
  assert(!hasRunningProgress(['Start fitting', 'fitting · it 2']),
    'an iteration label alone cannot impersonate a running control');
  if (mode !== 'singlethread') assert(hasRunningProgress(progress),
    'multithread fitting must publish both a running control and a live iteration indicator');
  await evaluate('window.__e04ProgressObserver.disconnect()');
  const fitAX = await send('Accessibility.getFullAXTree');
  await writeFile(join(output, `${mode}-fit-accessibility.json`), JSON.stringify(fitAX, null, 2));
  // The results popup, browser download and reopening all cross the real UI boundary.
  for (const type of ['keyDown','keyUp']) await send('Input.dispatchKeyEvent', {type,key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await waitModal(false);
  await click(/^Project$/);
  await click(/Get started$/, 'button');
  const saved = await saveArchive();
  const before = inspectArchive(saved);
  const nativeOracle = JSON.parse(await readFile(new URL('../../fixtures/e04_t11_wasm/native.json', import.meta.url)));
  assert(/_fit_result.success\s+true/.test(before.analysis) &&
    /_fit_result.iterations\s+[1-9]\d*/.test(before.analysis),
    'the saved project must contain a successful performed fit, not only the unfitted example');
  const chi = Number(before.analysis.match(/^_fit_result.reduced_chi_square\s+(\S+)/m)?.[1]);
  assert(Number.isFinite(chi) && Math.abs(chi-nativeOracle.reduced_chi_square) <=
    nativeOracle.absolute_tolerance + nativeOracle.relative_tolerance*Math.abs(nativeOracle.reduced_chi_square),
    'browser saved fit must agree with the independent committed native CLI chi square');

  // The public reset toolbar action closes the model. Identify its actual browser rectangle,
  // not a stale offscreen page control: the documented four left toolbar buttons end with Reset.
  const tree = await send('Accessibility.getFullAXTree');
  const toolbar = [];
  for (const item of tree.nodes.filter(n => !n.ignored && n.role?.value === 'button' && !n.name?.value && n.backendDOMNodeId)) {
    const {model} = await send('DOM.getBoxModel', {backendNodeId:item.backendDOMNodeId});
    const q = model.content, x=(q[0]+q[2]+q[4]+q[6])/4, y=(q[1]+q[3]+q[5]+q[7])/4;
    if (x>0 && x<200 && y>0 && y<70) toolbar.push({x,y});
  }
  toolbar.sort((a,b) => a.x-b.x);
  assert.equal(toolbar.length,4,'reset must address the real four-button left app toolbar');
  for (const type of ['mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent',
    {type,...toolbar[3],button:'left',clickCount:1});
  await settleRenderedPage();
  await click(/^Start$/); await click(/^Project$/);
  await waitAX(/^Save project as/, false, 'button');
  const emptyTree = await send('Accessibility.getFullAXTree');
  const disabled = regex => emptyTree.nodes.some(n => !n.ignored && regex.test(n.name?.value || '') &&
    (n.properties || []).some(p => p.name==='disabled' && p.value.value));
  assert(disabled(/^Structure$/) && disabled(/^Experiment$/) && disabled(/^Analysis$/),
    'before reopening, reset must remove the old live project and disable its fitting/save actions');
  await shot('empty-before-reopen');
  lastEvents.delete('Page.fileChooserOpened');
  const chooser = event('Page.fileChooserOpened');
  await click(/^Open an existing project/);
  const opened = await chooser;
  await writeFile(join(output, `${mode}-reopen-picker.json`), JSON.stringify(opened,null,2));
  const picked = await send('Runtime.evaluate', {expression:'window.__e04FileInput'});
  const picker = {objectId:picked.result.objectId};
  assert(picker.objectId, 'reopen must use the actual browser file input that opened the chooser');
  const reopened = join(output, 'saved-project');
  const unpack = spawnSync('python', ['-c', `import pathlib, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    archive.extractall(sys.argv[2])
markers = list(pathlib.Path(sys.argv[2]).rglob('project.edi'))
if len(markers) != 1:
    raise SystemExit('saved zip must contain one project root')
if sys.argv[3] == 'refuse':
    markers[0].write_text('_edi.schema_version invalid\\n')
print(markers[0].parent)`, saved, reopened, reopenControl || 'normal'], { encoding: 'utf8', timeout: 10000 });
  assert.equal(unpack.status, 0, 'browser save must produce a real reopenable project archive');
  if (reopenControl === 'noop') {
    await send('Runtime.callFunctionOn', {...picker,
      functionDeclaration: "function() { this.addEventListener('change', e => e.stopImmediatePropagation(), {capture:true,once:true}); }"});
  }
  await send('DOM.setFileInputFiles', { ...picker,
    files: [unpack.stdout.trim()] });
  // Neither a no-op upload nor Session.openProject's refusal can enable this from the proved empty state.
  await waitAX(/^Analysis$/, true, 'tab');
  const after = inspectArchive(await saveArchive());
  assert.deepEqual(after, before,
    'reopened project must retain its identity and every saved scientific byte, including the complete fit state');
  await writeFile(join(output, `${mode}-reopen-roundtrip.json`), JSON.stringify({before,after},null,2));
  await click(/^Analysis$/); await waitAX(/^Start fitting$/); await shot('reopened');
  }
  if (!reopenControl && fileRequestCase !== 'none') {
    const inputs = join(scratch,'routing');
    const generator = spawnSync('python', [fileURLToPath(new URL('../../fixtures/e04_t11_wasm/routing.py', import.meta.url)),inputs],
      {encoding:'utf8',timeout:10000});
    assert.equal(generator.status,0,'routing inputs must materialize from committed native inputs');
    const waitBrowser = async (expression, obligation) => {
      const deadline=Date.now()+45000;
      do { if (await evaluate(expression)) return; await frame(); } while (Date.now()<deadline);
      const observed=await evaluate('window.__e04NativeReads || []');
      throw Error(`${obligation}; actual native reads ${JSON.stringify(observed)}`);
    };
    const waitName = async name => {
      const deadline=Date.now()+45000;
      do {
        const tree=await send('Accessibility.getFullAXTree');
        if (tree.nodes.some(n=> !n.ignored && (n.value?.value===name || n.name?.value===name))) return;
        await frame();
      } while (Date.now()<deadline);
      throw Error(`requested project identity must become ${name}`);
    };
    const accessiblePress = async (regex, role='button') => {
      const found = await waitAX(regex,true,role);
      const node = await send('DOM.resolveNode',{backendNodeId:found.backendDOMNodeId});
      await send('Runtime.callFunctionOn',{objectId:node.object.objectId,
        functionDeclaration:'function() { this.click(); }',userGesture:true});
      await frame(); await settleRenderedPage();
    };
    const beginPicker = async regex => {
      lastEvents.delete('Page.fileChooserOpened');
      const opened=event('Page.fileChooserOpened');
      // Before: synthetic click on Qt's accessibility element. Now: pointer
      // input on the app control, including Qt's openFiles/Load data path.
      await click(regex, 'button');
      const chooser=await opened;
      assert(chooser.backendDOMNodeId,'each request must expose its actual browser file input');
      const result=await send('DOM.resolveNode',{backendNodeId:chooser.backendDOMNodeId});
      const picker={objectId:result.object.objectId};
      const actual=await send('Runtime.callFunctionOn',{...picker,returnByValue:true,
        functionDeclaration:'function() { return this === window.__e04FileInput && this instanceof HTMLInputElement && this.type === "file"; }'});
      assert(actual.result.value,'each request must cross the actual browser picker, not reuse an earlier input');
      return picker;
    };
    let getStartedOpen = !fileRequestsOnly;
    const projectPage = async () => {
      await click(/^Project$/);
      if (!getStartedOpen) {
        await click(/Get started$/, 'button'); getStartedOpen = true;
      }
    };
    const openFolder = async name => {
      await projectPage();
      const input=await beginPicker(/^Open an existing project/);
      await send('DOM.setFileInputFiles',{...input,files:[join(inputs,name)]});
      await waitName(name);
      await settleRenderedPage();
    };
    const snapshot = async () => { await projectPage(); return inspectArchive(await saveArchive()); };
    const createEmpty = async name => {
      await projectPage(); await accessiblePress(/^Create a new project$/);
      // Qt omits popup editors from AX, as it omits the fit table. The real rendered name
      // input at 1280x768 is recorded in seq4-f1-create's capture; type through native input.
      for (const type of ['mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent',
        {type,x:640,y:325,button:'left',clickCount:1});
      for (const type of ['keyDown','keyUp']) await send('Input.dispatchKeyEvent',
        {type,key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
      await send('Input.insertText',{text:name});
      for (const type of ['keyDown','keyUp']) await send('Input.dispatchKeyEvent',
        {type,key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await waitName(name); await settleRenderedPage();
    };
    // Capture the browser's actual reads, hold promises, and release on explicit observable states.
    await evaluate(`(() => {
      window.__e04NativeReads=[];
      const readNative=FileReader.prototype.readAsArrayBuffer;
      FileReader.prototype.readAsArrayBuffer=function(blob) {
        const record={bytes:blob.size,done:false}; window.__e04NativeReads.push(record);
        this.addEventListener('loadend',()=>{record.done=true;record.error=!!this.error;},{once:true});
        return readNative.call(this,blob);
      };
      const read=Blob.prototype.arrayBuffer;
      window.__e04Reads=[]; window.__e04HoldReads=false;
      Blob.prototype.arrayBuffer=async function() {
        if (window.__e04HoldReads) {
          const record={released:false}; window.__e04Reads.push(record);
          await new Promise(resolve=>record.release=()=>{record.released=true;resolve();});
        }
        return read.call(this);
      };
    })()`);
    const armReads = async () => evaluate('window.__e04Reads=[]; window.__e04HoldReads=true; true');
    const releaseRead = async index => evaluate(`window.__e04Reads[${index}].release(); true`);
    const completedPicker = async id => waitBrowser(`window.__e04FolderCompleted.includes(${id})`,
      'the actual folder handler must finish before checking its destination');

    if (['all','overlap'].includes(fileRequestCase)) {
    await projectPage(); await armReads();
    const first=await beginPicker(/^Open an existing project/);
    const firstId=await evaluate('window.__e04FileInput.__e04Picker');
    await send('DOM.setFileInputFiles',{...first,files:[join(inputs,'routing_a')]});
    await waitBrowser('window.__e04Reads.length===1','first folder read must be pending');
    const second=await beginPicker(/^Open an existing project/);
    const secondId=await evaluate('window.__e04FileInput.__e04Picker');
    await send('DOM.setFileInputFiles',{...second,files:[join(inputs,'routing_b')]});
    await waitBrowser('window.__e04Reads.length===2','both folder requests must overlap before either completion');
    await evaluate('window.__e04HoldReads=false; true');
    await releaseRead(0); await completedPicker(firstId);
    await releaseRead(1); await completedPicker(secondId);
    await waitName('routing_b');
    const overlap=await snapshot();
    assert.equal(overlap.name,'routing_b','a stale completion must not discard or replace the later folder');

    }
    if (['all','replacement'].includes(fileRequestCase)) {
    if (fileRequestCase !== 'all') await openFolder('routing_b');
    // A folder read started for B must not replace a project opened while that read is pending.
    await armReads();
    const obsolete=await beginPicker(/^Open an existing project/);
    const obsoleteId=await evaluate('window.__e04FileInput.__e04Picker');
    await send('DOM.setFileInputFiles',{...obsolete,files:[join(inputs,'routing_a')]});
    await waitBrowser('window.__e04Reads.length===1','replacement exercise must reach a pending upload');
    await click(/Get started$/, 'button'); getStartedOpen = false;
    await accessiblePress(/Examples$/);
    // The first delegate's Qt AX rectangle predates table layout. Input location is from
    // the 1280x768 rendered table (seq4-f1-layout capture); identity below is the oracle.
    for (const type of ['mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent',
      {type,x:992.5,y:239.5,button:'left',clickCount:1});
    await settleRenderedPage();
    await waitName('cosio_d20_s1');
    await settleRenderedPage();
    const replacementBefore=await snapshot();
    assert.notEqual(replacementBefore.name,'routing_b','the replacement control must actually replace the old live project');
    await evaluate('window.__e04HoldReads=false; true');
    await releaseRead(0); await completedPicker(obsoleteId); await settleRenderedPage();
    assert.deepEqual(await snapshot(),replacementBefore,
      'a late upload must not act on a replacement project');

    }
    if (['all','cancel-structure'].includes(fileRequestCase)) {
    // Real cancel events route through Qt. The source seam gate independently checks that no
    // stale receiver makes an unrelated refused call (a refusal can leave archive bytes unchanged).
    await createEmpty('routing_empty_c');
    await click(/^Structure$/); await waitAX(/Structures \(0\)/);
    await accessiblePress(/Structures \(0\)/);
    await beginPicker(/^Load structure from file$/);
    assert.equal(await evaluate('window.__e04FileInput.multiple'),false,
      'Structure must preserve the standalone single-file chooser contract');
    await evaluate("window.__e04FileInput.dispatchEvent(new Event('cancel')); true"); await frame();
    await click(/^Experiment$/); await waitAX(/Experiments \(0\)/);
    await accessiblePress(/Experiments \(0\)/);
    const experiment=await beginPicker(/^Load experiment\(s\) from file\(s\)$/);
    assert.equal(await evaluate('window.__e04FileInput.multiple'),true,
      'Experiment must retain its batch chooser contract');
    await send('DOM.setFileInputFiles',{...experiment,files:[join(inputs,'blocks/experiment-1.edi'),join(inputs,'blocks/experiment-2.edi')]});
    await waitAX(/Experiments \(2\)/);
    await click(/^Structure$/); await waitAX(/Structures \(0\)/);
    }
    if (['all','cancel-experiment'].includes(fileRequestCase)) {
    await createEmpty('routing_empty_d');
    await click(/^Experiment$/); await waitAX(/Experiments \(0\)/);
    if (fileRequestCase !== 'all') await accessiblePress(/Experiments \(0\)/);
    await beginPicker(/^Load experiment\(s\) from file\(s\)$/);
    await evaluate("window.__e04FileInput.dispatchEvent(new Event('cancel')); true"); await frame();
    await click(/^Structure$/); await waitAX(/Structures \(0\)/);
    if (fileRequestCase !== 'all') await accessiblePress(/Structures \(0\)/);
    const structure=await beginPicker(/^Load structure from file$/);
    assert.equal(await evaluate('window.__e04FileInput.multiple'),false,
      'Structure must keep a single-file chooser after Experiment cancellation');
    await send('DOM.setFileInputFiles',{...structure,files:[join(inputs,'blocks/structure.edi')]});
    await waitAX(/Structures \(1\)/);
    await click(/^Experiment$/); await waitAX(/Experiments \(0\)/);
    }
    if (['all','load-data'].includes(fileRequestCase)) {
    await createEmpty('routing_empty_data');
    await click(/^Experiment$/); await waitAX(/Experiments \(0\)/);
    if (fileRequestCase !== 'all') await accessiblePress(/Experiments \(0\)/);
    await click(/^Create experiment$/, 'button');
    await waitAX(/Experiments \(1\)/);
    await beginPicker(/^Load data(?:…|\.\.\.)$/);
    assert.equal(await evaluate('window.__e04FileInput.multiple'),false,
      'Load data must open a real single-file browser chooser through its experiment control');
    await evaluate("window.__e04FileInput.dispatchEvent(new Event('cancel')); true"); await frame();
    await waitAX(/Experiments \(1\)/);
    }
    await writeFile(join(output,`${mode}-file-requests.json`),JSON.stringify({case:fileRequestCase,completed:true},null,2));
  }
  assert.equal(errors.length, 0, 'both browser workflows must complete without runtime exceptions');
  await writeFile(join(output, `${mode}-browser.json`), JSON.stringify({ isolated, wasm, errors, transcript, fileRequestsOnly, fileRequestCase }, null, 2));
  if (fileRequestsOnly) console.log(`${mode}: request-only ${fileRequestCase} passed; full browser checks not run`);
  else console.log(`${mode}: workflow and saved-fit roundtrip passed; file requests ${fileRequestCase}`);
  }
} catch (error) {
  await writeFile(join(output, `${mode}-failure.json`), JSON.stringify({ message: error.message, network, errors, transcript }, null, 2));
  if (send) {
    try {
      const screenshot = await send('Page.captureScreenshot', { format: 'png' });
      await writeFile(join(output, `${mode}-failure.png`), Buffer.from(screenshot.data, 'base64'));
      const tree = await send('Accessibility.getFullAXTree');
      await writeFile(join(output, `${mode}-failure-accessibility.json`), JSON.stringify(tree, null, 2));
    } catch { /* The original failure remains the verdict if the target already closed. */ }
  }
  throw error;
} finally {
  ws?.close(); child.kill(); server.closeAllConnections(); server.close();
  await new Promise(ok => { if (child.exitCode !== null || child.signalCode !== null) ok(); else child.once('exit', ok); });
  await rm(join(output, 'saved-project'), { recursive: true, force: true });
  await rm(scratch, { recursive: true, force: true });
}
