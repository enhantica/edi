"""Exercise bond cutoffs and probe-dependent atom types through actual Structure controls."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_bond_cutoffs_change_displayed_cubic_distances_and_persist',
    *[
        f'test_active_probe_types_and_element_colour_regression_pin:{probe}'
        for probe in ('neutron', 'neutron-sears', 'xray')
    ],
]


@pytest.mark.parametrize('case', CASES)
def test_real_structure_bonds_and_probe_types(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Structure bond and atom-type acceptance requires the actual Qt host'
    status, output = capture(
        [
            binary,
            '-input',
            ROOT / 'tests/unit/app/tst_structure_bonds_and_types.qml',
            'StructureBondsAndTypes::' + case,
        ],
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert 'Could not find the following test functions' not in output, (
        'The requested native Structure function resolves before product behavior is judged'
    )
    assert status == 0, (
        'Real Structure controls satisfy the independent geometry and profile contract: ' + output
    )
    function, _, tag = case.partition(':')
    expected = f'{function}({tag})' if tag else f'{function}()'
    assert expected in output and '0 failed' in output, (
        'The requested Structure geometry or atom-type function reaches its actual assertions'
    )
    assert 'SKIP' not in output, (
        'Each independent Structure geometry and profile contract executes'
    )
