import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

const source = await readFile(process.argv[2] ||
  new URL('../../../app/src/web_files.cpp', import.meta.url), 'utf8');
const body = source.match(/^EM_JS\(void, edi_web_pick_folder, [^\n]+, \{\n([\s\S]*?)^\}\);/m)?.[1];
assert(body, 'Run the production browser folder-picker callback');
const bound = 50_000_000;

async function choose(entries) {
  const reads = [], writes = [], receipts = [];
  const callbacks = new Map();
  const input = {
    files: entries.map(([name, size]) => ({
      name, size, webkitRelativePath: `scan/${name}`,
      async arrayBuffer() {
        reads.push(name);
        return new Uint8Array([1, 2, 3]).buffer;
      },
    })),
    style: {},
    addEventListener(event, callback) { callbacks.set(event, callback); },
    click() {},
    remove() {},
  };
  runInNewContext(body, {
    request: 37,
    root_utf8: '/picked',
    limit: bound,
    UTF8ToString: String,
    stringToNewUTF8: String,
    document: {
      getElementById() { return null; },
      createElement() { return input; },
      body: { appendChild() {} },
    },
    FS: {
      mkdirTree() {},
      writeFile(path) { writes.push(path); },
    },
    Module: {
      _edi_web_folder_copied(id, count) { receipts.push(['copied', id, count]); },
      _edi_web_folder_refused(id, name, size) { receipts.push(['refused', id, name, size]); },
    },
  });
  await callbacks.get('change')();
  return { reads, writes, receipts };
}

for (const files of [
  [['small.xye', 132], ['oversize.xye', bound + 1]],
  [['oversize.xye', bound + 1], ['small.xye', 132]],
]) {
  const refused = await choose(files);
  assert.deepEqual(refused.reads, [], 'A too-large member refuses the folder before any read');
  assert.deepEqual(refused.writes, [], 'No member of the refused folder is copied');
  assert.deepEqual(refused.receipts, [['refused', 37, 'oversize.xye', bound + 1]],
    'One refusal reports the original request, oversize filename and byte count');
}

const allowed = await choose([['at-bound.xye', bound], ['small.xye', 132]]);
assert.deepEqual(allowed.reads, ['at-bound.xye', 'small.xye'],
  'A file at the measured byte limit is admitted');
assert.deepEqual(allowed.writes, ['/picked/scan/at-bound.xye', '/picked/scan/small.xye'],
  'The admitted folder retains both selected paths');
assert.deepEqual(allowed.receipts, [['copied', 37, 2]],
  'The accepted request completes after both writes');
