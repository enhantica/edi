// Run through tools/ci/wasm-check.sh against the packed production app.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, extname, sep, join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const [siteArg, mode, output, chrome] = process.argv.slice(2);
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
const site = resolve(siteArg);
await mkdir(output, {recursive:true});
const server = createServer(async (req, res) => {
  try {
    const path = resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    assert(path.startsWith(site + sep), 'The browser gate serves only the packed app');
    const bytes = await readFile(extname(path) ? path : join(path, 'index.html'));
    const headers = {'Content-Type':({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm'})[extname(path)] || 'text/html'};
    if (mode === 'multithread') Object.assign(headers, {'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'});
    res.writeHead(200, headers); res.end(bytes);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await chromium.launch({executablePath:chrome, headless:true,
  args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const origin = `http://127.0.0.1:${server.address().port}`;
const fixture = join(repo, 'tests/fixtures/project_archive/sc-neut-cwl_tb2ti2o7-heidi_basic.zip');
const documents = spawnSync('python', ['-c', 'import base64,json,sys,zipfile\nwith zipfile.ZipFile(sys.argv[1]) as z: print(json.dumps({n:base64.b64encode(z.read(n)).decode() for n in z.namelist() if not n.endswith("/")}))', fixture], {encoding:'utf8'});
assert.equal(documents.status, 0, 'Browser input comes from Python zipfile, independently of the app');
const initial = JSON.parse(documents.stdout);
const receipts = {};
try {
  for (const capability of ['folder', 'fallback']) {
    const context = await browser.newContext({viewport:{width:1280,height:768}, acceptDownloads:true});
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send('Accessibility.enable');
    await page.addInitScript(({capability, initial}) => {
      window.__projectFolderPickCount = 0;
      window.__projectFolderReady = (async () => {
        const store = await navigator.storage.getDirectory();
        const root = await store.getDirectoryHandle('project', {create:true});
        for await (const name of root.keys()) await root.removeEntry(name, {recursive:true});
        for (const [name, encoded] of Object.entries(initial)) {
          const parts = name.split('/'); let parent = root;
          for (const part of parts.slice(0,-1)) parent = await parent.getDirectoryHandle(part, {create:true});
          const file = await parent.getFileHandle(parts.at(-1), {create:true});
          const stream = await file.createWritable();
          await stream.write(Uint8Array.from(atob(encoded), c => c.charCodeAt(0))); await stream.close();
        }
        return root;
      })();
      // Supply the user's folder choice; all reads and writes use real Chromium directory/file handles.
      if (capability === 'folder') {
        window.showDirectoryPicker = async () => { ++window.__projectFolderPickCount; return await window.__projectFolderReady; };
      } else {
        for (const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
          Object.defineProperty(window, name, {value:undefined, configurable:true});
      }
    }, {capability, initial});
    await page.goto(origin + '/webapp/');
    const frame = () => page.evaluate(() => new Promise(ok => requestAnimationFrame(() => ok(true))));
    const control = async (regex, role) => {
      const deadline = Date.now()+45000;
      while (Date.now()<deadline) {
        const {nodes} = await cdp.send('Accessibility.getFullAXTree');
        for (const node of nodes.filter(n => !n.ignored && regex.test(n.name?.value || '') && (!role || n.role?.value===role) && !(n.properties||[]).some(p=>p.name==='disabled' && p.value.value))) {
          if (!node.backendDOMNodeId) continue;
          try {
            const {model} = await cdp.send('DOM.getBoxModel',{backendNodeId:node.backendDOMNodeId});
            const q=model.content, x=((q[0]+q[2]+q[4]+q[6])/4%1280+1280)%1280, y=(q[1]+q[3]+q[5]+q[7])/4;
            if(model.width>0 && model.height>0 && y>=0 && y<768) return {node,x,y};
          } catch {}
        }
        await frame();
      }
      throw Error('The production UI must expose ' + regex);
    };
    const click = async (regex, role) => {const item=await control(regex,role); await page.mouse.click(item.x,item.y); await frame();};
    const activation = await control(/(?:activate|enable) screen reader/i,'button');
    const resolved = await cdp.send('DOM.resolveNode',{backendNodeId:activation.node.backendDOMNodeId});
    await cdp.send('Runtime.callFunctionOn',{objectId:resolved.object.objectId,functionDeclaration:'function(){this.click();}'});
    await click(/^Start$/); await click(/^Project$/,'tab');
    const rename = async name => {
      const item = await page.evaluate(() => window.ediControlGeometry('project.name'));
      assert(item?.visible && item.enabled && item.width > 0 && item.height > 0,
        'Folder overwrite uses the actual project-name editor');
      await page.mouse.click(item.x + item.width/2, item.y + item.height/2);
      await page.keyboard.press('ControlOrMeta+A'); await page.keyboard.type(name);
      await page.keyboard.press('Tab'); await frame();
    };
    const inspect = archive => {
      const result=spawnSync('python',['-c','import base64,json,sys,zipfile\nwith zipfile.ZipFile(sys.argv[1]) as z: print(json.dumps({n:base64.b64encode(z.read(n)).decode() for n in z.namelist() if not n.endswith("/")}))',archive],{encoding:'utf8'});
      assert.equal(result.status,0,'The exported project is independently readable with Python zipfile');
      return JSON.parse(result.stdout);
    };
    const saveAs = async (zip, copy, name) => {
      await click(/^Save project as/);
      await control(/^Save project as$/);
      await click(zip ? /^Zip archive$/ : /^Folder$/, 'radio');
      if (copy) await click(/^Save a copy/, 'checkbox');
      const completed = zip ? page.waitForEvent('download') : null;
      await click(/^OK$/, 'button');
      if (!zip) return null;
      const path = join(output, name);
      await (await completed).saveAs(path);
      return inspect(path);
    };
    const savedCopy = async () => saveAs(true, true, capability+'-copy.zip');
    const chooser=page.waitForEvent('filechooser');
    await click(/^Open project(?:…|\.\.\.)?$/);
    await (await chooser).setFiles(fixture);
    await control(/^Analysis$/,'tab');
    if (capability === 'folder') {
      await page.evaluate(() => window.__projectFolderReady.then(()=>true));
      await rename('archive-folder-first');
      await saveAs(false, false);
      const readFolder = () => page.evaluate(async () => {
        const result={};
        const walk=async (folder,prefix='')=>{for await(const [name,handle] of folder.entries()) {
          if(handle.kind==='directory') await walk(handle,prefix+name+'/');
          else {const bytes=new Uint8Array(await (await handle.getFile()).arrayBuffer()); result[prefix+name]=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));}
        }};
        await walk(await window.__projectFolderReady); return result;
      });
      await page.waitForFunction(async () => {
        const root=await window.__projectFolderReady;
        return (await (await root.getFileHandle('project.edi')).getFile()).text().then(text=>/_su_format\.rule\s+iucr_99/.test(text));
      });
      const first=await readFolder();
      assert.equal(first['reports/opaque.html'],initial['reports/opaque.html'],'Picked-folder Save retains exact report bytes');
      const picks=await page.evaluate(()=>window.__projectFolderPickCount);
      await rename('archive-folder-second');
      await click(/^Save current state of the project$/, 'button');
      await page.waitForFunction(async () => {
        const root=await window.__projectFolderReady;
        return (await (await root.getFileHandle('project.edi')).getFile()).text().then(text=>text.includes('archive-folder-second'));
      });
      const second=await readFolder();
      assert.equal(await page.evaluate(()=>window.__projectFolderPickCount),picks,'Later Save overwrites the picked folder without another picker');
      assert.notEqual(second['project.edi'],first['project.edi'],'A later Save really overwrites the picked folder with the edited model');
      const archive=await savedCopy();
      assert.deepEqual(archive,second,'Save a copy as ZIP contains exactly the picked folder member names and bytes');
      receipts.folder={first,second,picks,archive};
    } else {
      const members=await saveAs(true, false, 'fallback.zip');
      assert.equal(members['reports/opaque.html'],initial['reports/opaque.html'],'Fallback ZIP Save retains exact report bytes');
      assert(members['project.edi'],'Fallback ZIP Save contains the project record');
      const archive=await savedCopy();
      assert.deepEqual(archive,members,'Save a copy as ZIP retains exactly the previously saved project members and report bytes');
      receipts.fallback={members,archive};
    }
    await page.screenshot({path:join(output,capability+'.png')});
    await context.close();
  }
  await writeFile(join(output,'project-archives.json'),JSON.stringify({mode,receipts},null,2));
} finally {await browser.close(); await new Promise(ok=>server.close(ok));}
