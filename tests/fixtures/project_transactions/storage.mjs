// Execute the shipped storage script with real Chromium handles, independent of Qt rendering.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
const [root,input,output,chrome,scenario='population']=process.argv.slice(2);
assert(root&&input&&output&&chrome,'Storage observations require source, independent files, output and pinned Chromium');
const source=await readFile(join(root,'app/src/web_storage.cpp'),'utf8');
const bodies={};
for(const name of ['edi_storage_install','edi_storage_pick_save','edi_storage_write','edi_storage_drop']) {
  const match=source.match(new RegExp('EM_JS\\([^,]+,\\s*'+name+',\\s*\\([^]*?\\), \\{([^]*?)\\n\\}\\);'));
  assert(match,'The storage observer must execute each actual production entry point');bodies[name]=match[1];
}
const toolchain=process.env.EDI_WASM_TOOLCHAIN||join(process.env.HOME,'.cache/edi-wasm');
const {chromium}=await import(join(toolchain,'playwright/node_modules/playwright-core/index.mjs'));
const server=createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/html'});res.end('<!doctype html><title>Storage boundary</title>');});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const browser=await chromium.launch({executablePath:chrome,args:['--no-sandbox'],headless:true});
try {
 const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port);
 const files=JSON.parse(await readFile(input,'utf8'));
 const result=await page.evaluate(async({bodies,files,scenario})=>{
   const root=await navigator.storage.getDirectory();const chosen=await root.getDirectoryHandle('existing-project',{create:true});
   const bytes=text=>Uint8Array.from(atob(text),c=>c.charCodeAt(0));
   const write=async(name,body)=>{const parts=name.split('/');let parent=chosen;for(const part of parts.slice(0,-1))parent=await parent.getDirectoryHandle(part,{create:true});const stream=await(await parent.getFileHandle(parts.at(-1),{create:true})).createWritable();await stream.write(body);await stream.close();};
   for(const [name,body] of Object.entries(files))await write(name,bytes(body));
   const structure=Object.keys(files).find(name=>name.startsWith('structures/'));
   const experiment=Object.keys(files).find(name=>name.startsWith('experiments/'));
   if(!structure||!experiment)throw Error('The source must contain both entity families');
   await write('structures/obsolete.edi',bytes(files[structure]));
   await write('experiments/obsolete.edi',bytes(files[experiment]));
   await write('keep.txt','independent unrelated content');await write('photos/keep.txt','independent nested content');
   const answers=new Map(),pending=new Map();
   const Module={_edi_storage_answered:(job,text)=>{const value=JSON.parse(text);answers.set(job,value);pending.get(job)?.(value);}};
   const UTF8ToString=value=>value,stringToNewUTF8=value=>value;
   const FS={};
   window.showDirectoryPicker=async()=>chosen;window.showSaveFilePicker=async()=>{};window.showOpenFilePicker=async()=>{};
   new Function('FS','Module','UTF8ToString','stringToNewUTF8',bodies.edi_storage_install)(FS,Module,UTF8ToString,stringToNewUTF8);
   const invoke=(name,args)=>new Function('FS','Module','UTF8ToString','stringToNewUTF8',...args.map(([key])=>key),bodies[name])(FS,Module,UTF8ToString,stringToNewUTF8,...args.map(([,value])=>value));
   const answer=job=>answers.has(job)?Promise.resolve(answers.get(job)):new Promise(ok=>pending.set(job,ok));
   // Both moving Save as and Save a copy use this identical production boundary.
   invoke('edi_storage_pick_save',[['job',1],['kind_utf8','folder'],['suggested_utf8','source'],['start_utf8','']]);
   const picked=await answer(1);if(!picked.ok)throw Error(JSON.stringify(picked));
   const handle=ediStorage.handles.get(picked.key);
   // OPFS handles lack permission methods on some Chromium versions; this is the user's granted picker permission.
   for(const name of ['queryPermission','requestPermission'])if(typeof handle[name]!=='function')Object.defineProperty(handle,name,{value:async()=> 'granted'});
   ediStorage.staged.set(2,Object.entries(files).map(([name,body])=>[name,bytes(body)]));
   invoke('edi_storage_write',[['job',2],['key_utf8',picked.key],['kind_utf8','folder'],['name_utf8',picked.name],['recovery',0]]);
   const written=await answer(2);const actual={};
   for(const [name,handle] of await ediStorage.walk(chosen,'',[]))actual[name]=btoa(String.fromCharCode(...new Uint8Array(await(await handle.getFile()).arrayBuffer())));
   const cleanup=[];let nextJob=100;
   const faultSpecs=[];
   if(scenario.startsWith('cleanup'))for(const category of ['structures','experiments']) {
     for(const error of ['NotAllowedError','NoModificationAllowedError','UnknownError','Error','NotFoundError'])faultSpecs.push({stage:'remove',category,error});
     for(const stage of ['lookup','list'])for(const error of ['NotAllowedError','UnknownError'])faultSpecs.push({stage,category,error});
   }
   for(const spec of faultSpecs.filter(s=>scenario==='cleanup'||scenario===`cleanup:${s.stage}:${s.category}:${s.error}`)) {
     const destination=await root.getDirectoryHandle('cleanup-'+nextJob,{create:true});
     const put=async(path,body)=>{let parent=destination;const parts=path.split('/');for(const part of parts.slice(0,-1))parent=await parent.getDirectoryHandle(part,{create:true});const stream=await(await parent.getFileHandle(parts.at(-1),{create:true})).createWritable();await stream.write(body);await stream.close();};
     for(const [path,body] of Object.entries(files))await put(path,bytes(body));
     await put('structures/obsolete.edi',bytes(files[structure]));await put('experiments/obsolete.edi',bytes(files[experiment]));await put('keep.txt','independent unrelated content');
     const categoryHandle=await destination.getDirectoryHandle(spec.category);
     const originalGet=destination.getDirectoryHandle.bind(destination),originalRemove=categoryHandle.removeEntry.bind(categoryHandle),originalEntries=categoryHandle.entries.bind(categoryHandle);
     let failing=spec.stage!=='remove',attempts=0;
     const fault=()=>{++attempts;throw spec.error==='Error'?new Error('independent cleanup refusal'):new DOMException('independent cleanup refusal',spec.error);};
     Object.defineProperty(destination,'getDirectoryHandle',{value:async(name,options)=>{
       if(name!==spec.category)return originalGet(name,options);
       if(failing&&spec.stage==='lookup'&&!options?.create)fault();
       return categoryHandle;
     }});
     Object.defineProperty(categoryHandle,'entries',{value:async function*(){if(failing&&spec.stage==='list')fault();yield* originalEntries();}});
     Object.defineProperty(categoryHandle,'removeEntry',{value:async(name,options)=>{if(name==='obsolete.edi'){++attempts;if(failing)throw spec.error==='Error'?new Error('independent cleanup refusal'):new DOMException('independent cleanup refusal',spec.error);}return originalRemove(name,options);}});
     for(const name of ['queryPermission','requestPermission'])if(typeof destination[name]!=='function')Object.defineProperty(destination,name,{value:async()=> 'granted'});
     window.showDirectoryPicker=async()=>destination;
     const pick=async()=>{const job=nextJob++;invoke('edi_storage_pick_save',[['job',job],['kind_utf8','folder'],['suggested_utf8','source'],['start_utf8','']]);return answer(job);};
     const writePicked=async picked=>{const job=nextJob++;ediStorage.staged.set(job,Object.entries(files).map(([name,body])=>[name,bytes(body)]));invoke('edi_storage_write',[['job',job],['key_utf8',picked.key],['kind_utf8','folder'],['name_utf8',picked.name],['recovery',0]]);return answer(job);};
     const firstPick=await pick();const knownBefore=firstPick.ok?[...ediStorage.loaded.get(firstPick.key)||[]].sort():null;
     if(spec.stage==='remove') {
       if(spec.error==='NotFoundError')await originalRemove('obsolete.edi');
       failing=true;
     }
     const first=firstPick.ok?await writePicked(firstPick):firstPick;
     const knownAfter=firstPick.ok?[...ediStorage.loaded.get(firstPick.key)||[]].sort():null;
     const recordAfter=firstPick.ok?await ediStorage.record(firstPick.key):null;
     const attemptsBeforeRetry=attempts;failing=false;
     const retryPick=firstPick.ok?firstPick:await pick();const retry=retryPick.ok?await writePicked(retryPick):retryPick;
     const members=(await ediStorage.walk(destination,'',[])).map(([name])=>name).sort();
     cleanup.push({...spec,firstPick,first,retry,knownBefore,knownAfter,recordAfter:recordAfter??null,attemptsBeforeRetry,attemptsAfterRetry:attempts,members,knownAfterRetry:[...ediStorage.loaded.get(retryPick.key)||[]].sort()});
   }
   // Hold the worker boundary with immediate fake metadata/directory operations.
   // The real production write/drop entry points still own their causal ordering.
   let releaseWrite, announceHeld, recoveryPresent=true;
   const held=new Promise(ok=>announceHeld=ok), gate=new Promise(ok=>releaseWrite=ok);
   ediStorage.record=async key=>({key,saved:true,kind:'browser',name:'held'});
   ediStorage.put=async()=>{};ediStorage.remove=async()=>{};
   ediStorage.opfs=async()=>({removeEntry:async()=>{recoveryPresent=false;}});
   ediStorage.writeBrowser=async()=>{announceHeld();await gate;recoveryPresent=true;};
   ediStorage.staged.set(10,[['project.edi',new Uint8Array([1])]]);
   invoke('edi_storage_write',[['job',10],['key_utf8','held-recovery'],['kind_utf8','browser'],['name_utf8','held'],['recovery',1]]);
   await held;
   invoke('edi_storage_drop',[['job',11],['key_utf8','held-recovery'],['whole',0]]);
   await new Promise(ok=>requestAnimationFrame(ok));
   const discardedBeforeWriteSettled=answers.has(11);
   releaseWrite();await Promise.all([answer(10),answer(11)]);
   return {picked,written,actual,cleanup,recoveryRace:{discardedBeforeWriteSettled,recoveryPresent}};
 },{bodies,files,scenario});
 await writeFile(output,JSON.stringify(result,null,2));
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
