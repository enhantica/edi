import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {join,resolve,extname} from 'node:path';
import {fileURLToPath} from 'node:url';

const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME,'.cache/edi-wasm');
const {chromium} = await import(join(toolchain,'playwright/node_modules/playwright-core/index.mjs'));
const chrome = process.env.EDI_CHROME || join(toolchain,'chrome-146.0.7680.153/chrome-headless-shell/linux-146.0.7680.153/chrome-headless-shell-linux64/chrome-headless-shell');
export async function openBrowser() {
  return chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
}

export async function observeEvent(root,pagePath,eventPath,instant,browser) {
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
let page;
try {
  page = await browser.newPage();
  await page.clock.install({time:new Date(instant)});
  await page.clock.setFixedTime(new Date(instant));
  const base = `http://127.0.0.1:${server.address().port}`;
  const submissions = [];
  await page.route(`${base}/survey`, async route => {
    submissions.push(route.request().postDataJSON());
    await route.fulfill({status:201,contentType:'application/json',body:'{}'});
  });
  await page.goto(`${base}/${pagePath}`);
  await page.evaluate(endpoint => {
    window.edFeedbackForm = {endpoint,status:{sending:'Sending',failed:'Failed %1'}};
  }, `${base}/feedback`);
  const config = await readFile(join(root,'../mkdocs.yml'),'utf8');
  const scripts = config.split('extra_javascript:')[1]?.split(/^\S/m)[0] || '';
  const surveyScripts = [...scripts.matchAll(/^\s+-\s+(assets\/survey\/[^\s]+\.js(?:\?[^\s]+)?)/gm)];
  assert.equal(surveyScripts.length, 1, 'The site must load the real survey script once');
  for (const match of surveyScripts)
    await page.addScriptTag({url:`http://127.0.0.1:${server.address().port}/${match[1]}`});
  const event = page.getByRole('combobox',{name:/event/i});
  await event.waitFor({timeout:3000});
  const expected = instant.slice(0,10)>='2030-05-10' && instant.slice(0,10)<='2030-05-12';
  await page.waitForFunction(() => [...document.querySelectorAll('select option')].some(o=>o.textContent.includes('General')),{},{timeout:3000});
  assert.equal(await page.evaluate(() => new Date().toISOString()), new Date(instant).toISOString(), 'The date witness stays at its supplied instant throughout browser setup');
  const options = await event.locator('option').allTextContents();
  assert(fetched,'The event combobox must read the single events file');
  assert(options.some(value=>value.trim()==='General'),'General must always be offered');
  assert.equal(options.some(value=>value.includes('Window witness')),expected,'The event must be offered exactly during its inclusive date window');
  assert(!options.some(value=>value.includes('Past witness')) || instant.startsWith('2030-05-09'),'Expired events must be absent');
  assert(!options.some(value=>value.includes('Future witness')) || instant.startsWith('2030-05-13'),'Future events must be absent');
  const form = page.locator('form.ed-survey-form');
  const privateFields = form.locator('[name="name"], [name="email"], [name="affiliation"], [name="consent"], [name="contact"], input[type="email"]');
  assert.equal(await privateFields.count(),0,'The anonymous survey must not render contact or consent controls');
  assert(await form.getByRole('heading',{name:'About your work',exact:true}).isVisible(),
    'The anonymous form asks about work rather than personal identity');
  const platforms = form.locator('[data-key="platforms"]');
  const choices = await platforms.locator('input[type="checkbox"]').evaluateAll(boxes=>boxes.map(box=>box.value));
  assert.deepEqual(choices,['Windows','macOS','Linux','Tablet','Smartphone','Other'],
    'The platform question offers the six owner-declared checkbox choices');
  const linux = platforms.getByRole('checkbox',{name:'Linux',exact:true});
  const follow = platforms.locator('[name="platforms_linux"]');
  assert(await follow.isHidden(),'The Linux distribution field starts hidden');
  await platforms.getByRole('checkbox',{name:'Windows',exact:true}).check();
  await linux.check();
  assert(await follow.isVisible(),'Selecting Linux must reveal its distribution follow-up');
  await follow.fill('Debian 13');
  let answers = await form.evaluate(form=>window.edSurvey.answers(form));
  assert.deepEqual(answers.platforms,['Windows','Linux'],'Platform answers retain multiple selected platforms');
  assert.equal(answers.platforms_linux,'Debian 13','The selected Linux answer retains its distribution');
  await linux.uncheck();
  assert(await follow.isHidden(),'Deselecting Linux hides its distribution field');
  answers = await form.evaluate(form=>window.edSurvey.answers(form));
  assert(!('platforms_linux' in answers),'A stale hidden Linux answer must not enter the payload');
  await linux.check();
  await follow.fill('Debian 13');
  await form.getByRole('button',{name:'Send',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('form.ed-survey-form [name="platforms_linux"]').hidden,
    {},{timeout:3000});
  assert.equal(submissions.length,1,'One anonymous Send must produce one intercepted submission');
  const payload = submissions[0];
  assert.deepEqual(Object.keys(payload).sort(),['answers','app','event'],
    'The anonymous payload contains only event, answers and application context');
  assert.equal(payload.event,'general','The anonymous payload retains the selected event');
  assert.deepEqual(payload.answers.platforms,['Windows','Linux'],'Submission retains platform choices');
  assert.equal(payload.answers.platforms_linux,'Debian 13','Submission retains the selected Linux distribution');
  for (const key of ['contact','name','email','affiliation','consent'])
    assert(!(key in payload.answers),'Anonymous answers must not contain structured contact fields');
  assert.equal(await platforms.locator('input:checked').count(),0,
    'Successful submission resets the platform choices and hides the Linux follow-up');

} finally {if (page) await page.context().close();await new Promise(ok=>server.close(ok));}
}

if (resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const browser = await openBrowser();
  try {await observeEvent(...process.argv.slice(2),browser);}
  finally {await browser.close();}
}
