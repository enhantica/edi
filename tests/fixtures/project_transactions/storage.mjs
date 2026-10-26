// Execute the shipped storage script with real Chromium handles, independent of Qt rendering.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
const [root,input,output,chrome]=process.argv.slice(2);
assert(root&&input&&output&&chrome,'Storage observations require source, independent files, output and pinned Chromium');
const source=await readFile(join(root,'app/src/web_storage.cpp'),'utf8');
const bodies={};
for(const name of ['edi_storage_install','edi_storage_pick_save','edi_storage_write']) {
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
 const result=await page.evaluate(async({bodies,files})=>{
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
   return {picked,written,actual};
 },{bodies,files});
 await writeFile(output,JSON.stringify(result,null,2));
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
