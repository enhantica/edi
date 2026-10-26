import {createServer} from 'node:http';
import {readFile, writeFile} from 'node:fs/promises';
import {resolve, extname, sep} from 'node:path';
import assert from 'node:assert/strict';
const [siteArg, output, chrome, playwright] = process.argv.slice(2);
const {chromium} = await import(playwright);
const site = resolve(siteArg);
const server = createServer(async (req, res) => {
  try {
    const path = resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    assert(path.startsWith(site + sep), 'The font server serves only its sealed browser build');
    let bytes = await readFile(path);
    if (path.endsWith('/chart_font_tests.html')) {
      const original = bytes.toString();
      assert(original.includes('const instance = await qtLoad({'), 'The pinned Qt loader exposes its ordinary argument configuration');
      bytes = Buffer.from(original.replace('const instance = await qtLoad({', `const instance = await qtLoad({
        arguments: ['-input', ':/chart-fonts/tests/system/app/ChartFonts.qml', '-o', '-,txt'],
        print: text => console.log(text), printErr: text => console.error(text),`)
        );
      bytes = Buffer.from(bytes.toString().replace("status.innerHTML = 'Application exit';", "window.__fontExit = exitData; status.innerHTML = 'Application exit';"));
    }
    res.writeHead(200, {'Cross-Origin-Opener-Policy':'same-origin', 'Cross-Origin-Embedder-Policy':'require-corp',
      'Content-Type': ({'.html':'text/html','.js':'text/javascript','.wasm':'application/wasm'})[extname(path)] || 'application/octet-stream'});
    res.end(bytes);
  } catch (error) { console.error(String(error)); res.writeHead(404); res.end(); }
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await chromium.launch({executablePath:chrome, headless:true,
  args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
  const page = await browser.newPage({viewport:{width:1280,height:900}});
  const logs = [];
  page.on('console', msg => {logs.push(msg.text()); console.log(msg.text());});
  page.on('pageerror', error => {logs.push('PAGE_ERROR '+String(error)); console.error(String(error));});
  await page.goto(`http://127.0.0.1:${server.address().port}/chart_font_tests.html`);
  await page.waitForFunction(() => !!window.__fontExit, undefined, {timeout:120000});
  const exit = await page.evaluate(() => window.__fontExit);
  await page.screenshot({path:output+'.png'});
  await writeFile(output, JSON.stringify({backend:'browser', exit, output:logs.join('\n'), isolated:true}, null, 2));
} finally {
  await browser.close();
  await new Promise(ok => server.close(ok));
}
