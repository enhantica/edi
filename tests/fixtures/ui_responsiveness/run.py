"""Collect fresh driver traces from the current built app; never compile a host."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from tests.fixtures.ui_responsiveness.generate import full_scan
from tests.fixtures.ui_responsiveness.tab_inventory import declared_tabs, scenario_steps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTRACT = json.loads((HERE / 'contract.json').read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(app, output, scan, series, *, archive=None):
    """Run the declared scenarios and their GUI-blocking controls separately."""
    app = app.resolve()
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    markers = set(re.findall(rb'edi-build-commit:([0-9a-f]{40})([^\n]*)\n', app.read_bytes()))
    if markers != {(source.encode(), b'')}:
        raise ValueError('The app must carry exactly the clean current source build identity')
    output.mkdir(parents=True, exist_ok=False)
    if archive is not None:
        scan = full_scan(archive, output / 'full-input')
    if scan is None:
        raise ValueError('A scan project or the original nightly archive is required')
    manifest = {
        'schema': 1,
        'source': source,
        'binary': str(app),
        'binary_sha256': digest(app),
        'full_scan': archive is not None,
        'archive_sha256': json.loads((HERE / 'scan-source.json').read_text())['archive_sha256']
        if archive is not None
        else None,
        'runs': {},
        'tab_inventory': declared_tabs(ROOT),
    }
    for name in scenario_steps(ROOT):
        for control in (False, True):
            key = name + ('-control' if control else '')
            folder = output / key
            folder.mkdir()
            settings = folder / 'settings'
            settings.mkdir()
            env = {
                **os.environ,
                'EDI_STALL_PROBE': '1',
                'EDI_UI_TRACE': '1',
                'XDG_CONFIG_HOME': str(settings),
                'XDG_DATA_HOME': str(settings),
                'OMP_NUM_THREADS': '1',
                'EDI_DEMO_SCAN_PROJECT': str(series if name == 'e58-series' else scan),
                'EDI_UI_TAB_INVENTORY': json.dumps(manifest['tab_inventory']),
            }
            env.pop('EDI_STALL_PROBE_STACKS', None)
            env.pop('EDI_UI_BLOCK_MS', None)
            if control:
                env['EDI_UI_BLOCK_MS'] = '150'
            with (folder / 'app.log').open('w') as stream:
                result = subprocess.run(
                    [str(app), '--demo', str(folder / 'images'), '--demo-only', name],
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=1200,
                    check=False,
                )
            if result.returncode:
                raise RuntimeError('The actual UI scenario failed: ' + key)
            records = [
                json.loads(line.split(CONTRACT['prefix'], 1)[1])
                for line in (folder / 'app.log').read_text().splitlines()
                if CONTRACT['prefix'] in line
            ]
            if not records:
                raise RuntimeError('The actual app emitted no UI observations: ' + key)
            trace = folder / 'trace.jsonl'
            trace.write_text(''.join(json.dumps(row) + '\n' for row in records))
            manifest['runs'][key] = {
                'path': str(trace.relative_to(output)),
                'sha256': digest(trace),
            }
    if digest(app) != manifest['binary_sha256']:
        raise RuntimeError('The app changed during observation')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scan', type=Path)
    parser.add_argument('--series', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    options = parser.parse_args()
    collect(
        options.app,
        options.output.resolve(),
        options.scan.resolve() if options.scan else None,
        options.series.resolve(),
        archive=options.archive,
    )
