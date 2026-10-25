"""Census actual app tooltip delegates, including live desktop and web popup branches."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCOPES = [
    'project',
    'structure',
    'experiment',
    'analysis',
    'report',
    'save-native',
    'save-web-disk',
    'save-web-fallback',
    'web-open',
    'browser-warning',
]


@pytest.fixture(scope='module')
def tooltip_receipts():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Tooltip census requires the actual app test host'
    return subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_tooltip_style.qml'),
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        timeout=150,
        check=False,
    )


@pytest.mark.parametrize(
    'scope',
    [
        'counterexamples',
        'shared_wrap_width',
        'disabled_choice_class',
        'balanced_placement',
        *SCOPES,
    ],
)
def test_every_live_tooltip_uses_the_app_delegate(scope, tooltip_receipts):
    run = tooltip_receipts
    output = run.stdout + run.stderr
    totals = re.findall(
        r'Totals:\s+(\d+) passed, (\d+) failed, (\d+) skipped, (\d+) blacklisted', output
    )
    assert len(totals) == 1, (
        'The complete live-tooltip producer must reach exactly one Qt test summary: ' + output
    )
    passed, failed, skipped, blacklisted = map(int, totals[0])
    assert passed + failed == len(SCOPES) + 6 and skipped == blacklisted == 0, (
        'The shared tooltip producer must finish every context and both lifecycle receipts'
    )
    assert 'QFATAL' not in output and (
        run.returncode == 0 if failed == 0 else 1 <= run.returncode <= failed
    ), (
        'The complete live tooltip census exits only with its declared Qt assertion result: '
        + output
    )
    receipt = 'ToolTipStyle::' + (
        'test_' + scope + '()'
        if scope
        in {'counterexamples', 'shared_wrap_width', 'disabled_choice_class', 'balanced_placement'}
        else 'test_live_tree(' + scope + ')'
    )
    assert (
        len(
            re.findall(
                r'^PASS\s*:\s*(?:edi_app::)?' + re.escape(receipt) + r'\s*$', output, re.MULTILINE
            )
        )
        == 1
    ), 'Every tooltip context must finish exactly one actual passing Qt receipt: ' + output
    assert not re.search(
        r'^(?:FAIL!|SKIP)\s*:\s*(?:edi_app::)?' + re.escape(receipt), output, re.MULTILINE
    ), 'A missing or skipped popup cannot count as tooltip-style coverage'

    if scope not in {
        'counterexamples',
        'shared_wrap_width',
        'disabled_choice_class',
        'balanced_placement',
    }:
        rows = [
            row
            for row in re.findall(r'TOOLTIP_STYLE_CENSUS (\{[^\n]+\})', output)
            if json.loads(row)['scope'] == scope
        ]
        assert len(rows) == 1, 'Every tooltip scope must retain one actual live-tree census'
        census = json.loads(rows[0])
        print('LIVE_TOOLTIP_CENSUS ' + json.dumps(census, sort_keys=True))
        assert census['scope'] == scope and census['declared'] > 0, (
            'Tooltip coverage must identify its actual open context and instantiated app delegates'
        )
        assert census['hovered'] == census['sources'], (
            'Every discovered tooltip source must receive real hover input, or remain unqualified'
        )
        assert census['sources'] == 0 or census['rendered'] > 0, (
            'A nonempty tooltip source census must render actual tooltip delegates'
        )
