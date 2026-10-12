import {createServer} from 'node:http';
import {readFile, writeFile} from 'node:fs/promises';
import {resolve, extname, sep} from 'node:path';
import assert from 'node:assert/strict';
const [siteArg, out, chrome, playwright] = process.argv.slice(2);
const {chromium} = await import(playwright);
const site = resolve(siteArg);
const server = createServer(async (req, res) => {
  try {
    const path = resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    assert(path.startsWith(site + sep), 'The observation server serves only the qualified browser build');
    const bytes = await readFile(path);
    res.writeHead(200, {'Cross-Origin-Opener-Policy':'same-origin', 'Cross-Origin-Embedder-Policy':'require-corp',
      'Content-Type': ({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm'})[extname(path)] || 'application/octet-stream'});
    res.end(bytes);
  } catch {res.writeHead(404); res.end();}
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await chromium.launch({executablePath:chrome, headless:true, args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const results = {};
try {
  for (const mode of ['adaptive','every','second','end']) {
    const context = await browser.newContext({viewport:{width:1280,height:768}});
    const page = await context.newPage();
    const origin = `http://127.0.0.1:${server.address().port}/edi_app.html`;
    const observe = async (choice, settingsOnly) => {
      await page.goto(`${origin}?SCAN_SCREEN_MODE=${choice}&SCAN_SCREEN_SETTINGS_ONLY=${settingsOnly?1:0}`);
      await page.waitForFunction(() => !!window.__scanScreenObservation, undefined, {timeout:150000});
      return await page.evaluate(() => window.__scanScreenObservation);
    };
    results[mode] = await observe(mode, false);
    results[mode].saved = await observe(mode, true);
    results[mode].reopened = await observe('read', true);
    await page.screenshot({path:out + '-' + mode + '.png'});
    await context.close();
  }
  await writeFile(out, JSON.stringify({backend:'browser', isolated:true, results}, null, 2));
} finally {
  await browser.close();
  await new Promise(ok => server.close(ok));
}
