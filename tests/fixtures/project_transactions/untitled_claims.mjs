// Run production browser publication in two tabs sharing IndexedDB, OPFS, and Web Locks.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {join} from 'node:path';

const [root, chrome] = process.argv.slice(2);
const source = await readFile(join(root, 'app/src/web_storage.cpp'), 'utf8');
const bodies = Object.fromEntries([
  'edi_storage_install',
  'edi_storage_write',
  'edi_storage_publish_untitled',
  'edi_storage_revoke',
  'edi_storage_resume',
].map(name => {
  const match = source.match(new RegExp('EM_JS\\([^,]+,\\s*' + name + ',\\s*\\([^]*?\\), \\{([^]*?)\\n\\}\\);'));
  assert(match, 'The browser must execute the shipped ' + name + ' entry point');
  return [name, match[1]];
}));
const toolchain = process.env.EDI_WASM_TOOLCHAIN || join(process.env.HOME, '.cache/edi-wasm');
const {chromium} = await import(join(toolchain, 'playwright/node_modules/playwright-core/index.mjs'));
const server = createServer((_req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.end('<!doctype html><title>Untitled publication</title>');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({executablePath: chrome, args: ['--no-sandbox'], headless: true});

async function install(page) {
  await page.goto('http://127.0.0.1:' + server.address().port);
  await page.evaluate(bodies => {
    const jobs = new Map();
    const answers = new Map();
    const vetoes = new Map();
    const Module = {
      _edi_storage_answered: (job, value) => {
        answers.set(job, (answers.get(job) || 0) + 1);
        jobs.get(job)(JSON.parse(value));
      },
      _edi_storage_serial_finished: () => {},
    };
    function invoke(name, args = {}) {
      new Function('FS', 'Module', 'UTF8ToString', 'stringToNewUTF8', ...Object.keys(args), bodies[name])(
        {}, Module, value => value, value => value, ...Object.values(args));
    }
    invoke('edi_storage_install');
    const S = globalThis.ediStorage;
    // Only C++ data marshalling is represented here. The production JS owns the real transactions and files.
    S.policy = (operation, {key, recovery, kind, name, entries, paths, job}) => {
      if (operation === 4) {
        if (entries.some(([path]) => !paths.includes(path))) {
          throw new Error('The claim witness only marshals writes into new destinations');
        }
        return [];
      }
      if (operation === 7) return ['edi', recovery ? 'recovery' : 'projects', key];
      if (operation === 5) return {key, recovery, kind, name};
      if (operation === 15) return 'browser';
      if (operation === 21) return vetoes.get(job) || {outcome: 'go'};
      throw new Error('Unexpected storage marshalling operation ' + operation);
    };
    const files = text => [['project.edi', new TextEncoder().encode(text)]];
    const controls = new Map();
    const realWrite = S.writeBrowser;
    S.writeBrowser = async (path, entries) => {
      await realWrite(path, entries);
      const gate = controls.get(path.at(-1));
      if (gate) {
        gate.written();
        if (await gate.release) throw new Error('Independent stage write refusal');
      }
    };
    let nextJob = 0;
    function run(name, args, staged) {
      const job = ++nextJob;
      const answer = new Promise(resolve => jobs.set(job, resolve));
      if (staged) S.staged.set(job, staged);
      invoke(name, {job, ...args});
      if (staged) invoke('edi_storage_resume', {job});
      return {job, answer};
    }
    function hold(key) {
      let resume, written;
      const release = new Promise(resolve => { resume = resolve; });
      const reached = new Promise(resolve => { written = resolve; });
      const gate = {written, release, resume, reached};
      controls.set(key, gate);
      return gate;
    }
    async function reached(gate) {
      await Promise.race([gate.reached, gate.answer.then(value => {
        throw new Error('Write settled before reaching its hold: ' + JSON.stringify(value));
      })]);
    }
    globalThis.claimTest = {
      async seed(key, text) {
        await realWrite(['edi', 'recovery', key], files(text));
        await S.put({key, kind: 'browser', name: 'Untitled', recovery: 1});
      },
      async start(key, stage, text, refuse = false) {
        const gate = hold(stage);
        Object.assign(gate, run('edi_storage_publish_untitled', {
          untitled_utf8: key, op: 7, stage_utf8: stage, name_utf8: text,
        }, files(text)));
        if (refuse)
          vetoes.set(gate.job, {outcome: 'rejected', message: 'Independent precommit snapshot veto'});
        await reached(gate);
      },
      async startRecovery(key, text) {
        const gate = hold(key);
        Object.assign(gate, run('edi_storage_write', {
          key_utf8: key, kind_utf8: 'browser', name_utf8: 'Untitled', recovery: 1,
        }, files(text)));
        await reached(gate);
      },
      async recover(key, text) {
        const result = run('edi_storage_write', {
          key_utf8: key, kind_utf8: 'browser', name_utf8: 'Untitled', recovery: 1,
        }, files(text));
        return result.answer;
      },
      revoke: (key, stage) => run('edi_storage_revoke', {
        untitled_utf8: key, op: 7, stage_utf8: stage,
      }).answer,
      finish(stage, fail) {
        const gate = controls.get(stage);
        gate.resume(fail);
        return gate.answer;
      },
      count: key => answers.get(controls.get(key).job),
      claim: stage => S.record(S.claimKey(stage)),
      record: key => S.record(key),
      sweep: async () => S.sweep(await S.store('readonly', store => store.getAll())),
      async bytes(part, key) {
        try {
          const dir = await S.opfs(['edi', part, key], false);
          return await (await (await dir.getFileHandle('project.edi')).getFile()).text();
        } catch (error) {
          if (error.name === 'NotFoundError') return null;
          throw error;
        }
      },
    };
  }, bodies);
}

const call = (page, method, ...args) => page.evaluate(([method, args]) => claimTest[method](...args), [method, args]);

try {
  const context = await browser.newContext();
  const first = await context.newPage(), second = await context.newPage();
  await Promise.all([install(first), install(second)]);
  const staleClaims = [];
  for (const fail of [false, true]) {
    const key = 'shared-untitled-' + fail;
    const stageA = 'stage-7-a-' + fail, stageB = 'stage-7-b-' + fail;
    const original = 'Untitled recovery ' + fail;
    await call(first, 'seed', key, original);
    const originalRecord = await call(first, 'record', key);
    await call(first, 'start', key, stageA, 'First tabs files');
    await call(second, 'start', key, stageB, 'Second tabs files');
    for (const stage of [stageA, stageB]) {
      const claim = await call(first, 'claim', stage);
      assert.equal(claim?.stage, stage, 'Each tab has its own claim despite identical local operation ids');
      assert.equal(claim?.state, 'live', 'Staging has granted temporary authority to the exact stage');
    }
    await call(second, 'sweep');
    assert.equal(await call(second, 'bytes', 'projects', stageA), 'First tabs files',
      'Startup sweep preserves an unclaimed stage while the other tab holds its write lock');
    await call(first, 'revoke', key, stageA);
    const lost = await call(first, 'finish', stageA, fail);
    if (fail) {
      assert.equal(lost.ok, false, 'A staged write failure answers with a refusal');
    } else {
      assert.equal(lost.outcome, 'lost', 'A different stage with the same id has no authority to publish');
    }
    assert.equal(await call(second, 'bytes', 'projects', stageA), null,
      'A failed or losing stage removes its own files');
    assert.equal(await call(second, 'record', stageA), undefined, 'The losing stage has no named place');
    assert.equal(await call(second, 'record', stageB), undefined, 'Staged files alone do not publish a named place');
    assert.equal(await call(second, 'bytes', 'projects', stageB), 'Second tabs files',
      'Revoke and failure in the first tab preserve the same-id second stage');
    assert.deepEqual(await call(second, 'record', key), originalRecord,
      'A stage which lost never changes the untitled place record');
    assert.equal(await call(second, 'bytes', 'recovery', key), original,
      'A stage which lost never changes the untitled recovery bytes');

    assert.equal((await call(second, 'finish', stageB, false)).outcome, 'published',
      'The tab with the live stage publishes its own write');
    const published = await call(second, 'record', stageB);
    assert.equal(published.name, 'Second tabs files', 'The named place comes from the stage that won');
    assert.equal(await call(second, 'record', key), undefined, 'Publication removes the old untitled place');
    assert.equal(await call(second, 'bytes', 'recovery', key), null, 'Publication removes obsolete recovery');
    await call(first, 'revoke', key, stageA);
    assert.deepEqual(await call(first, 'record', stageB), published,
      'An old revoke cannot change the published place of the other stage');
    staleClaims.push({
      observed: (await call(first, 'claim', stageB))?.state,
      expected: 'published',
    });
    assert.equal(await call(first, 'count', stageA), 1, 'The losing or refused write answers once');
    assert.equal(await call(second, 'count', stageB), 1, 'The committed publication answers once');
    await call(first, 'sweep');
    assert.equal(await call(first, 'bytes', 'projects', stageB), 'Second tabs files',
      'The sweep keeps the published project bytes');
  }
  {
    const key = 'refused-untitled', stage = 'stage-7-refused';
    const original = 'Original recovery after decisional veto';
    await call(first, 'seed', key, original);
    const place = await call(first, 'record', key);
    await call(first, 'start', key, stage, 'Candidate refused at the commit boundary', true);
    const answer = await call(first, 'finish', stage, false);
    assert.equal(answer.outcome, 'rejected', 'A snapshot veto produces a terminal refusal');
    assert.equal(await call(first, 'count', stage), 1, 'The veto receives exactly one publication outcome');
    assert.equal(await call(second, 'record', stage), undefined, 'A veto leaves no committed named place');
    assert.equal(await call(second, 'bytes', 'projects', stage), null, 'A veto reclaims its own staged files');
    assert.deepEqual(await call(second, 'record', key), place, 'A veto preserves the unnamed place record');
    assert.equal(await call(second, 'bytes', 'recovery', key), original, 'A veto preserves the recovery bytes');
  }
  const observedRecovery = [];
  for (const timing of ['before-commit', 'after-commit']) {
    const key = 'stale-recovery-' + timing, stage = 'stage-7-published-' + timing;
    await call(first, 'seed', key, 'Original recovery');
    if (timing === 'before-commit')
      await call(first, 'startRecovery', key, 'Older tab has a delayed recovery write');
    await call(second, 'start', key, stage, 'Named snapshot');
    assert.equal((await call(second, 'finish', stage, false)).outcome, 'published',
      'A separately admitted first save has one committed named outcome');
    await (timing === 'before-commit'
      ? call(first, 'finish', key, false) : call(first, 'recover', key, 'Older tab writes after naming'));
    assert.equal(await call(second, 'count', stage), 1, 'Named publication does not report a second outcome');
    assert.equal(await call(second, 'bytes', 'projects', stage), 'Named snapshot',
      'The late recovery write cannot change the durable named bytes');
    observedRecovery.push({
      timing,
      placeExists: !!(await call(second, 'record', key)),
      recovery: await call(second, 'bytes', 'recovery', key),
    });
  }
  assert.deepEqual(observedRecovery, [
    {timing: 'before-commit', placeExists: false, recovery: null},
    {timing: 'after-commit', placeExists: false, recovery: null},
  ], 'Recovery from another tab cannot recreate the retired place before or after naming commits');

  const key = 'teardown-untitled', stageA = 'stage-7-torn-down', stageB = 'stage-7-still-live';
  await call(first, 'seed', key, 'Untitled recovery after tab teardown');
  await call(first, 'start', key, stageA, 'Abandoned files');
  await call(second, 'start', key, stageB, 'Files from the remaining tab');
  await first.close();
  await call(second, 'sweep');
  assert.equal(await call(second, 'bytes', 'projects', stageA), null,
    'The sweep removes an orphan when the writer tab and its lock are gone');
  assert.equal(await call(second, 'bytes', 'projects', stageB), 'Files from the remaining tab',
    'The sweep preserves the other tabs live stage');
  await call(second, 'revoke', key, stageB);
  assert.equal((await call(second, 'finish', stageB, false)).outcome, 'lost',
    'A committed revoke beats publication even after the staged files were written');
  assert.equal(await call(second, 'record', stageB), undefined, 'Revoke prevents named publication');
  assert.equal(await call(second, 'bytes', 'projects', stageB), null, 'Revoking removes staged files');
  assert.equal(await call(second, 'bytes', 'recovery', key), 'Untitled recovery after tab teardown',
    'Revoking the only live stage leaves its untitled recovery intact');
  for (const {observed, expected} of staleClaims) {
    assert.deepEqual(observed, expected,
      'An old revoke cannot rewrite the published claim of the other stage');
  }
} finally {
  await browser.close();
  server.close();
}
