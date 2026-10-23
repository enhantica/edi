"""Deferred Windows clipping checks; the rendering fault has not been reproduced."""

import copy
from pathlib import Path

import pytest
import yaml

from tests.fixtures.windows_clipping.check_receipt import CASES, validate

ROOT = Path(__file__).resolve().parents[3]


def test_windows_clipping_job_is_installed_with_a_real_producer():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    assert 'windows-web-clipping' in jobs, (
        'The actual workflow installs the Windows clipping job, beyond its fixture fragment'
    )
    job = jobs['windows-web-clipping']
    assert job.get('runs-on') == 'windows-2025' and 'app-wasm' in job['needs'], (
        'A hosted Windows browser consumes both web kits from the same workflow run'
    )
    commands = '\n'.join(step.get('run', '') for step in job['steps'])
    assert 'windows_clipping.mjs' in commands and 'check_receipt.py' in commands, (
        'The installed job executes real browser pixels and requires a complete exact-head receipt'
    )
    producer = jobs['app-wasm']
    script = '\n'.join(step.get('run', '') for step in producer['steps'])
    assert 'clipping' in script, (
        'The web producer explicitly builds and manifests its native clipping host'
    )
    sources = (ROOT / 'app/CMakeLists.txt').read_text()
    hooks = (ROOT / 'app/main.cpp').read_text()
    assert 'clipping' in sources and 'clipping' in hooks, (
        'The app compiles its native observer and QML presets and installs the gated host'
    )


def witness():
    rows = []
    for mode, theme, scenario in sorted(CASES):
        rows.append({
            'mode': mode,
            'theme': theme,
            'scenario': scenario,
            'status': 'passed',
            'build': {
                'ediCommit': 'a' * 40,
                'sources': {'fixture.qml': 'b' * 64, 'observer.cpp': 'c' * 64},
            },
            'state': {'completed': True},
            'gpu': {'renderer': 'ANGLE Direct3D11'},
            'pixels': {
                'visibleInside': 2,
                'changed': 3,
                'visibleOutside': 0,
                'afterOutside': int(scenario == 'outer-off'),
                'afterInside': 0,
            },
        })
    return {
        'complete': True,
        'platform': 'win32',
        'browser': 'Independent control',
        'errors': [],
        'receipts': rows,
    }


@pytest.mark.parametrize(
    'escape',
    [
        'missing',
        'duplicate',
        'skipped',
        'stale',
        'no-content',
        'no-action',
        'no-escape',
        'overflow',
        'stale-popup',
        'wrong-gpu',
        'no-native',
        'incomplete',
    ],
)
def test_windows_receipt_refuses_missing_skipped_and_false_green_controls(escape):
    document = witness()
    validate(document, 'a' * 40)
    bad = copy.deepcopy(document)
    row = bad['receipts'][0]
    if escape == 'missing':
        bad['receipts'].pop()
    elif escape == 'duplicate':
        bad['receipts'][-1] = row
    elif escape == 'skipped':
        row['status'] = 'skipped'
    elif escape == 'stale':
        row['build']['ediCommit'] = 'd' * 40
    elif escape == 'no-content':
        row['pixels']['visibleInside'] = 0
    elif escape == 'no-action':
        row['state']['completed'] = False
    elif escape == 'no-escape':
        next(r for r in bad['receipts'] if r['scenario'] == 'outer-off')['pixels'][
            'afterOutside'
        ] = 0
    elif escape == 'overflow':
        row['pixels']['afterOutside'] = 1
    elif escape == 'stale-popup':
        next(r for r in bad['receipts'] if r['scenario'] == 'popup-close')['pixels'][
            'afterInside'
        ] = 1
    elif escape == 'wrong-gpu':
        row['gpu']['renderer'] = 'SwiftShader'
    elif escape == 'no-native':
        row['build']['sources'].pop('observer.cpp')
    else:
        bad['complete'] = False
    with pytest.raises(
        ValueError, match=r'witness|execute|artifact|action|browser|pixels|escape|sources'
    ):
        validate(bad, 'a' * 40)
