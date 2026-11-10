"""Use crysta's actual public Python fit, with a recorded SDK/binding identity."""

import argparse
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('package', type=Path)
parser.add_argument('project', type=Path)
parser.add_argument('sha')
parser.add_argument('--sdk-digest', required=True)
parser.add_argument('--cache', type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.package))
crysta = importlib.import_module('crysta')
if crysta.__build_commit__ != args.sha:
    raise RuntimeError(
        'Scan run, consistency: Python reference and app must link the same SDK identity'
    )
inputs = {
    str(path.relative_to(args.project)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(args.project.rglob('*'))
    if path.is_file() and not (path.parent.name == 'analysis' and path.name.startswith('results'))
}
key = hashlib.sha256(
    json.dumps(
        [
            inputs,
            args.sdk_digest,
            hashlib.sha256(Path(crysta._crysta.__file__).read_bytes()).hexdigest(),
        ],
        sort_keys=True,
    ).encode()
).hexdigest()
cached = args.cache / (key + '.json') if args.cache else None
if cached and cached.exists():
    record = json.loads(cached.read_text())
    content = json.dumps(record['result'], sort_keys=True)
    if record['key'] != key or record['digest'] != hashlib.sha256(content.encode()).hexdigest():
        raise RuntimeError('Scan run, consistency: independent reference cache receipt differs')
    print(json.dumps(record['result']))
    raise SystemExit(0)
project = crysta.Project.load(str(args.project))
completed = []


def record(row):
    completed.append(row[0])
    print('Python reference committed ' + str(len(completed)), file=sys.stderr, flush=True)
    if progress := os.environ.get('SCAN_CONTRACT_PROGRESS_LOG'):
        with Path(progress).open('a', encoding='utf-8') as log:
            log.write('Python reference committed ' + str(len(completed)) + '\n')


project.fit(on_file_complete=record)
result = {
    'csv': (args.project / 'analysis/results.csv').read_text(),
    'completed': completed,
    'engine_sha': crysta.__build_commit__,
}
if cached:
    cached.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(result, sort_keys=True)
    cached.write_text(
        json.dumps({
            'key': key,
            'digest': hashlib.sha256(content.encode()).hexdigest(),
            'result': result,
        })
    )
print(json.dumps(result))
