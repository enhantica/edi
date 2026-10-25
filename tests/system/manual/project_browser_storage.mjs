// Run through tools/ci/wasm-check.sh against the packed production app.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {resolve, extname, sep, join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {restoreCanvasViewport} from './web_control_geometry.mjs';
import {installDownloadBoundary,assertPendingNotice,checkNoticeControls,assertFallbackChoices,assertBrowserWarning,checkChoiceAndWarningControls} from './browser_download_boundary.mjs';
checkNoticeControls();checkChoiceAndWarningControls();

const [siteArg, mode, output, chrome] = process.argv.slice(2);
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
assert(siteArg && mode && output && chrome, 'Browser storage gates require a packed site, mode, evidence directory and real Chromium');
const site = resolve(siteArg);
await access(join(site, 'index.html'));
await mkdir(output, {recursive:true});
const server = createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (mode === 'singlethread' && pathname.endsWith('/coi-serviceworker.js')) {res.writeHead(404);res.end();return;}
    const path = resolve(site, '.' + pathname + (pathname.endsWith('/') ? 'index.html' : ''));
    assert(path.startsWith(site + sep), 'The browser gate serves only the packed app');
    const bytes = await readFile(extname(path) ? path : join(path, 'index.html'));
    const headers = {'Content-Type':({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm','.json':'application/json','.css':'text/css','.svg':'image/svg+xml'})[extname(path)] || 'text/html'};
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
const observation=JSON.parse(await readFile(join(repo,'tests/fixtures/project_archive/browser_save_observation.json'),'utf8')).controls;
const offersProjectRecord=options=>options?.types?.some(type=>
  Object.values(type.accept??{}).some(extensions=>Array.isArray(extensions)&&
    extensions.some(extension=>typeof extension==='string'&&extension.toLowerCase()==='.edi')))===true;
assert(!offersProjectRecord({types:[{description:'project.edi archive',accept:{'application/zip':['.zip']}}]}),
  'A picker description cannot impersonate an offered project record extension');
assert(offersProjectRecord({types:[{accept:{'application/octet-stream':['.edi']}}]})&&
  offersProjectRecord({types:[{accept:{'application/octet-stream':['.EDI']}}]})&&!offersProjectRecord({}),
  'Only an explicitly accepted project record extension satisfies the file-route requirement');
const receipts = {}, failures = {};
const logicalMembers=members=>{
  const logical={...members};const text=Buffer.from(members['project.edi'],'base64').toString();
  const field=/^(_metadata\.last_modified[ \t]+).+$/gm;
  assert.equal([...text.matchAll(field)].length,1,'A saved project has exactly one declared wall-clock field');
  logical['project.edi']=Buffer.from(text.replace(field,'$1<NORMALIZED-WALL-CLOCK>')).toString('base64');
  return logical;
};
let activePage,activeCdp;
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
  for (const scenario of (process.env.EDI_BROWSER_STORAGE_SCENARIOS || 'example-folder,example-zip,upload-fallback,disk-folder,disk-record,disk-zip,example-private,example-private-save,example-warning,example-warning-save-as').split(',')) {
    console.log(mode,scenario,'starting');
    const privateStorage=scenario.startsWith('example-private'),warningScenario=scenario.startsWith('example-warning');
    const boundary=privateStorage||warningScenario;
    const fallback=scenario==='upload-fallback'||boundary;
    const context=await browser.newContext({viewport:{width:1280,height:768},acceptDownloads:true});
    const page=await context.newPage();
    page.setDefaultTimeout(45000);
    const cdp=await context.newCDPSession(page);activePage=page;activeCdp=cdp;
    await cdp.send('Accessibility.enable');
    const events={downloads:0,filechoosers:0,dialogs:0};
    page.on('download',()=>++events.downloads);
    page.on('filechooser',()=>++events.filechoosers);
    page.on('dialog',async dialog=>{++events.dialogs;await dialog.dismiss();});
    if(boundary)await page.addInitScript(installDownloadBoundary,{denyStorage:scenario==='example-private'});
    await page.addInitScript(({initial,scenario,fallback,boundary})=>{
      const nativeFocus=HTMLElement.prototype.focus;
      HTMLElement.prototype.focus=function(options){return nativeFocus.call(this,{...options,preventScroll:true});};
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
      if(!boundary)window.__storageHandles=(async()=>{
        const root=await navigator.storage.getDirectory();
        const disk=await root.getDirectoryHandle('test-picked-output',{create:true});
        if(!(await disk.keys().next()).done)return disk;
        await put(disk,initial);return disk;
      })();
      if(!boundary)window.__storageExportHandles=navigator.storage.getDirectory().then(root=>root.getDirectoryHandle('test-picked-exports',{create:true}));
      if(fallback) {
        for(const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
          Object.defineProperty(window,name,{value:undefined,configurable:true});
      } else {
        window.showDirectoryPicker=async()=>{++window.__storagePicks.directory;return await window.__storageHandles;};
        window.showOpenFilePicker=async options=>{
          window.__storageOpenOptions=options;
          ++window.__storagePicks.open;
          const folder=await window.__storageHandles;
          return [await folder.getFileHandle(scenario==='disk-zip'?'picked.zip':'project.edi')];
        };
        window.showSaveFilePicker=async()=>{++window.__storagePicks.save;return await (await window.__storageExportHandles).getFileHandle('destination.zip',{create:true});};

      }
    },{initial,scenario,fallback,boundary});
    const navigationError=error=>/Execution context was destroyed|Cannot find context|navigated/i.test(error.message);
    const evaluate=async(expression,arg)=>{
      const deadline=Date.now()+45000;
      while(true){try{return await page.evaluate(expression,arg);}catch(error){
        if(!navigationError(error)||Date.now()>=deadline)throw error;
        await page.waitForLoadState('domcontentloaded');
      }}
    };
    const frame=()=>evaluate(()=>new Promise(ok=>requestAnimationFrame(()=>ok(true))));
    const settle=async()=>{
      const deadline=Date.now()+15000;let previous,stable=0;
      while(Date.now()<deadline){await frame();const current=(await cdp.send('Page.captureScreenshot',{format:'png'})).data;stable=current===previous?stable+1:0;previous=current;if(stable>=2)return;}
      throw Error('Actual application layout must settle before the next real pointer action');
    };
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
    let lastDialogControl;
    const click=async(regex,role)=>{
      await restoreCanvasViewport(expression=>evaluate(expression));
      // Qt's shipped Popup controls are drawn but absent from the web AX tree.
      // Resolve the declared native radio/checkbox, then use trusted input; the
      // subsequent real picker/write proves that the dialog accepted the choice.
      if(role==='radio'||role==='checkbox') {
        const opening=await evaluate(()=>{try{return window.ediControlGeometry('open.folder').visible}catch{return false}});
        const objectName=role==='checkbox'?'saveAs.copy':(opening?'open.':'saveAs.')+(regex.test('Zip archive')?'zip':'folder');
        lastDialogControl=objectName;
        const rect=await geometry(objectName);console.log(mode,scenario,'native choice',objectName);
        await page.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);await page.mouse.down();await frame();await page.mouse.up();await frame();return;
      }
      if(regex.source==='^OK$') {
        const tabs=lastDialogControl==='saveAs.folder'?3:lastDialogControl==='saveAs.zip'||lastDialogControl==='open.folder'?2:1;
        console.log(mode,scenario,'accept real dialog with keyboard',tabs);
        for(let i=0;i<tabs;++i)await page.keyboard.press('Tab');
        await page.keyboard.press('Space');await frame();return;
      }
      const item=await control(regex,role);console.log(mode,scenario,'click',item.node.name?.value);
      let point=item;
      const names={'Open project…':'project.open','Save project as…':'project.saveAs','Save current state of the project':'appBar.button.save'};
      const groupName=/Examples$/.test(item.node.name?.value||'')?'group.examples':/Recent projects$/.test(item.node.name?.value||'')?'group.recentProjects':null;
      if(groupName){const rect=await geometry(groupName);point={x:rect.x+50,y:rect.y+15};}
      const recentLabels=[...new Set((await ax()).filter(n=>n.role?.value==='StaticText'&&/^(Continue where you left off:)| · (in this browser|on this computer)$/.test(n.name?.value||'')).map(n=>n.name.value))];
      const recentIndex=recentLabels.indexOf(item.node.name?.value);
      const nativeName=(recentIndex>=0?'recentProjects.path.'+recentIndex:null)||names[item.node.name?.value]||(item.node.name?.value?.startsWith('sc-neut-cwl_tb2ti2o7-heidi_fit:')?'examples.open.sc-neut-cwl_tb2ti2o7-heidi_fit':null);
      if(nativeName){const rect=await geometry(nativeName);point={x:rect.x+rect.width/2,y:rect.y+rect.height/2};}
      if(item.node.role?.value==='tab'&&/^(Home|Project|Structure|Experiment|Analysis|Report)$/.test(item.node.name?.value||'')){
        const rect=await geometry('appBar.tab.'+item.node.name.value.toLowerCase());point={x:rect.x+rect.width/2,y:rect.y+rect.height/2};
      }
      console.log(mode,scenario,'pointer',point.x,point.y);
      await page.mouse.move(point.x,point.y);await page.mouse.down();await frame();await page.mouse.up();await frame();
      if(/^(Start|Project|Structure|Experiment|Analysis|Report)$/.test(item.node.name?.value||'')||/(Examples|Recent projects|Get started)$/.test(item.node.name?.value||''))await settle();
    };
    const geometry=async(name)=>{
      console.log(mode,scenario,'geometry',name);
      await page.waitForFunction(name=>{try{const r=window.ediControlGeometry?.(name);return r?.visible&&r.enabled&&r.width>0&&r.height>0;}catch(error){if(/no visible item|no item is named|visible items/.test(error.message))return false;throw error;}},name);
      return evaluate(name=>window.ediControlGeometry(name),name);
    };
    const location=async regex=>{
      const rect=await geometry('project.location');
      const item=await control(regex);
      await writeFile(join(output,scenario+'-location.json'),JSON.stringify({rect,item},null,2));
      // Qt's web AX text boxes retain x=0 after their native row moves; the rendered
      // native rectangle and the unique AX text's row still identify this field.
      assert(item.y>=rect.y&&item.y<=rect.y+rect.height,'The required working-place text is rendered on the actual Project Location row');
    };
    const clean=()=>page.waitForFunction(()=>{try{const r=window.ediControlGeometry?.('appBar.button.save');return r?.visible&&r.enabled===false;}catch{return false;}});
    const edit=async(name,value)=>{
      await settle();await restoreCanvasViewport(expression=>evaluate(expression));const r=await geometry(name);
      await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.mouse.down();await frame();await page.mouse.up();await frame();
      await page.keyboard.press('ControlOrMeta+A');await page.keyboard.type(value);await page.keyboard.press('Tab');await frame();
      const deadline=Date.now()+45000;let observed=false;
      while(Date.now()<deadline){observed=(await ax()).some(n=>n.value?.value===value||n.name?.value===value);if(observed)break;await frame();}
      assert(observed,'The real editor must display the requested input before persistence is tested');
    };
    const activate=async()=>{
      const activation=await control(/(?:activate|enable) screen reader/i,'button');
      const resolved=await cdp.send('DOM.resolveNode',{backendNodeId:activation.node.backendDOMNodeId});
      await cdp.send('Runtime.callFunctionOn',{objectId:resolved.object.objectId,functionDeclaration:'function(){this.click();}'});
      await click(/^Start$/);await click(/^Project$/,'tab');
    };
    const readFiles=async(picked=false)=>{
      const deadline=Date.now()+30000;
      while(true){try{return await page.evaluate(async picked=>{
      const files={};
      const walk=async(folder,prefix='')=>{for await(const [name,handle] of folder.entries()){
        if(!picked&&prefix===''&&['test-picked-output','test-picked-exports'].includes(name))continue;
        if(handle.kind==='directory')await walk(handle,prefix+name+'/');
        else{const bytes=new Uint8Array(await(await handle.getFile()).arrayBuffer());files[prefix+name]=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));}
      }};
      if(picked){await walk(await window.__storageHandles,'selected-folder/');await walk(await window.__storageExportHandles,'selected-exports/');}
      else await walk(await navigator.storage.getDirectory());return files;
    },picked);}catch(error){
        if(!/NotFoundError|NotReadableError/.test(error.message)||Date.now()>=deadline)throw error;
        await frame();
      }}
    };
    const awaitStored=async (name,recovery=false)=>{
      const deadline=Date.now()+30000;
      while(Date.now()<deadline){
        try {
          const files=await readFiles();const prefix=recovery?'edi/recovery/':'edi/projects/';
          return pythonStore(Object.fromEntries(Object.entries(files).filter(([path])=>path.startsWith(prefix))),name);
        }catch(error){if(!/requested saved or recovery state/.test(error.message))throw error;}
        await frame();
      }
      throw Error('Actual browser storage must durably contain '+name);
    };
    const native=async name=>evaluate(name=>{try{return window.ediControlGeometry(name);}catch(error){
      if(/no visible item/.test(error.message))return {visible:false,exists:true};
      if(/no item is named/.test(error.message))return {visible:false,exists:false};throw error;
    }},name);
    const pointer=async name=>{const r=await geometry(name);await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.mouse.down();await frame();await page.mouse.up();await frame();};
    const warning=async(privateStorage=false)=>{
      const text=await native(observation.warningText),icon=await native(observation.warningIcon);
      assert(text.visible,'The first Save into browser storage must show the warning dialog before later short notices');
      assertBrowserWarning(text.text,icon,privateStorage);
      await geometry(observation.warningOk);await geometry(observation.warningSaveAs);
      return {text,icon};
    };
    const formatChoice=async()=>{
      if(boundary)await page.waitForFunction(()=>{try{return window.ediControlGeometry('saveAs.zip').visible;}catch{return window.__downloadBoundary.calls.length>0;}});
      if(!boundary)await geometry('saveAs.zip');
      const zip=await native('saveAs.zip');
      assert(zip.visible,'Fallback Save-as must open edi format dialog before handing any ZIP to the browser');
      if(!fallback){
        assert.equal((await native('saveAs.folder')).enabled,true,'File System Access keeps the Folder format available');
        assert.equal((await native('saveAs.copy')).enabled,true,'File System Access keeps Save-a-copy optional');
      }
      if(fallback){
        if(boundary)assert.equal(await evaluate(()=>window.__downloadBoundary.calls.length),0,'The browser must not be asked to download before edi dialog OK');
        const folder=await native('saveAs.folder'),copy=await native('saveAs.copy');
        await page.mouse.move(folder.x+folder.width/2,folder.y+folder.height/2);
        await page.waitForFunction(name=>{try{return window.ediControlGeometry(name).visible;}catch{return false;}},observation.folderTooltip,{timeout:5000});
        const tooltip=await native(observation.folderTooltip);
        assertFallbackChoices(folder,zip,copy,tooltip.text);
        await click(/^Zip archive$/,'radio');
        // Disabled Save-a-copy is skipped in the real dialog focus order.
        lastDialogControl='saveAs.copy';
      }
      return zip;
    };
    const exportZip=async (label,copy=true)=>{
      const download=fallback?page.waitForEvent('download'):null;download?.catch(()=>{});
      await click(/^Save project as/);
      await formatChoice();
      if(!fallback){await geometry('saveAs.folder');await click(/^Zip archive$/,'radio');if(copy)await click(/^Save a copy/,'checkbox');}
      const previous=fallback?0:await page.evaluate(async()=>{try{return (await(await(await window.__storageExportHandles).getFileHandle('destination.zip')).getFile()).lastModified;}catch{return 0;}});
      await click(/^OK$/,'button');
      const path=join(output,scenario+'-'+label+'.zip');
      if(fallback)await(await download).saveAs(path);
      else {
        const deadline=Date.now()+30000;let encoded;
        while(Date.now()<deadline) {
          encoded=await page.evaluate(async previous=>{try {
            const file=await(await(await window.__storageExportHandles).getFileHandle('destination.zip')).getFile();
            if(!file.size||file.lastModified<=previous)return null;
            const bytes=new Uint8Array(await file.arrayBuffer());
            return btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));
          }catch{return null;}},previous);
          if(encoded)break;await frame();
        }
        assert(encoded,'The accepted Save-as picker must finish writing an actual ZIP file');
        await writeFile(path,Buffer.from(encoded,'base64'));
      }
      const parsed=spawnSync('python',['-c','import base64,json,sys,zipfile\nwith zipfile.ZipFile(sys.argv[1]) as z:\n assert len(z.namelist())==len(set(z.namelist())), "Export has no duplicate members"\n print(json.dumps({n:base64.b64encode(z.read(n)).decode() for n in z.namelist() if not n.endswith("/")}))',path],{encoding:'utf8'});
      assert.equal(parsed.status,0,'The actual Save-as download is independently readable');await settle();return JSON.parse(parsed.stdout);
    };
    try {
    await page.goto(origin+'/?build='+mode);
    await page.waitForFunction(expected=>window.ediBuildInfo?.build===expected&&typeof window.ediControlGeometry==='function',mode);
    assert.equal(await evaluate(()=>window.ediBuildInfo.build),mode,'The actual page runs the requested packed thread kit');
    await activate();
    if(scenario.startsWith('example')){
      // Find the real catalogue row through its actual search field, then real pointer input.
      await click(/Examples$/,'button');await edit('examples.search','sc-neut-cwl_tb2ti2o7-heidi_fit');
      await click(/^sc-neut-cwl_tb2ti2o7-heidi_fit:/,'button');
    } else if(fallback){
      await click(/^Open project(?:…|\.\.\.)?$/);await geometry('open.folder');await click(/^Zip archive$/,'radio');
      const chooser=page.waitForEvent('filechooser');chooser.catch(()=>{});await click(/^OK$/,'button');await(await chooser).setFiles(fixture);
    } else {
      await page.evaluate(async encoded=>{
        const file=await(await window.__storageHandles).getFileHandle('picked.zip',{create:true});const stream=await file.createWritable();await stream.write(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)));await stream.close();
      },(await readFile(fixture)).toString('base64'));
      await click(/^Open project(?:…|\.\.\.)?$/);await geometry('open.folder');
      await click(scenario==='disk-folder'?/^Folder$/:/^Zip archive$/,'radio');await click(/^OK$/,'button');
      if(scenario==='disk-record') {
        const options=await page.evaluate(()=>window.__storageOpenOptions);
        await writeFile(join(output,scenario+'-picker-options.json'),JSON.stringify(options??null,null,2));
        assert(offersProjectRecord(options),'The Chromium Open file route must offer the project.edi record declared by the working-place contract');
      }
    }
    await control(/^Analysis$/,'tab');
    if(scenario==='disk-folder')assert((await page.evaluate(()=>window.__storagePicks.directory))>0,'The disk-folder case actually reaches the directory picker');
    if(scenario==='disk-record'||scenario==='disk-zip')assert((await page.evaluate(()=>window.__storagePicks.open))>0,'Record and ZIP opening actually reach the file-handle picker');
    if(privateStorage) {
      // Opening an example may have reported failed automatic storage. Clear that
      // dialog before attributing anything to this separate Save-as action.
      await settle();await page.keyboard.press('Escape');await frame();
      const storageErrors=[];
      if(scenario==='example-private-save'){
        await evaluate(()=>window.__downloadBoundary.deny());await frame();
        await edit('project.name','private-save-edited');
        await click(/^Save current state of the project$/,'button');
        await page.waitForFunction(()=>window.__downloadBoundary.failures.length>0);
        await frame();
        try{await warning(true);}catch(error){storageErrors.push(error.message);}
        await page.keyboard.press('Escape');await frame();
      }
      await location(/^In this browser only$|^Only in this tab:|^.*\bmemory\b.*$/i);
      const actualLocation=await control(/^In this browser only$|^Only in this tab:|^.*\bmemory\b.*$/i);
      if(!/tab|memory/i.test(actualLocation.node.name?.value||''))storageErrors.push('Unavailable storage must use a plain-words in-memory Location, never In this browser only');
      const beforeStorage=await evaluate(()=>window.__downloadBoundary.storage.slice());
      assert(beforeStorage.length>0,'The private-session scenario must actually exercise throwing storage before Save-as');
      const errors=storageErrors;
      const errorState=()=>evaluate(()=>{
        try{return {observable:true,visible:window.ediControlGeometry('webFiles.error.message').visible};}
        catch(error){if(/no visible item/.test(error.message))return {observable:true,visible:false};
          if(/no item is named/.test(error.message))return {observable:false};throw error;}
      });
      const errorBefore=await errorState();
      if(errorBefore.observable)assert.equal(errorBefore.visible,false,'Any earlier storage error must be dismissed before Save-as is tested');
      await click(/^Save project as/);
      try{await formatChoice();await click(/^OK$/,'button');}catch(error){errors.push(error.message);}
      await page.waitForFunction(()=>window.__downloadBoundary.calls.length>0);
      await frame();await frame();
      const held=await evaluate(()=>({calls:window.__downloadBoundary.calls,storage:window.__downloadBoundary.storage,pending:window.__downloadBoundary.pending.length}));
      assert.equal(held.calls.length,1,'Save-as must reach exactly one real browser download request');
      assert.equal(held.pending,1,'The browser download must remain held before permission or completion');
      assert.equal(events.downloads,0,'No browser download can complete before the held request is released');
      if(JSON.stringify(held.storage)!==JSON.stringify(beforeStorage))errors.push('Save project as touched failing storage');
      const errorAfter=await errorState();
      if(!errorAfter.observable)errors.push('The actual storage-error label is not observable; absence from AX cannot prove the dialog stayed closed');
      else if(errorAfter.visible)errors.push('Save project as displayed a storage error');
      let notice;
      try{notice=await evaluate(()=>window.ediControlGeometry('webNotice.text'));}
      catch(error){if(!/no visible item/.test(error.message))throw error;}
      // A global AX search can mistake an unrelated download icon for this label.
      // A visible notice needs the text of this actual native item; absence is not a pass.
      const text=notice?notice.text:'';
      try{assertPendingNotice(text,false);}catch(error){errors.push(error.message);}
      const shot=await cdp.send('Page.captureScreenshot',{format:'png'});
      await writeFile(join(output,scenario+'-permission-pending.png'),Buffer.from(shot.data,'base64'));
      await writeFile(join(output,scenario+'-permission-pending-ax.json'),JSON.stringify(await cdp.send('Accessibility.getFullAXTree'),null,2));
      // Cancellation proves that even a refused download cannot have been reported as finished.
      await evaluate(()=>window.__downloadBoundary.cancel());await frame();
      assert.equal(events.downloads,0,'Cancelling permission must not create a finished download');
      receipts[scenario]={held,beforeStorage,errorBefore,errorAfter,notice,text,errors,events,browser:'real Chromium',capability:'Throwing OPFS and IndexedDB in main/worker contexts; disk APIs absent; browser anchor held then cancelled'};
      assert.deepEqual(errors,[],'Save-as from an example must bypass failing storage and report only an unconfirmed download request without original-file guidance');
      console.log(mode,scenario,'PASS');continue;
    }
    if(warningScenario){
      await edit('project.name','first-browser-save');
      await click(/^Save current state of the project$/,'button');
      await awaitStored('first-browser-save');await clean();
      const first=await warning(false);
      if(scenario==='example-warning-save-as'){
        const beforeStorage=await evaluate(()=>window.__downloadBoundary.storage.slice());
        await pointer(observation.warningSaveAs);await formatChoice();await click(/^OK$/,'button');
        await page.waitForFunction(()=>window.__downloadBoundary.calls.length>0);await frame();
        assert.deepEqual(await evaluate(()=>window.__downloadBoundary.storage),beforeStorage,'The warning Save-as action must download without another browser-storage save');
        assert.equal(events.downloads,0,'The warning action must leave browser permission pending');
        await evaluate(()=>window.__downloadBoundary.cancel());
        receipts[scenario]={first,events,action:'Save project as from actual first-Save warning'};
        console.log(mode,scenario,'PASS');continue;
      }
      await pointer(observation.warningOk);
      assert.equal((await native(observation.warningText)).visible,false,'OK must close the first-Save browser warning');
      await edit('project.name','later-browser-save');
      await click(/^Save current state of the project$/,'button');
      await awaitStored('later-browser-save');await clean();
      assert.equal((await native(observation.warningText)).visible,false,'A later Save of the same project must use the short notice');
      await geometry(observation.notice);await page.keyboard.press('Escape');await frame();
      const beforeStorage=await evaluate(()=>window.__downloadBoundary.storage.slice());
      await click(/^Save project as/);await formatChoice();await click(/^OK$/,'button');
      await page.waitForFunction(()=>window.__downloadBoundary.calls.length>0);await frame();
      assert.deepEqual(await evaluate(()=>window.__downloadBoundary.storage),beforeStorage,'Fallback Save-as must not save into browser storage even when storage works');
      assert.equal(events.downloads,0,'The healthy-storage fallback also holds browser permission before completion');
      await evaluate(()=>window.__downloadBoundary.cancel());
      receipts[scenario]={first,events,capability:'Real Chromium OPFS, no disk APIs, held/cancelled anchor'};
      console.log(mode,scenario,'PASS');continue;
    }
    const name='browser-saved-'+scenario;
    await edit('project.name',name);
    const before={...events},picksBefore=await page.evaluate(()=>({...window.__storagePicks}));
    await click(/^Save current state of the project$/,'button');
    const browserPlace=scenario.startsWith('example')||fallback;
    let stored;
    if(browserPlace){
      stored=await awaitStored(name);
      await location(/^In this browser only$/);
      // This Qt Popup has no AX node in the shipped kit. Retain actual rendered
      // pixels for the independent notice-text inspection, and gate its visibility.
      await warning(false);
      await settle();
      const notice=await cdp.send('Page.captureScreenshot',{format:'png'});
      await writeFile(join(output,scenario+'-save-notice.png'),Buffer.from(notice.data,'base64'));
      await pointer(observation.warningOk);
    } else {
      const deadline=Date.now()+30000;let candidates=[];
      while(Date.now()<deadline){try{candidates=pythonStore(await readFiles(true),name);break;}catch(error){if(!/requested saved or recovery state/.test(error.message))throw error;}await frame();}
      assert(candidates.length>0,'Chromium ordinary Save writes the opened real file or folder in place');stored=candidates;await location(scenario==='disk-zip'?/^picked\.zip$/:/^test-picked-output$/);
    }
    await clean();
    assert.deepEqual(events,before,'Ordinary Save has no download, file chooser or browser dialog');
    assert.deepEqual(await page.evaluate(()=>window.__storagePicks),picksBefore,'Ordinary Save never asks for another disk location');
    if(fallback){
      assert(stored.some(m=>m['reports/opaque.html']===initial['reports/opaque.html']),'Browser storage keeps exact independently authored report bytes');
    }
    const snapshot=await exportZip('saved');
    await writeFile(join(output,scenario+'-saved-members.json'),JSON.stringify({stored,snapshot},null,2));
    // Save-as canonicalizes generated structure output into project-input spelling.
    // Compare the edited record and carried reports here; compare EVERY canonical
    // scientific member between independent reload and recovery exports below.
    assert(stored.map(logicalMembers).some(m=>
      Object.keys(m).length===Object.keys(snapshot).length&&
      m['project.edi']===logicalMembers(snapshot)['project.edi']&&
      Object.keys(snapshot).every(n=>n in m)&&
      Object.entries(snapshot).filter(([n])=>n.startsWith('reports/')).every(([n,b])=>m[n]===b)),
      'Save-as retains the saved project record, complete member inventory and every carried report byte');
    await page.reload();await activate();
    await click(/Recent projects$/,'button');
    const diskName=scenario==='disk-zip'?'picked.zip':'test-picked-output';
    const diskLabel=new RegExp('^'+diskName.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+' · on this computer$');
    const recent=await control(browserPlace?/ · in this browser$/:diskLabel);
    await click(new RegExp('^'+recent.node.name.value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'));await control(/^Analysis$/,'tab');
    assert.deepEqual(logicalMembers(await exportZip('reopened')),logicalMembers(snapshot),'Reload then Recent projects reopens every saved project and report byte identically');
    const unsaved='browser-unsaved-'+scenario;
    await edit('project.name',unsaved);
    await awaitStored(unsaved,true);
    await page.reload();await activate();await click(/Recent projects$/,'button');
    await click(/^Continue where you left off:/);
    await control(/^Analysis$/,'tab');
    const recovered=await exportZip('recovered');
    assert(Buffer.from(recovered['project.edi'],'base64').toString().includes(unsaved),'Continue where you left off recovers the actual unsaved name after a page reload');
    for(const [member,body] of Object.entries(snapshot))if(member!=='project.edi')assert.equal(recovered[member],body,'Recovery retains every unchanged scientific and report member: '+member);
    if(scenario==='example-folder'||scenario==='example-zip') {
      if(scenario==='example-folder'){
        await click(/^Save project as/);await geometry('saveAs.folder');await click(/^Folder$/,'radio');await click(/^OK$/,'button');
        await location(/^test-picked-output$/);
      } else {await exportZip('becomes-working-place',false);await location(/^destination\.zip$/);}
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
    console.log(mode,scenario,'PASS');
    } catch(error) {
      failures[scenario]={message:error.message,stack:error.stack,picks:await page.evaluate(()=>window.__storagePicks)};console.error(mode,scenario,'FAIL',error.stack);
      await writeFile(join(output,scenario+'-failure-ax.json'),JSON.stringify(await cdp.send('Accessibility.getFullAXTree'),null,2));
      const shot=await cdp.send('Page.captureScreenshot',{format:'png'});await writeFile(join(output,scenario+'-failure.png'),Buffer.from(shot.data,'base64'));
    } finally {await context.close();}

  }
  await writeFile(join(output,'browser-storage.json'),JSON.stringify({mode,receipts,failures},null,2));
  assert.equal(Object.keys(failures).length,0,'Every browser working-place scenario must satisfy durable save, reload, recovery and disk-copy requirements');
} catch(error) {
  if(activeCdp){try{await writeFile(join(output,'failure-ax.json'),JSON.stringify(await activeCdp.send('Accessibility.getFullAXTree'),null,2));const shot=await activeCdp.send('Page.captureScreenshot',{format:'png'});await writeFile(join(output,'failure.png'),Buffer.from(shot.data,'base64'));}catch{}}
  throw error;
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
