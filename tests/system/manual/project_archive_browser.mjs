// Run through tools/ci/wasm-check.sh against the packed production app.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, extname, sep, join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {controlPointer,restoreCanvasViewport,waitControlGeometry} from './web_control_geometry.mjs';

const [siteArg, mode, output, chrome] = process.argv.slice(2);
const selectedCapability=process.argv.find(arg=>arg.startsWith('--capability='))?.split('=')[1];
assert(!selectedCapability || ['folder','fallback'].includes(selectedCapability),
  'The scoped archive gate must select a declared browser filesystem capability');
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
const site = resolve(siteArg);
await mkdir(output, {recursive:true});
const server = createServer(async (req, res) => {
  try {
    const pathname=new URL(req.url,'http://localhost').pathname;
    if(mode==='singlethread' && pathname.endsWith('/coi-serviceworker.js')) {res.writeHead(404);res.end();return;}
    const path = resolve(site, '.' + pathname+(pathname.endsWith('/')?'index.html':''));
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
const declaredRule=Buffer.from(initial['project.edi'],'base64').toString().match(/^_su_format\.rule\s+(\S+)/m)?.[1];
assert(declaredRule,'The archive fixture must declare the save rule that Open and Save must retain');
const archiveInput=(await readFile(fixture)).toString('base64');
const receipts = {};
let activePage;
try {
  for (const capability of selectedCapability?[selectedCapability]:['folder', 'fallback']) {
    const context = await browser.newContext({viewport:{width:1280,height:768}, acceptDownloads:true});
    const page = await context.newPage();
    activePage=page;page.setDefaultTimeout(45000);
    page.on('pageerror',error=>console.error('browser exception:',error.message));
    const cdp = await context.newCDPSession(page);
    await cdp.send('Accessibility.enable');
    await page.addInitScript(({capability, initial, archiveInput}) => {
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
        window.__projectZipPickCount=0;
        window.showOpenFilePicker=async()=>{
          ++window.__projectZipPickCount;
          const root=await navigator.storage.getDirectory();
          const handle=await root.getFileHandle('archive-input.zip',{create:true});
          const stream=await handle.createWritable();
          await stream.write(Uint8Array.from(atob(archiveInput),value=>value.charCodeAt(0)));await stream.close();
          return [handle];
        };
        window.__projectArchiveWrites=[];
        window.showSaveFilePicker=async()=>{
          const root=await navigator.storage.getDirectory();
          const handle=await root.getFileHandle('archive-export-'+window.__projectArchiveWrites.length+'.zip',{create:true});
          window.__projectArchiveWrites.push(handle);return handle;
        };
      } else {
        for (const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
          Object.defineProperty(window, name, {value:undefined, configurable:true});
      }
    }, {capability, initial, archiveInput});
    await page.goto(origin + '/?build='+mode);
    await page.waitForFunction(expected=>window.ediBuildInfo?.build===expected && typeof window.ediControlGeometry==='function',mode,{timeout:90000});
    const frame = () => page.evaluate(() => new Promise(ok => requestAnimationFrame(() => ok(true))));
    const ready=async(read,obligation)=>{
      const deadline=Date.now()+45000;
      do {const value=await read();if(value)return value;await frame();}while(Date.now()<deadline);
      throw Error(obligation);
    };
    const settle=async()=>{
      const deadline=Date.now()+15000;let previous,stable=0;
      do {
        await frame();const current=(await cdp.send('Page.captureScreenshot',{format:'png'})).data;
        stable=current===previous?stable+1:0;previous=current;
        if(stable>=2)return;
      }while(Date.now()<deadline);
      throw Error('The actual dialog must finish its entry transition before default Enter');
    };
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
    const geometry=name=>waitControlGeometry(expression=>page.evaluate(expression),frame,name);
    const nativeClick=async name=>{
      await restoreCanvasViewport(expression=>page.evaluate(expression));
      await geometry(name);
      const point=await controlPointer(expression=>page.evaluate(expression),name);
      console.log(mode,capability,'native pointer',name,point.x,point.y);
      await page.mouse.move(point.x,point.y);await page.mouse.down();await frame();await page.mouse.up();await frame();
    };
    const accept=async()=>{
      await settle();
      console.log(mode,capability,'accept native dialog with default Enter');
      await page.keyboard.press('Enter');await frame();
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
      assert.equal(result.status,0,'The exported project is independently readable with Python zipfile: '+result.stderr);
      return JSON.parse(result.stdout);
    };
    const saveAs = async (zip, copy, name) => {
      await nativeClick('project.saveAs');
      await nativeClick(zip?'saveAs.zip':'saveAs.folder');
      const copyChoice=await waitControlGeometry(expression=>page.evaluate(expression),frame,'saveAs.copy',{enabled:false});
      if(copyChoice.checked!==copy) {
        assert.equal(copyChoice.enabled,true,'A required Save-a-copy change must be an available real dialog choice');
        await nativeClick('saveAs.copy');
      }
      const observed=await waitControlGeometry(expression=>page.evaluate(expression),frame,'saveAs.copy',{enabled:false});
      assert.equal(observed.checked,copy,'The actual Save-as dialog must hold the requested Save-a-copy state');
      await writeFile(join(output,capability+'-'+(name||'folder')+'-dialog.json'),JSON.stringify({
        choice:await geometry(zip?'saveAs.zip':'saveAs.folder'),copy:observed,
      },null,2));
      const completed = zip && capability==='fallback' ? page.waitForEvent('download') : null;
      const previous=capability==='folder'?await page.evaluate(()=>window.__projectArchiveWrites.length):0;
      await accept();
      if (!zip) return null;
      const path = join(output, name);
      if(completed) await (await completed).saveAs(path);
      else {
        const encoded=await ready(()=>page.evaluate(async previous=>{
          const handle=window.__projectArchiveWrites[previous];if(!handle)return false;
          const file=await handle.getFile(),bytes=new Uint8Array(await file.arrayBuffer());
          return file.size>0 && bytes.length===file.size && btoa(Array.from(bytes,value=>String.fromCharCode(value)).join(''));
        },previous),'The browser must finish writing nonempty ZIP bytes before independent inspection');
        await writeFile(path,Buffer.from(encoded,'base64'));
      }
      return inspect(path);
    };
    const savedCopy = async () => saveAs(true, true, capability+'-copy.zip');
    const chooser=capability==='fallback'?page.waitForEvent('filechooser'):null;
    await nativeClick('project.open');
    await nativeClick('open.zip');await accept();
    if(chooser)await (await chooser).setFiles(fixture);
    await control(/^Analysis$/,'tab');
    if(capability==='folder')assert.equal(await page.evaluate(()=>window.__projectZipPickCount),1,
      'Opening the fixture ZIP must read the actual browser file handle supplied by one file picker');
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
      await ready(()=>page.evaluate(async rule => {
        const root=await window.__projectFolderReady;
        const text=await (await (await root.getFileHandle('project.edi')).getFile()).text();
        return text.match(/^_su_format\.rule\s+(\S+)/m)?.[1]===rule && text.includes('archive-folder-first');
      },declaredRule),'The chosen folder must contain the edited project with its declared save rule retained');
      const first=await readFolder();
      assert.equal(first['reports/opaque.html'],initial['reports/opaque.html'],'Picked-folder Save retains exact report bytes');
      const picks=await page.evaluate(()=>window.__projectFolderPickCount);
      await rename('archive-folder-second');
      await click(/^Save current state of the project$/, 'button');
      await ready(()=>page.evaluate(async () => {
        const root=await window.__projectFolderReady;
        return (await (await root.getFileHandle('project.edi')).getFile()).text().then(text=>text.includes('archive-folder-second'));
      }),'Ordinary Save must finish overwriting the chosen folder before its bytes are compared');
      const second=await readFolder();
      assert.equal(await page.evaluate(()=>window.__projectFolderPickCount),picks,'Later Save overwrites the picked folder without another picker');
      assert.notEqual(second['project.edi'],first['project.edi'],'A later Save really overwrites the picked folder with the edited model');
      const archive=await savedCopy();
      assert.deepEqual(archive,second,'Save a copy as ZIP contains exactly the picked folder member names and bytes');
      receipts.folder={first,second,picks,archive};
    } else {
      const members=await saveAs(true, true, 'fallback.zip');
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
} catch(error) {
  if(activePage && !activePage.isClosed()) {
    await writeFile(join(output,'failure.json'),JSON.stringify({error:error.stack,
      page:await activePage.evaluate(()=>({build:window.ediBuildInfo,screen:document.getElementById('screen')?.style.display})).catch(()=>null),
    },null,2));
    await activePage.screenshot({path:join(output,'failure.png'),timeout:5000}).catch(captureError=>
      console.error('Failure screenshot unavailable:',captureError.message));
  }
  throw error;
} finally {await browser.close(); await new Promise(ok=>server.close(ok));}
