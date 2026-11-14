// Execute the shipped browser routes and measure the owner's workload on one runner.
import { spawnSync } from 'node:child_process';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const [site, outputArg, chrome] = process.argv.slice(2);
assert(site && outputArg && chrome, 'web performance acceptance requires the shipped site, persistent evidence directory and pinned browser');
const output = resolve(outputArg);
await mkdir(output, {recursive:true});
const contract = JSON.parse(await readFile(new URL('../../fixtures/web_parallel/contract.json',import.meta.url)));
const driver = fileURLToPath(new URL('./e04_t11_browser.mjs',import.meta.url));
const reference=process.argv.find(arg=>arg.startsWith('--written-reference='));
assert(reference,'The full matrix requires independently raw-qualified ordinary native Save counterparts');
const observations = {};
for (const fitCase of ['lbco','ncaf']) {
  observations[fitCase] = {};
  for (const name of ['oneworker','multithread','shim']) {
    const mode=name==='oneworker'?'multithread':name;
    const workers=name==='oneworker'?'1':'auto';
    const dir = join(output, fitCase, name);
    const run = spawnSync(process.execPath, ['--experimental-websocket',driver,resolve(site),mode,dir,chrome,`--fit-case=${fitCase}`,`--engine-workers=${workers}`,reference], {stdio:'inherit',timeout:300000});
    assert.equal(run.status,0,'every corpus fit must complete through each shipped browser route');
    const measurement = JSON.parse(await readFile(join(dir,`${mode}-${fitCase}-measurement.json`)));
    const route = contract.routes[mode];
    assert.equal(measurement.kit,route.kit,'observed wasm requests must select the shipped route kit');
    assert.equal(measurement.isolated,route.isolated,'the browser must observe the route isolation state');
    assert.equal(measurement.sharedArrayBuffer,route.shared_array_buffer,'the browser must observe SharedArrayBuffer availability for the route');
    assert.equal(measurement.nativeNumerics,true,'every route must compare fitted parameters and arrays to the independent native capture');
    assert.equal(measurement.engineWorkers,workers,'The measured fit retains its real UI worker selection');
    observations[fitCase][name] = measurement;
  }
}
const st = observations.ncaf.oneworker, mt = observations.ncaf.multithread;
assert(st.coreCount >= contract.speed.minimum_core_count && mt.coreCount === st.coreCount,
  'the measured browser runner must expose at least four cores consistently across worker selections on one kit');
assert.deepEqual(st.wasm,mt.wasm,'One-worker and parallel measurements execute the exact same served multithread module');
const ratio = st.fitElapsedMs / mt.fitElapsedMs;
const evidence = {chrome,coreCount:mt.coreCount,ratio,observations};
await writeFile(join(output,'web-performance.json'),JSON.stringify(evidence,null,2));
console.log(JSON.stringify({coreCount:mt.coreCount,ratio,oneWorkerMs:st.fitElapsedMs,multithreadMs:mt.fitElapsedMs}));
assert(ratio >= contract.speed.minimum_ratio,'the parallel five-bank fit must be at least 1.4 times faster than one worker on the same kit on the same browser runner');
const webkitDriver=fileURLToPath(new URL('./web_parallel_routes.mjs',import.meta.url));
const webkitArgs=[webkitDriver,resolve(site),join(output,'webkit-routes')];
if(process.env.WEB_PARALLEL_PLAYWRIGHT)webkitArgs.push(process.env.WEB_PARALLEL_PLAYWRIGHT);
const webkitRun=spawnSync(process.execPath,webkitArgs,{stdio:'inherit',timeout:600000});
assert.equal(webkitRun.status,0,'The shipped WebKit routes must pass reload and second navigation with COEP require-corp');
