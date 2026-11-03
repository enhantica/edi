import {createServer} from 'node:http';
import {readFile, writeFile} from 'node:fs/promises';
import {resolve, extname, sep} from 'node:path';
import assert from 'node:assert/strict';
const [siteArg, output, chrome, playwright, inventory] = process.argv.slice(2);
const {chromium} = await import(playwright);
const site = resolve(siteArg);
const server = createServer(async (req, res) => {
  try {
    const path = resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    assert(path.startsWith(site + sep), 'The font server serves only its sealed browser build');
    const bytes = await readFile(path);
    res.writeHead(200, {'Cross-Origin-Opener-Policy':'same-origin', 'Cross-Origin-Embedder-Policy':'require-corp',
      'Content-Type': ({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm'})[extname(path)] || 'application/octet-stream'});
    res.end(bytes);
  } catch (error) { console.error(String(error)); res.writeHead(404); res.end(); }
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await chromium.launch({executablePath:chrome, headless:true,
  args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
  const result = {backend:'browser', cases:{}, output:'', isolated:true};
  for (const {tag} of JSON.parse(await readFile(inventory, 'utf8'))) {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const logs = [];
    page.on('console', msg => {logs.push(msg.text()); console.log(tag+': '+msg.text());});
    page.on('pageerror', error => {logs.push('PAGE_ERROR '+String(error)); console.error(tag+': '+String(error));});
    try {
      await page.goto(`http://127.0.0.1:${server.address().port}/chart_font_tests.html?chart=${encodeURIComponent(tag)}`);
      await page.waitForFunction(() => !!window.__chartFontObservation, undefined, {timeout:30000});
      const observation = await page.evaluate(() => window.__chartFontObservation);
      assert.deepEqual(Object.keys(observation.cases), [tag], 'Each isolated web actor observes its requested actual chart');
      result.cases[tag] = observation.cases[tag];
      await page.screenshot({path:output+'.'+tag+'.png', timeout:5000});
    } catch (error) { result.cases[tag] = {error:'Browser host: '+String(error)}; }
    finally {result.output += tag+'\n'+logs.join('\n')+'\n'; await writeFile(output, JSON.stringify(result, null, 2)); await page.close();}
  }
  await writeFile(output, JSON.stringify(result, null, 2));
} finally {
  await browser.close();
  await new Promise(ok => server.close(ok));
}
