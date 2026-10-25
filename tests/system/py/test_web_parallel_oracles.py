"""Numerical and owner-baseline controls independent of the web implementation."""

import copy
import json
from pathlib import Path

import pytest

from tests.fixtures.web_parallel.numeric import compare_scientific

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/web_parallel'


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_web_fit_native_reference_covers_parameters_and_calculated_pattern(case):
    path = FIXTURE / (case + '-native.json')
    assert path.is_file(), (
        'Web fit parity requires a committed independent native fit capture for each corpus case'
    )
    oracle = json.loads(path.read_text())
    conditioning = json.loads((FIXTURE / (case + '-conditioning.json')).read_text())
    assert oracle['reference'] == 'unchanged native serial/OpenMP core, independent of wasm', (
        'Web correctness references must come from the unchanged native backend'
    )
    rows = [row for document in oracle['scientific'].values() for row in document]
    assert any('_data.intensity_calc' in row for row in rows), (
        'Native fit parity must retain calculated pattern operands, not only scalar report values'
    )
    assert any(any(token.startswith('_atom_site.') for token in row) for row in rows), (
        'Native fit parity must retain every fitted atomic parameter'
    )
    assert compare_scientific(
        oracle['scientific'], oracle['scientific'], conditioning=conditioning
    ), 'Native conditioning must certify its unchanged scientific reference'
    changed = copy.deepcopy(oracle['scientific'])
    for document in changed.values():
        for row in document:
            if '_data.intensity_calc' in row:
                # Loop tags precede their operands in the independent capture.
                count = next(index for index, token in enumerate(row) if not token.startswith('_'))
                index = count + row[:count].index('_data.intensity_calc')
                try:
                    float(row[index])
                except ValueError:
                    continue
                row[index] = 'nan'
                with pytest.raises(ValueError, match='parameter or pattern'):
                    compare_scientific(changed, oracle['scientific'], conditioning=conditioning)
                return
    pytest.fail('Native fit capture must expose a perturbable calculated pattern operand')


def test_owner_five_bank_reference_is_not_a_generated_web_pin():
    contract = json.loads((FIXTURE / 'contract.json').read_text())
    baseline = contract['baseline']
    assert (
        baseline['initial_reduced_chi_square'],
        baseline['final_reduced_chi_square'],
        baseline['rwp_percent'],
        baseline['iterations'],
    ) == (649.33, 9.50, 7.69, 5), (
        'Five-bank acceptance must retain the owner native start, end, Rwp and iterations'
    )
    assert contract['speed'] == {'minimum_core_count': 4, 'minimum_ratio': 1.4}, (
        'Web speed acceptance must use the packet ratio and minimum core count'
    )


def test_native_fit_retains_the_owner_five_iteration_final_values():
    native = json.loads((FIXTURE / 'ncaf-native.json').read_text())['native_start_and_finish']
    assert abs(native['initial_reduced_chi_square'] - 649.33) <= 0.005, (
        'Independent native pre-fit record must retain the owner rounded starting chi-square'
    )
    fields = dict(
        line.split('=', 1)
        for line in (FIXTURE / 'ncaf-native-report.txt').read_text().splitlines()
        if '=' in line
    )
    assert fields['iterations'] == '5', 'Native owner workload must converge in five iterations'
    assert abs(float(fields['reduced_chi_square']) - 9.50) <= 0.005, (
        'Independent native fit must retain the owner rounded final chi-square'
    )
    assert abs(100 * float(fields['rwp']) - 7.69) <= 0.005, (
        'Independent native fit must retain the owner rounded Rwp percentage'
    )
