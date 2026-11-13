// Exercise the shipped loader's policy with offline browser/network transports.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
const html=await readFile(process.argv[2] || new URL('../../../app/web/index.html',import.meta.url),'utf8');
const source=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('async function chooseBuild('));
assert(source,'The actual delivered page owns the build selection procedure');
const entry=source.lastIndexOf('start().catch');
assert(entry>0,'The actual loader retains its error-reporting entrypoint');
function host(options={}) {
  const scripts=[],requests=[],timers=[],cleared=[],storage=new Map();
  let reloads=0,qtCalls=0;
  const nodes=Object.fromEntries(['status','splash','still','loading','screen'].map(name=>[name,{style:{},textContent:''}]));
  const context={URLSearchParams,console:{log(){},error(){}},WebAssembly,
    SharedArrayBuffer:options.shared===false?undefined:SharedArrayBuffer,
    crossOriginIsolated:options.isolated!==false,isSecureContext:options.secure!==false,
    location:{search:options.search||'',reload(){++reloads;}},
    sessionStorage:{getItem:key=>{if(options.storageFailure==='get')throw Error('storage denied');return storage.get(key)||null;},
      setItem:(key,value)=>{if(options.storageFailure==='set')throw Error('storage denied');storage.set(key,value);},
      removeItem:key=>{if(options.storageFailure==='remove')throw Error('storage denied');storage.delete(key);}},
    navigator:{serviceWorker:{register:async()=>{if(options.registrationFailure)throw Error('denied');if(options.registerPending)await new Promise(()=>{});},
      ready:options.pending?new Promise(()=>{}):Promise.resolve()}},
    addEventListener(){},
    document:{documentElement:{dataset:{}},getElementById:name=>nodes[name],
      createElement:()=>({}),body:{appendChild(script){scripts.push(script.src);options.scriptFailure?script.onerror():script.onload();}}},
    setTimeout(callback,ms){const token={callback,ms};timers.push(token);return token;},
    clearTimeout:token=>cleared.push(token),
    fetch:async url=>{requests.push(url);return url==='build.json'?{ok:true,json:async()=>options.manifest??{multithread:'multithread-a1b2'}}:
      new Response(new Uint8Array([0,97,115,109,1,0,0,0]),{headers:{'Content-Type':'application/wasm'}});},
    qtLoad:async config=>{++qtCalls;await config.qt.module;config.qt.onLoaded();},
  };
  if(options.noWorker)context.navigator.serviceWorker=undefined;
  if(options.noStorage)Object.defineProperty(context,'sessionStorage',{get(){throw Error('blocked');}});
  if(options.reloaded)storage.set('edi.coi-reloaded','multithread-a1b2');
  context.window=context;context.self=context;
  runInNewContext(source.slice(0,entry)+'globalThis.loader={chooseBuild,start};',context);
  return {context,storage,scripts,requests,timers,cleared,nodes,stats:()=>({reloads,qtCalls})};
}
for(const search of ['', '?build=multithread']) {
 const h=host({search});const result=await h.context.loader.chooseBuild('multithread-a1b2');
 assert.equal(result.build,'multithread','The sole supported request selects the isolated threaded kit');
 assert.equal(h.stats().reloads,0,'An already isolated host does not reload or fall back');
 await h.context.loader.start();
 assert.deepEqual(h.scripts,['multithread-a1b2/qtloader.js','multithread-a1b2/edi_app.js'],
   'The loader requests only the declared content-addressed threaded scripts');
 assert.equal(h.stats().qtCalls,1,'The supported startup reaches its Qt transport once');
}
for(const storageFailure of ['get','remove','set']) {
 const h=host({storageFailure});await h.context.loader.start();
 assert.equal(h.stats().qtCalls,1,'Direct header isolation does not require successful optional storage methods');
 assert.equal(h.stats().reloads,0,'Broken optional storage cannot redirect an already isolated app');
}
for(const [options,reason] of [
 [{search:'?build=singlethread'},/multithreaded build/],
 [{search:'?build=unknown'},/multithreaded build/],
 [{search:'?build=multithread',isolated:false,noWorker:true},/cross-origin isolation/],
 [{isolated:false,secure:false},/HTTPS|secure/],
 [{shared:false},/shared memory/],
 [{isolated:false,noWorker:true},/cross-origin isolation/],
 [{isolated:false,noStorage:true},/session storage/],
 [{isolated:false,storageFailure:'get'},/session storage/],
 [{isolated:false,storageFailure:'remove'},/session storage/],
 [{isolated:false,storageFailure:'set'},/could not be enabled/],
 [{isolated:false,reloaded:true},/still unavailable/],
 [{isolated:false,registrationFailure:true},/could not be enabled/],
]) {
 const h=host(options);await assert.rejects(h.context.loader.start(),reason,
   'Unsupported targets or unavailable isolation refuse before any app script');
 assert.equal(h.scripts.length,0,'Refused startup cannot load an alternate kit');
 assert.equal(h.stats().reloads,0,'Refused startup cannot navigate to a fallback kit');
}
{
 const h=host({isolated:false});
 assert.equal(await h.context.loader.chooseBuild('multithread-a1b2'),null,
   'A newly enabled service worker requests navigation before app startup');
 assert.equal(h.stats().reloads,1,'Service-worker setup requests exactly one real reload');
 assert.equal(h.storage.get('edi.coi-reloaded'),'multithread-a1b2',
   'The reload marker binds the exact declared kit');
}
for(const stalled of ['registerPending','pending']) {
 const h=host({isolated:false,[stalled]:true});const pending=h.context.loader.chooseBuild('multithread-a1b2');
 await new Promise(setImmediate);
 assert.equal(h.timers.length,1,'A stalled service-worker activation has one owned deadline');
 assert.equal(h.timers[0].ms,15000,'The existing activation bound remains fifteen seconds');
 h.timers[0].callback();
 await assert.rejects(pending,/timed out/,'Neither registration nor readiness can leave startup pending indefinitely');
 assert(h.cleared.includes(h.timers[0]),'The activation timer is cleared after refusal');
}
for(const manifest of [{},{singlethread:'singlethread-abcd'},{multithread:4},
 {multithread:'../escape'},{multithread:'singlethread-abcd'},{multithread:'multithread-'},
 {multithread:'https://outside.invalid/multithread-abcd'}]) {
 const h=host({manifest});await assert.rejects(h.context.loader.start(),/names no multithread/,
   'Missing, retired, malformed and escaping kit paths refuse before script loading');
 assert.equal(h.scripts.length,0,'An invalid manifest cannot select arbitrary executable script');
}
{
 const h=host({scriptFailure:true});await assert.rejects(h.context.loader.start(),/cannot load/,
   'A broken threaded script remains a startup failure');
 assert.equal(h.scripts.length,1,'Script failure cannot attempt a serial fallback');
 assert.equal(h.stats().reloads,0,'A failed threaded script cannot redirect to another build');
}
console.log('Sole-kit loader, direct/shim setup, bounded activation and refusal controls passed; no Qt engine execution claimed');
