"""Current catalogue custody accepts only the two independently archived states."""

from pathlib import Path

import pytest

from tests.fixtures.e04_t11_wasm import written
from tests.fixtures.metadata_transition import task_inputs

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_each_catalogue_source_pair_is_exact_and_idempotent(case):
    name = 'docs/user/cli/' + written.CASES[case] + '/project/analysis/analysis.edi'
    row = task_inputs.rows()[name]
    original = task_inputs.archived(row['before_sha256'])
    for state in ('before_sha256', 'after_sha256'):
        data = task_inputs.archived(row[state])
        recovered = task_inputs.previous_bytes(name, data)
        assert recovered == original, (
            'Each authenticated endpoint projects to the exact independently archived before bytes'
        )
        assert task_inputs.previous_bytes(name, recovered) == original, (
            'Applying the exact source projection twice preserves its authenticated byte identity'
        )


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
@pytest.mark.parametrize(
    'change',
    [
        b'\n_peak.cutoff_fwhm 1.25\n',
        b'\n_minimizer.descent fast_descent\n',
        b'\n_metadata.description "unrecorded input"\n',
    ],
)
def test_source_pair_refuses_unarchived_science_condition_or_metadata(case, change):
    name = 'docs/user/cli/' + written.CASES[case] + '/project/analysis/analysis.edi'
    row = task_inputs.rows()[name]
    for state in ('before_sha256', 'after_sha256'):
        with pytest.raises(AssertionError, match='entire independently archived source'):
            task_inputs.previous_bytes(name, task_inputs.archived(row[state]) + change)


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_actual_current_catalogue_inputs_preserve_their_original_raw_custody(case):
    fixture, raw, source, _names, banks = written.inputs(ROOT, case)
    assert source == ROOT / fixture['project'] and banks, (
        'Current catalogue sources retain their original raw and conditioning capture'
    )
    assert raw['labels'] and raw['n_data'] > len(raw['labels']), (
        'No-solve custody retains complete independent raw parameter and point dimensions'
    )
