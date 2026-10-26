"""An adopting save recalculates rounded current inputs without consuming due estimates."""

import importlib
import re
import shutil

import numpy as np
import pytest

from tests.fixtures.project_save.review2 import agreement, bank_state, prepared_mixed
from tests.integration.py.test_anisotropic_adps import loop_rows

ENGINE = importlib.import_module('edi')


def digests(path):
    return dict(re.findall(r'(?m)^(_background_estimate\.\w+_digest)\s+(\S+)', path.read_text()))


@pytest.mark.parametrize('empty', [False, True], ids=['points', 'empty'])
@pytest.mark.parametrize('provenance', ['stale', 'absent'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
def test_due_background_state_is_exact_in_memory_and_file_beside_a_rounded_current_bank(
    tmp_path, empty, provenance, operation
):
    project, source = prepared_mixed(
        ENGINE, tmp_path / 'input', empty=empty, provenance=provenance
    )
    due = project.experiments['due']
    before = bank_state(due)
    expected_digest = digests(source / 'experiments/due.edi')
    assert bool(before['rows']) is not empty, 'The due witness exercises populated and empty bases'
    assert before['mode'] == 'auto', (
        'The measured due bank explicitly requests automatic estimation'
    )
    if not empty:
        assert before['rows'][0][2].hex() == float('2.34567891').hex(), (
            'The due witness starts at an independently authored precision beyond six digits'
        )
    destination = source if operation == 'save' else tmp_path / 'saved'
    project.save() if operation == 'save' else project.save_as(destination)
    assert bank_state(due) == before, (
        'An adopting save never estimates, rounds or changes any due-bank row, constant, '
        'free flag, mode or option while another bank needs rounded-input recalculation'
    )
    again = ENGINE.Project.load(destination)
    assert bank_state(again.experiments['due']) == before, (
        'The file preserves the complete exact due background, including an empty automatic basis'
    )
    assert digests(destination / 'experiments/due.edi') == expected_digest, (
        'Save retains the due bank input and point digests exactly, including absent provenance'
    )


@pytest.mark.parametrize('empty', [False, True], ids=['points', 'empty'])
@pytest.mark.parametrize('provenance', ['stale', 'absent'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
def test_current_bank_inputs_arrays_and_factors_match_independent_rounded_calculation(
    tmp_path, empty, provenance, operation
):
    project, source = prepared_mixed(
        ENGINE, tmp_path / 'input', empty=empty, provenance=provenance
    )
    bank = project.experiments['current']
    before = np.array([
        float(row['_data.intensity_calc'])
        for row in loop_rows((source / 'experiments/current.edi').read_text(), '_data')
    ])
    np.testing.assert_array_equal(
        before,
        np.full(4, 1.23456789),
        err_msg='Zero scale and constant background give the independently authored pattern',
    )
    destination = source if operation == 'save' else tmp_path / 'saved'
    project.save() if operation == 'save' else project.save_as(destination)
    expected = np.full(4, 1.23457)
    np.testing.assert_array_equal(
        bank.data.intensity_calc,
        expected,
        err_msg='The live current bank recalculates from independently six-digit-rounded inputs',
    )
    assert not np.array_equal(before, expected), 'The rounding witness actually moves the pattern'
    assert [point.intensity.value for point in bank.background] == [1.23457, 1.23457], (
        'The live current inputs adopt the rounded values used to calculate the saved pattern'
    )
    again = ENGINE.Project.load(destination)
    np.testing.assert_array_equal(
        again.experiments['current'].data.intensity_calc,
        expected,
        err_msg='Reopened current-bank calculated columns equal the live adopted pattern',
    )
    single = tmp_path / 'fresh-current'
    shutil.copytree(destination, single)
    (single / 'experiments/due.edi').unlink()
    analysis = single / 'analysis/analysis.edi'
    analysis.write_text(re.sub(r'(?m)^due .*\n', '', analysis.read_text()))
    fresh = ENGINE.Project.load(single)
    fresh.calculate()
    np.testing.assert_array_equal(
        fresh.experiment.data.intensity_calc,
        expected,
        err_msg='A fresh independent current-only reopen and calculation reproduces saved columns',
    )
    rows = loop_rows((destination / 'analysis/analysis.edi').read_text(), '_fit_result_bank')
    current = next(
        (row for row in rows if row['_fit_result_bank.experiment_id'] == 'current'), None
    )
    assert current is not None, 'The saved current bank retains a real agreement-factor record'
    reference = agreement(1.23457)
    for name, value in reference.items():
        assert float(current['_fit_result_bank.' + name]) == pytest.approx(
            float(format(value, '.6g')), rel=1e-12
        ), (
            'Saved agreement factors follow an independent weighted-residual calculation '
            'from rounded current inputs'
        )
