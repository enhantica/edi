"""Disabled entries retain their own rendered symbols and Bragg-strip names."""

import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = []
for page in ('experiment', 'analysis'):
    for count in ('one', 'many'):
        kinds = ['meas', 'calc', 'bkg', 'resid', 'bragg0']
        if count == 'many':
            kinds.append('bragg1')
        CASES.extend(f'test_symbol:{page}-{count}-{kind}' for kind in kinds)
        CASES.extend(
            f'test_strip:{page}-{count}-{kind}' for kind in kinds if kind.startswith('bragg')
        )
    CASES.append(f'test_symbol:{page}-single')


@pytest.fixture(scope='module')
def symbol_receipts():
    receipts = {}
    for case in CASES:
        receipts[case] = capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/LegendSymbols.qml',
                '-o',
                '-,txt',
                'LegendSymbols::' + case,
            ],
            timeout=60,
        )
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_hidden_entry_retains_its_own_drawn_symbols(symbol_receipts, case):
    status, output = symbol_receipts[case]
    assert status == 0, 'Hidden legend symbols and Bragg-strip labels must complete: ' + output
    name, _, tag = case.partition(':')
    assert f'PASS   : edi_app::LegendSymbols::{name}({tag})' in output, (
        'Every requested entry type, structure count and page executes in the actual host'
    )
    assert '::LegendSymbols::cleanupTestCase()' in output, (
        'Every symbol witness completes after actual hidden and restored rendered states'
    )
