import {createServer} from 'node:http';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
import assert from 'node:assert/strict';
const [siteArg,out,chrome,playwright,escape] = process.argv.slice(2);
const {chromium}=await import(playwright),site=resolve(siteArg);
const server=createServer(async(req,res)=>{
 try {
  const path=resolve(site,'.'+new URL(req.url,'http://localhost').pathname);
  assert(path.startsWith(site+sep),'Selector observations must use only the qualified app build');
  const bytes=await readFile(path);
  res.writeHead(200,{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp',
   'Content-Type':({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm'})[extname(path)]||'application/octet-stream'});
  res.end(bytes);
 } catch {res.writeHead(404);res.end();}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const results={};
try {
 for(const count of (escape?[3]:[0,1,3,9,'restore'])) {
  const context=await browser.newContext({viewport:{width:1280,height:768}}),page=await context.newPage();
  const origin=`http://127.0.0.1:${server.address().port}/edi_app.html`;
  const invoke=async(choice)=>{
   const control=choice==='read'||escape!=='ignored-persistence'?escape:'';
   await page.goto(`${origin}?THREAD_SELECTOR_COUNT=${choice}&THREAD_SELECTOR_ESCAPE=${control||''}`);
   await page.waitForFunction(()=>!!window.__threadSelectorObservation,undefined,{timeout:150000});
   return await page.evaluate(()=>window.__threadSelectorObservation);
  };
  results[count]={selected:await invoke(String(count)),reopened:await invoke('read')};
  await context.close();
 }
 await writeFile(out,JSON.stringify({backend:'browser',isolated:true,preallocated:8,results},null,2));
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
