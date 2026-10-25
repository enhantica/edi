// Run through tools/ci/wasm-check.sh against the packed production app.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {resolve, extname, sep, join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const [siteArg, mode, output, chrome] = process.argv.slice(2);
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
assert(siteArg && mode && output && chrome, 'Browser storage gates require a packed site, mode, evidence directory and real Chromium');
const site = resolve(siteArg);
await access(join(site, 'webapp/index.html'));
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
const pythonStore = (files, wanted) => {
  const program = `import base64,io,json,sys,zipfile
files=json.load(sys.stdin); candidates=[]
for path,body in files.items():
 raw=base64.b64decode(body)
 if raw.startswith(b'PK\\x03\\x04'):
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   assert len(z.namelist())==len(set(z.namelist())), 'Browser archives contain unique members'
   candidates.append({n:base64.b64encode(z.read(n)).decode() for n in z.namelist() if not n.endswith('/')})
 if path.endswith('project.edi'):
  prefix=path[:-len('project.edi')]
  candidates.append({n[len(prefix):]:v for n,v in files.items() if n.startswith(prefix)})
print(json.dumps([c for c in candidates if sys.argv[1].encode() in base64.b64decode(c.get('project.edi',''))]))`;
  const result=spawnSync('python',['-c',program,wanted],{input:JSON.stringify(files),encoding:'utf8'});
  assert.equal(result.status,0,'Independent Python ZIP/directory inspection reads the browser-stored project');
  const matches=JSON.parse(result.stdout);
  assert(matches.length>0,'Actual OPFS bytes contain the requested saved or recovery state');
  return matches;
};
try {
  for (const scenario of ['example-folder','example-zip','upload-fallback','disk-folder','disk-record','disk-zip']) {
    const fallback=scenario==='upload-fallback';
    const context=await browser.newContext({viewport:{width:1280,height:768},acceptDownloads:true});
    const page=await context.newPage();
    const cdp=await context.newCDPSession(page);
    await cdp.send('Accessibility.enable');
    const events={downloads:0,filechoosers:0,dialogs:0};
    page.on('download',()=>++events.downloads);
    page.on('filechooser',()=>++events.filechoosers);
    page.on('dialog',async dialog=>{++events.dialogs;await dialog.dismiss();});
    await page.addInitScript(({initial,scenario,fallback})=>{
      window.__storagePicks={directory:0,open:0,save:0};
      const put=async(folder,members)=>{
        for(const [name,body] of Object.entries(members)) {
          const parts=name.split('/');let parent=folder;
          for(const part of parts.slice(0,-1))parent=await parent.getDirectoryHandle(part,{create:true});
          const handle=await parent.getFileHandle(parts.at(-1),{create:true});
          const stream=await handle.createWritable();await stream.write(Uint8Array.from(atob(body),c=>c.charCodeAt(0)));await stream.close();
        }
      };
      // This is only the user's picker selection. Every byte uses real browser file handles.
      // It is not proof of an OS file-picker widget or actual Firefox/Safari execution.
      window.__storageHandles=(async()=>{
        const root=await navigator.storage.getDirectory();
        const disk=await root.getDirectoryHandle('test-picked-output',{create:true});
        if(!(await disk.keys().next()).done)return disk;
        await put(disk,initial);return disk;
      })();
      if(fallback) {
        for(const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
          Object.defineProperty(window,name,{value:undefined,configurable:true});
      } else {
        window.showDirectoryPicker=async()=>{++window.__storagePicks.directory;return await window.__storageHandles;};
        window.showOpenFilePicker=async()=>{
          ++window.__storagePicks.open;
          const folder=await window.__storageHandles;
          return [await folder.getFileHandle(scenario==='disk-zip'?'picked.zip':'project.edi')];
        };
        window.showSaveFilePicker=async()=>{++window.__storagePicks.save;return await (await window.__storageHandles).getFileHandle('destination.zip',{create:true});};
        if(scenario==='disk-folder')Object.defineProperty(window,'showOpenFilePicker',{value:undefined,configurable:true});
      }
    },{initial,scenario,fallback});
    const frame=()=>page.evaluate(()=>new Promise(ok=>requestAnimationFrame(()=>ok(true))));
    const ax=async()=> (await cdp.send('Accessibility.getFullAXTree')).nodes.filter(n=>!n.ignored);
    const control=async(regex,role)=>{
      const deadline=Date.now()+45000;
      while(Date.now()<deadline){
        for(const node of (await ax()).filter(n=>regex.test(n.name?.value||'')&&(!role||n.role?.value===role)&&!(n.properties||[]).some(p=>p.name==='disabled'&&p.value.value))){
          if(!node.backendDOMNodeId)continue;
          try{const {model}=await cdp.send('DOM.getBoxModel',{backendNodeId:node.backendDOMNodeId});const q=model.content,x=((q[0]+q[2]+q[4]+q[6])/4%1280+1280)%1280,y=(q[1]+q[3]+q[5]+q[7])/4;
            if(model.width>0&&model.height>0&&y>=0&&y<768)return {node,x,y};
          }catch{}
        }
        await frame();
      }
      throw Error('The real browser UI must expose '+regex);
    };
    const click=async(regex,role)=>{const item=await control(regex,role);await page.mouse.click(item.x,item.y);await frame();};
    const geometry=async(name)=>{
      await page.waitForFunction(name=>{const r=window.ediControlGeometry?.(name);return r?.visible&&r.enabled&&r.width>0&&r.height>0;},name);
      return page.evaluate(name=>window.ediControlGeometry(name),name);
    };
    const location=async regex=>{
      const rect=await geometry('project.location');
      const item=await control(regex);
      assert(item.x>=rect.x&&item.x<=rect.x+rect.width&&item.y>=rect.y&&item.y<=rect.y+rect.height,'The required working-place text is rendered in the actual Project Location field');
    };
    const clean=()=>page.waitForFunction(()=>{const r=window.ediControlGeometry?.('appBar.button.save');return r?.visible&&r.enabled===false;});
    const edit=async(name,value)=>{const r=await geometry(name);await page.mouse.click(r.x+r.width/2,r.y+r.height/2);await page.keyboard.press('ControlOrMeta+A');await page.keyboard.type(value);await page.keyboard.press('Tab');await frame();};
    const activate=async()=>{
      const activation=await control(/(?:activate|enable) screen reader/i,'button');
      const resolved=await cdp.send('DOM.resolveNode',{backendNodeId:activation.node.backendDOMNodeId});
      await cdp.send('Runtime.callFunctionOn',{objectId:resolved.object.objectId,functionDeclaration:'function(){this.click();}'});
      await click(/^Start$/);await click(/^Project$/,'tab');
    };
    const readFiles=async(picked=false)=>page.evaluate(async picked=>{
      const files={};
      const walk=async(folder,prefix='')=>{for await(const [name,handle] of folder.entries()){
        if(!picked&&prefix===''&&name==='test-picked-output')continue;
        if(handle.kind==='directory')await walk(handle,prefix+name+'/');
        else{const bytes=new Uint8Array(await(await handle.getFile()).arrayBuffer());files[prefix+name]=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));}
      }};
      await walk(picked?await window.__storageHandles:await navigator.storage.getDirectory());return files;
    },picked);
    const awaitStored=async name=>{
      const deadline=Date.now()+30000;
      while(Date.now()<deadline){
        try{return pythonStore(await readFiles(),name);}catch(error){if(!/requested saved or recovery state/.test(error.message))throw error;}
        await frame();
      }
      throw Error('Actual browser storage must durably contain '+name);
    };
    const exportZip=async (label,copy=true)=>{
      await click(/^Save project as/);await control(/^Save project as$/);
      await click(/^Zip archive$/,'radio');if(copy)await click(/^Save a copy/,'checkbox');
      const previous=fallback?0:await page.evaluate(async()=>{try{return (await(await(await window.__storageHandles).getFileHandle('destination.zip')).getFile()).lastModified;}catch{return 0;}});
      const download=fallback?page.waitForEvent('download'):null;await click(/^OK$/,'button');
      const path=join(output,scenario+'-'+label+'.zip');
      if(fallback)await(await download).saveAs(path);
      else {
        await page.waitForFunction(async previous=>{try{const file=await(await(await window.__storageHandles).getFileHandle('destination.zip')).getFile();return file.size>0&&file.lastModified>previous;}catch{return false;}},previous);
        const encoded=await page.evaluate(async()=>{const bytes=new Uint8Array(await(await(await(await window.__storageHandles).getFileHandle('destination.zip')).getFile()).arrayBuffer());return btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));});
        await writeFile(path,Buffer.from(encoded,'base64'));
      }
      const parsed=spawnSync('python',['-c','import base64,json,sys,zipfile\nwith zipfile.ZipFile(sys.argv[1]) as z:\n assert len(z.namelist())==len(set(z.namelist())), "Export has no duplicate members"\n print(json.dumps({n:base64.b64encode(z.read(n)).decode() for n in z.namelist() if not n.endswith("/")}))',path],{encoding:'utf8'});
      assert.equal(parsed.status,0,'The actual Save-as download is independently readable');return JSON.parse(parsed.stdout);
    };
    await page.goto(origin+'/webapp/');await activate();
    if(scenario.startsWith('example')){
      // Find the real catalogue row through its actual search field, then real pointer input.
      await click(/^Examples$/);await edit('examples.search','sc-neut-cwl_tb2ti2o7-heidi_basic');
      await click(/^sc-neut-cwl_tb2ti2o7-heidi_basic:/,'button');
    } else if(fallback){
      const chooser=page.waitForEvent('filechooser');await click(/^Open project(?:…|\.\.\.)?$/);await(await chooser).setFiles(fixture);
    } else {
      await page.evaluate(async encoded=>{
        const file=await(await window.__storageHandles).getFileHandle('picked.zip',{create:true});const stream=await file.createWritable();await stream.write(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)));await stream.close();
      },(await readFile(fixture)).toString('base64'));
      await click(/^Open project(?:…|\.\.\.)?$/);
    }
    await control(/^Analysis$/,'tab');
    if(scenario==='disk-folder')assert((await page.evaluate(()=>window.__storagePicks.directory))>0,'The disk-folder case actually reaches the directory picker');
    if(scenario==='disk-record'||scenario==='disk-zip')assert((await page.evaluate(()=>window.__storagePicks.open))>0,'Record and ZIP opening actually reach the file-handle picker');
    const name='browser-saved-'+scenario;
    await edit('project.name',name);
    const before={...events},picksBefore=await page.evaluate(()=>({...window.__storagePicks}));
    await click(/^Save current state of the project$/,'button');
    const browserPlace=scenario.startsWith('example')||fallback;
    let stored;
    if(browserPlace){
      stored=await awaitStored(name);
      await location(/^In this browser only$/);
      await control(/Saved in this browser only[.\s][\s\S]*Use Save project as…/);
    } else {
      const deadline=Date.now()+30000;let candidates=[];
      while(Date.now()<deadline){try{candidates=pythonStore(await readFiles(true),name);break;}catch(error){if(!/requested saved or recovery state/.test(error.message))throw error;}await frame();}
      assert(candidates.length>0,'Chromium ordinary Save writes the opened real file or folder in place');stored=candidates;await location(scenario==='disk-zip'?/picked\.zip/:/test-picked-output/);
    }
    await clean();
    assert.deepEqual(events,before,'Ordinary Save has no download, file chooser or browser dialog');
    assert.deepEqual(await page.evaluate(()=>window.__storagePicks),picksBefore,'Ordinary Save never asks for another disk location');
    if(fallback){
      assert(stored.some(m=>m['reports/opaque.html']===initial['reports/opaque.html']),'Browser storage keeps exact independently authored report bytes');
    }
    const snapshot=await exportZip('saved');
    assert(stored.some(m=>Object.keys(m).length===Object.keys(snapshot).length&&Object.entries(snapshot).every(([n,b])=>m[n]===b)),'The downloaded project contains the exact saved browser/disk model and report bytes');
    await page.reload();await activate();
    await click(/^Recent projects$/);
    await control(new RegExp(name));
    if(browserPlace)await control(/^In this browser$/);
    await click(new RegExp(name));await control(/^Analysis$/,'tab');
    assert.deepEqual(await exportZip('reopened'),snapshot,'Reload then Recent projects reopens every saved project and report byte identically');
    const unsaved='browser-unsaved-'+scenario;
    await edit('project.name',unsaved);
    await awaitStored(unsaved);
    await page.reload();await activate();await click(/^Recent projects$/);
    await click(/^Continue where you left off/);
    await control(/^Analysis$/,'tab');
    const recovered=await exportZip('recovered');
    assert(Buffer.from(recovered['project.edi'],'base64').toString().includes(unsaved),'Continue where you left off recovers the actual unsaved name after a page reload');
    for(const [member,body] of Object.entries(snapshot))if(member!=='project.edi')assert.equal(recovered[member],body,'Recovery retains every unchanged scientific and report member: '+member);
    if(scenario==='example-folder'||scenario==='example-zip') {
      if(scenario==='example-folder'){
        await click(/^Save project as/);await control(/^Save project as$/);await click(/^Folder$/,'radio');await click(/^OK$/,'button');
        await location(/test-picked-output/);
      } else {await exportZip('becomes-working-place',false);await location(/destination\.zip/);}
      const external='external-next-save-'+scenario;
      await edit('project.name',external);
      const picks=await page.evaluate(()=>({...window.__storagePicks})),counts={...events};
      await click(/^Save current state of the project$/,'button');
      const deadline=Date.now()+30000;let written=[];
      while(Date.now()<deadline){try{written=pythonStore(await readFiles(true),external);break;}catch(error){if(!/requested saved or recovery state/.test(error.message))throw error;}await frame();}
      assert(written.length>0,'After Save as the picked folder or ZIP becomes the real working place');
      assert.deepEqual(await page.evaluate(()=>window.__storagePicks),picks,'Later Save writes the chosen disk place without another picker');
      assert.deepEqual(events,counts,'Later Save to a writable chosen disk place has no download or dialog');
    }
    receipts[scenario]={saved:stored,snapshot,recovered,events,picks:await page.evaluate(()=>window.__storagePicks),browser:'real Chromium',capability:fallback?'File System Access disabled; Firefox/Safari path simulated':'File System Access with real handles supplied at picker boundary'};
    await page.screenshot({path:join(output,scenario+'.png')});await context.close();
  }
  await writeFile(join(output,'browser-storage.json'),JSON.stringify({mode,receipts},null,2));
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
