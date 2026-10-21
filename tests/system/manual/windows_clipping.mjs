import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const require = createRequire(new URL('../../fixtures/web_parallel/package.json', import.meta.url));
const {chromium} = require('playwright-core');
const [origin, output] = process.argv.slice(2);
assert.equal(process.platform, 'win32', 'The web clipping acceptance must run in a Windows browser');
assert(origin && output && process.env.EDI_BROWSER, 'The actor needs the delivered site, evidence directory and Windows browser');
await mkdir(output, {recursive:true});
const browser = await chromium.launch({executablePath:process.env.EDI_BROWSER, headless:false});
try {
  const page = await browser.newPage({viewport:{width:1280,height:900}, deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror', error=>errors.push(String(error)));
  const receipts=[];
  for (const mode of ['singlethread','multithread']) {
    await page.goto(`${origin}/?mode=${mode}&acceptance=clipping`);
    await page.waitForFunction(()=>typeof window.ediControlGeometry === 'function');
    assert.equal(await page.evaluate(()=>typeof window.ediClippingAcceptance), 'function',
      'The real web build must load its preset host before Windows pixel evidence can count');
    const gpu = await page.evaluate(()=>{
      const gl=document.createElement('canvas').getContext('webgl2');
      if(!gl) throw Error('The Windows rendering control requires WebGL2');
      const ext=gl.getExtension('WEBGL_debug_renderer_info');
      return {vendor:gl.getParameter(ext ? ext.UNMASKED_VENDOR_WEBGL : gl.VENDOR),
        renderer:gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER)};
    });
    for(const theme of ['light','dark'])
      for(const scenario of ['rows','antialiased-border','outer-off','both-clips','layer','cover',
        'structure-table','experiment-table','analysis-table','sidebar-collapse','popup-close']) {
        // The host changes real QML items and returns their native clip rectangle.
        const facts=await page.evaluate(args=>window.ediClippingAcceptance(...args), [scenario,theme,'prepare']);
        assert(facts && ['x','y','width','height'].every(key=>Number.isFinite(facts.clip[key])) && facts.clip.width>0 && facts.clip.height>0,
          'The pixel check needs the native visible clip rectangle, not an assumed DOM box');
        const before=await page.screenshot({path:resolve(output,`${mode}-${theme}-${scenario}-before.png`)});
        const target=facts.action;
        assert(target && Number.isFinite(target.x) && Number.isFinite(target.y), 'A real scenario supplies a trusted pointer target');
        await page.mouse.click(target.x,target.y);
        await page.evaluate(()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))));
        const after=await page.screenshot({path:resolve(output,`${mode}-${theme}-${scenario}-after.png`)});
        const pixels=await page.evaluate(async ({before,after,clip})=>{
          async function read(encoded) {
            const picture=new Image(); picture.src='data:image/png;base64,'+encoded; await picture.decode();
            const canvas=new OffscreenCanvas(picture.width,picture.height), ctx=canvas.getContext('2d');
            ctx.drawImage(picture,0,0); return {width:picture.width,height:picture.height,data:ctx.getImageData(0,0,picture.width,picture.height).data};
          }
          const a=await read(before), b=await read(after); let inside=0,outside=0;
          for(let y=Math.max(0,Math.floor(clip.y)-8);y<Math.min(a.height,Math.ceil(clip.y+clip.height)+8);y++)
            for(let x=Math.max(0,Math.floor(clip.x)-8);x<Math.min(a.width,Math.ceil(clip.x+clip.width)+8);x++) {
              const at=4*(y*a.width+x);
              const changed=[0,1,2,3].some(c=>a.data[at+c]!==b.data[at+c]);
              if(!changed) continue;
              if(x>=clip.x && x<clip.x+clip.width && y>=clip.y && y<clip.y+clip.height) inside++; else outside++;
            }
          return {inside,outside};
        }, {before:before.toString('base64'),after:after.toString('base64'),clip:facts.clip});
        assert(pixels.inside>0, 'The real action must change pixels inside its clip; an empty scene cannot pass');
        if(scenario==='outer-off') assert(pixels.outside>0, 'Disabling clipping must reach the outside-pixel escape control');
        else assert.equal(pixels.outside,0, 'Hidden content must never change any pixel outside its native clip rectangle');
        receipts.push({mode,theme,scenario,gpu,pixels,geometry:facts});
      }
  }
  assert.deepEqual(errors, [], 'A clipping result cannot hide browser errors');
  await writeFile(resolve(output,'receipt.json'),JSON.stringify({browser:await browser.version(),receipts},null,2)+'\n');
} finally { await browser.close(); }
