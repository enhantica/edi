// Actual Chromium must show startup refusal before requesting an incompatible kit.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,join,sep,extname} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

export async function multithreadStartupRefusals(chrome,siteArg,outputArg) {
  const site=resolve(siteArg),output=resolve(outputArg);
  await mkdir(output,{recursive:true});
  const toolchain=process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME,'.cache/edi-wasm');
  const {chromium}=await import(pathToFileURL(join(toolchain,'playwright/node_modules/playwright-core/index.mjs')));
  const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
  const records=[];
  try {
    for(const test of [
      {name:'removed-build',query:'?build=singlethread',headers:true,reason:/multithreaded build/i},
      {name:'non-isolated',noWorker:true,reason:/cross-origin isolation/i},
      {name:'no-shared-memory',headers:true,noShared:true,reason:/shared memory/i},
      {name:'retired-manifest',headers:true,manifest:{singlethread:'singlethread-abcd'},reason:/names no multithread/i},
    ]) {
      const requests=[],errors=[];
      const server=createServer(async(req,res)=>{
        try {
          const pathname=new URL(req.url,'http://localhost').pathname;
          const headers=test.headers?{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'}:{};
          if(pathname==='/build.json'&&test.manifest){res.writeHead(200,{...headers,'Content-Type':'application/json'});res.end(JSON.stringify(test.manifest));return;}
          const file=resolve(site,'.'+(pathname==='/'?'/index.html':pathname));
          assert(file.startsWith(site+sep),'The refusal host serves only its declared site');
          const bytes=await readFile(file);
          res.writeHead(200,{...headers,'Content-Type':({'.html':'text/html','.js':'text/javascript','.json':'application/json','.wasm':'application/wasm'})[extname(file)]||'application/octet-stream'});res.end(bytes);
        }catch{res.writeHead(404);res.end();}
      });
      await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
      const context=await browser.newContext({serviceWorkers:'block'});
      try {
        await context.addInitScript(({noWorker,noShared})=>{
          if(noWorker)Object.defineProperty(navigator,'serviceWorker',{value:undefined});
          if(noShared)Object.defineProperty(window,'SharedArrayBuffer',{value:undefined});
        },{noWorker:test.noWorker,noShared:test.noShared});
        const page=await context.newPage();
        page.on('request',request=>requests.push(new URL(request.url()).pathname));
        page.on('pageerror',error=>errors.push(error.message));
        await page.goto(`http://127.0.0.1:${server.address().port}/${test.query||''}`);
        await page.waitForFunction(()=>document.getElementById('status')?.textContent.includes('could not start'),null,{timeout:5000});
        const actual=await page.evaluate(()=>({message:document.getElementById('status').textContent,
          isolated:crossOriginIsolated,shared:typeof SharedArrayBuffer==='function',screen:document.getElementById('screen').style.display}));
        assert.match(actual.message,test.reason,'The real page explains why its supported threaded kit cannot start');
        assert.notEqual(actual.screen,'block','Refused startup cannot display a pretend initialized app');
        assert(!requests.some(path=>/\/(?:multi|single)thread[^/]*\/(?:edi_app|qtloader)\./.test(path)),
          'Refused startup must not request any application module or alternate kit');
        assert.equal(errors.length,0,'Startup refusal is handled visibly rather than an uncaught page error');
        records.push({case:test.name,...actual,requests,errors});
      }finally{await context.close();server.closeAllConnections();await new Promise(ok=>server.close(ok));}
    }
    await writeFile(join(output,'multithread-startup-refusals.json'),JSON.stringify({browser:browser.version(),records},null,2));
    return records;
  }finally{await browser.close();}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  await multithreadStartupRefusals(process.argv[4],process.argv[2],process.argv[3]);
}
