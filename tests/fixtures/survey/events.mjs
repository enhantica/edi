import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {join,resolve,extname} from 'node:path';

const [root,pagePath,eventPath,instant] = process.argv.slice(2);
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME,'.cache/edi-wasm');
const {chromium} = await import(join(toolchain,'playwright/node_modules/playwright-core/index.mjs'));
const chrome = process.env.EDI_CHROME || join(toolchain,'chrome-146.0.7680.153/chrome-headless-shell/linux-146.0.7680.153/chrome-headless-shell-linux64/chrome-headless-shell');
const document = JSON.parse(await readFile(eventPath,'utf8'));
const original = Array.isArray(document) ? document : document.events;
assert(Array.isArray(original),'The single events file must declare an event list');
assert.equal(document.schema,'edi-survey-events/1','The survey observer uses the declared event schema');
assert(original.some(event=>event.name==='general' && event.title==='General'),
  'General is the permanent undated choice');
for (const event of original.filter(event=>event.name!=='general'))
  assert(event.name && event.title && /^\d{4}-\d{2}-\d{2}$/.test(event.start) && /^\d{4}-\d{2}-\d{2}$/.test(event.end),
    'Every named event carries its title and explicit inclusive date window');
const entry = (name,title,start,end) => ({name,title,start,end});
const entries = [{name:'general',title:'General'},
  entry('past-witness','Past witness','2030-05-01','2030-05-09'),
  entry('window-witness','Window witness','2030-05-10','2030-05-12'),
  entry('future-witness','Future witness','2030-05-13','2030-05-20')];
const events = {...document,events:entries};
let fetched = false;
const server = createServer(async (request,response) => {
  try {
    const path = decodeURIComponent(new URL(request.url,'http://localhost').pathname);
    const file = resolve(root,'.'+path);
    assert(file.startsWith(resolve(root)+'/'),'The survey server must stay within the docs');
    if (file === resolve(eventPath)) {
      fetched = true; response.setHeader('Content-Type','application/json'); response.end(JSON.stringify(events)); return;
    }
    response.setHeader('Content-Type',extname(file)==='.js'?'text/javascript':extname(file)==='.json'?'application/json':'text/html');
    response.end(await readFile(file));
  } catch {response.writeHead(404);response.end();}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const browser = await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
try {
  const page = await browser.newPage();
  await page.clock.install({time:new Date(instant)});
  await page.goto(`http://127.0.0.1:${server.address().port}/${pagePath}`);
  const config = await readFile(join(root,'../mkdocs.yml'),'utf8');
  const scripts = config.split('extra_javascript:')[1]?.split(/^\S/m)[0] || '';
  for (const match of scripts.matchAll(/^\s+-\s+(assets\/[^\s]+\.js(?:\?[^\s]+)?)/gm))
    await page.addScriptTag({url:`http://127.0.0.1:${server.address().port}/${match[1]}`});
  const event = page.getByRole('combobox',{name:/event/i});
  await event.waitFor({timeout:3000});
  const expected = instant.slice(0,10)>='2030-05-10' && instant.slice(0,10)<='2030-05-12';
  await page.waitForFunction(() => [...document.querySelectorAll('select option')].some(o=>o.textContent.includes('General')),{},{timeout:3000});
  const options = await event.locator('option').allTextContents();
  assert(fetched,'The event combobox must read the single events file');
  assert(options.some(value=>value.trim()==='General'),'General must always be offered');
  assert.equal(options.some(value=>value.includes('Window witness')),expected,'The event must be offered exactly during its inclusive date window');
  assert(!options.some(value=>value.includes('Past witness')) || instant.startsWith('2030-05-09'),'Expired events must be absent');
  assert(!options.some(value=>value.includes('Future witness')) || instant.startsWith('2030-05-13'),'Future events must be absent');
} finally {await browser.close();await new Promise(ok=>server.close(ok));}
