"""Every physical quantity has one setting across the actual workflow selectors."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ROUTES = {
    'x': [
        'structure-Pattern',
        'experiment-Pattern',
        'analysis-Pattern',
        'analysis-Stacked',
        'analysis-Map',
    ],
    'intensity': [
        'structure-Pattern',
        'experiment-Pattern',
        'analysis-Pattern',
        'analysis-Stacked',
        'analysis-Map',
    ],
    'rows': ['analysis-Stacked', 'analysis-Map', 'analysis-Evolution'],
}


@pytest.fixture(scope='module')
def axis_receipt():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Quantity sharing requires the real native workflow host'
    result = subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_scan_axis_sync.qml'),
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    output = result.stdout + result.stderr
    print(output)
    assert (
        result.returncode >= 0
        and 'Totals:' in output
        and '::ScanAxisSync::cleanupTestCase()' in output
    ), 'An incomplete or crashed quantity-sharing actor cannot produce passing receipts'
    return output


@pytest.mark.parametrize(
    'case', [f'{quantity}-{origin}' for quantity, routes in ROUTES.items() for origin in routes]
)
def test_scan_axis_quantity_is_shared(axis_receipt, case):
    witness = f'::ScanAxisSync::test_each_quantity_is_shared_both_directions({case})'
    lines = [line for line in axis_receipt.splitlines() if witness in line]
    assert any(line.startswith('PASS ') for line in lines) and not any(
        line.startswith(('FAIL', 'SKIP')) for line in lines
    ), 'Both actual input directions propagate the same physical quantity: ' + '\n'.join(lines)
