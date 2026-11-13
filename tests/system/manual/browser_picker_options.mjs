// Validate native Chromium options before the separate retained fallback workflow.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export async function nativePickerOptionChecks(chrome, output) {
  const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
  const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
  const server = createServer((_request, response) => {
    response.writeHead(200, {'Content-Type':'text/html'});
    response.end('<!doctype html><title>Native picker option validation</title>');
  });
  await new Promise(ready => server.listen(0, '127.0.0.1', ready));
  let browser;
  try {
    browser = await chromium.launch({executablePath:chrome, headless:true, args:['--no-sandbox']});
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    const client = await page.context().newCDPSession(page);
    let choices = 0;
    page.on('filechooser', () => ++choices);
    const capability = await client.send('Runtime.evaluate', {
      expression:"({native:String(window.showOpenFilePicker).includes('[native code]'),active:navigator.userActivation.isActive})",
      returnByValue:true, userGesture:false,
    });
    assert(capability.result.value.native,
      'The option contract must execute the actual browser picker API');
    assert.equal(capability.result.value.active, false,
      'Native schema controls must not acquire activation from an observation helper');
    const records = [];
    const cases = [
      {extensions:['.cif,.edi'], multiple:false, error:'TypeError'},
      {extensions:['.xye,.xy,.dat,.txt,.csv,.int,.hkl'], multiple:true, error:'TypeError'},
      {extensions:['.cif','.edi'], multiple:false, error:'SecurityError'},
      {extensions:['.cif','.edi'], multiple:true, error:'SecurityError'},
      {extensions:['.xye','.xy','.dat','.txt','.csv','.int','.hkl'], multiple:true, error:'SecurityError'},
      {extensions:[], multiple:false, error:'SecurityError'},
      {extensions:[], multiple:true, error:'SecurityError'},
    ];
    for (const expected of cases) {
      const options = {multiple:expected.multiple};
      if (expected.extensions.length) Object.assign(options, {
        types:[{accept:{'application/octet-stream':expected.extensions}}], excludeAcceptAllOption:true,
      });
      const expression = `(async()=>{try{await window.showOpenFilePicker(${JSON.stringify(options)});return {resolved:true};}
        catch(error){return {name:error.name,message:error.message};}})()`;
      const actual = await client.send('Runtime.evaluate', {
        expression, awaitPromise:true, returnByValue:true, userGesture:false,
      });
      assert(!actual.exceptionDetails, 'Native option validation returns its precise caught browser result');
      const result = actual.result.value;
      assert.equal(result.name, expected.error,
        'Comma tokens fail schema validation; split or empty filters reach the unchanged gesture guard');
      if (expected.error === 'TypeError') assert(result.message.includes('invalid characters'),
        'The old Qt comma token reaches the actual invalid-extension refusal');
      else assert(result.message.includes('user gesture'),
        'Valid extensions pass native schema checking without opening an interactive chooser');
      records.push({options, result});
    }
    assert.equal(choices, 0, 'Schema and gesture controls must not open an interactive file chooser');
    await mkdir(output, {recursive:true});
    const receipt = {browser:browser.version(), nativeApi:true, userGesture:false, choices, records};
    await writeFile(join(output, 'native-picker-options.json'), JSON.stringify(receipt, null, 2)+'\n');
    return receipt;
  } finally {
    if (browser) await browser.close();
    await new Promise(done => server.close(done));
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [chrome, output] = process.argv.slice(2);
  assert(chrome && output, 'The native picker probe requires its pinned browser and evidence directory');
  await nativePickerOptionChecks(chrome, output);
  console.log('Native Chromium picker option contract passed');
}
