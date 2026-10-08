// Run the owner's Safari load sequence on the shipped site with the pinned WebKit engine.
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join,sep,extname} from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';

const [siteArg,outputArg,moduleArg] = process.argv.slice(2);
assert(siteArg&&outputArg,'WebKit route acceptance requires the shipped site and persistent evidence');
const moduleUrl=moduleArg?pathToFileURL(resolve(moduleArg)):new URL('../../fixtures/web_parallel/node_modules/playwright-core/index.mjs',import.meta.url);
const packageInfo=JSON.parse(await readFile(new URL('./package.json',moduleUrl)));
assert(packageInfo.name==='playwright-core'&&packageInfo.version==='1.48.2',
 'WebKit acceptance must use the locked browser driver version');
const {webkit}=await import(moduleUrl.href);
const site=resolve(siteArg),output=resolve(outputArg);
await readFile(join(site,'index.html'));
await mkdir(output,{recursive:true});
const contract=JSON.parse(await readFile(new URL('../../fixtures/web_parallel/contract.json',import.meta.url)));
const mime={'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'};
const results=[];
let failures=0;
for(const mode of ['singlethread','multithread','shim']) {
 const headers=mode==='multithread'?{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'}:{};
 const server=createServer(async(req,res)=>{
  try {
   const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\/webapp(?=\/)/,'');
   if(mode==='singlethread'&&pathname.endsWith('/coi-serviceworker.js')){res.writeHead(404);res.end();return;}
   const file=resolve(site,'.'+pathname+(pathname.endsWith('/')?'index.html':''));
   assert(file.startsWith(site+sep),'WebKit route server must stay inside the shipped site');
   const bytes=await readFile(file);
   res.writeHead(200,{...headers,'Content-Type':mime[extname(file)]||'application/octet-stream'});res.end(bytes);
  } catch {res.writeHead(404);res.end();}
 });
 await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
 const url=`http://127.0.0.1:${server.address().port}/webapp/`;
 let browser;
 try {
  browser=await webkit.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1280,height:768}});
  const watched=new WeakMap();
  const observe=page=>{
   const state={wasm:[],documents:[],errors:[],console:[]};watched.set(page,state);
   page.on('request',request=>{if(new URL(request.url()).pathname.endsWith('.wasm'))state.wasm.push(request.url());});
   page.on('response',async response=>{
    if(response.request().isNavigationRequest()&&response.request().frame()===page.mainFrame())
     state.documents.push({url:response.url(),headers:await response.allHeaders()});
   });
   page.on('pageerror',error=>state.errors.push(error.message));
   page.on('console',message=>{state.console.push(message.text());if(state.console.length>20)state.console.shift();});
  };
  const navigate=async(page,label,reload=false)=>{
   const state=watched.get(page);state.wasm=[];state.documents=[];state.errors=[];state.console=[];
   console.log(`WebKit ${mode}: ${label} starts`);
   try {
    await page.bringToFront();
    if(reload)await page.reload({waitUntil:'domcontentloaded'});
    else await page.goto(url,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>{
     if(!document.documentElement.dataset.build||document.getElementById('screen')?.style.display!=='block')return false;
     const roots=[document];
     for(let i=0;i<roots.length;i++)for(const element of roots[i].querySelectorAll('*')) {
      if(element.shadowRoot)roots.push(element.shadowRoot);
      if(element.tagName==='CANVAS'&&element.width>100&&element.height>100&&element.getBoundingClientRect().width>100)return true;
     }
     return false;
    },null,{timeout:180000,polling:250});
    const actual=await page.evaluate(()=>({kit:document.documentElement.dataset.build,
     isolated:crossOriginIsolated,sharedArrayBuffer:typeof SharedArrayBuffer==='function',
     controlled:!!navigator.serviceWorker?.controller,coreCount:navigator.hardwareConcurrency,
     reason:window.ediBuildInfo?.reason,userAgent:navigator.userAgent}));
    const record={mode,label,browser:browser.version(),...actual,...state};results.push(record);
    const expected=contract.routes[mode];
    assert(/AppleWebKit/.test(actual.userAgent)&&!/Chrome|Chromium/.test(actual.userAgent),
     'Safari route regression acceptance must execute WebKit rather than substitute a Chromium engine');
    assert.equal(actual.kit,expected.kit,'WebKit must retain the shipped kit after reload and second navigation');
    assert.equal(actual.isolated,expected.isolated,'WebKit must retain the route isolation state on every navigation');
    assert.equal(actual.sharedArrayBuffer,expected.shared_array_buffer,'WebKit must retain shared memory availability on every navigation');
    assert(state.wasm.length&&state.wasm.every(name=>name.replaceAll(/[-_]/g,'').includes(expected.kit)),
     'Every WebKit load must request the actual expected wasm kit, including cache-backed reloads');
    if(mode==='shim') {
     assert(actual.controlled,'The WebKit shim must be controlled by its real service worker');
     assert(state.documents.some(item=>item.headers['cross-origin-embedder-policy']==='require-corp'),
      'The controlled WebKit navigation must receive COEP require-corp rather than unsupported credentialless');
    }
    assert.equal(state.errors.length,0,'A WebKit route may not pass with uncaught runtime exceptions');
    console.log(JSON.stringify(record));
   } catch(error) {
    const readiness=await page.evaluate(()=>({kit:document.documentElement.dataset.build,
     screen:document.getElementById('screen')?.style.display,
     canvas:[...document.querySelectorAll('*')].filter(element=>element.shadowRoot)
      .flatMap(element=>[...element.shadowRoot.querySelectorAll('canvas')])
      .map(element=>({width:element.width,height:element.height,visibleWidth:element.getBoundingClientRect().width}))})).catch(()=>null);
    failures++;results.push({mode,label,error:error.message,readiness,...state});
    console.error(`${mode} ${label}: ${error.message}`);
   } finally {
    await writeFile(join(output,'webkit-routes.json'),JSON.stringify(results,null,2));
   }
  };
  const first=await context.newPage();observe(first);
  await navigate(first,'initial');
  await navigate(first,'reload',true);
  await first.close();
  const second=await context.newPage();observe(second);
  await navigate(second,'second-navigation');
  await navigate(second,'second-navigation-reload',true);
 } finally {await browser?.close();await new Promise(ok=>server.close(ok));}
}
assert.equal(failures,0,'All three WebKit routes must preserve their actual kit and isolation through the owner reload sequence');
