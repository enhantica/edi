"""The LaM7O3 start must not finish before its useful linear polish."""

import json
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'docs/user/cli/pd-xray-cwl_lam7o3-p021/project'


def fitted():
    project = edi.Project.load(PROJECT)
    project.analysis.descent = 'ladder'
    outcome = project.analysis.fit()
    record = edi.machine_report(project, outcome, edi.VerbosityEnum.FULL)
    fields = dict(line.split('=', 1) for line in record.splitlines() if '=' in line)
    return project, fields


def test_default_descent_reaches_the_frozen_fast_descent_regression_witness():
    project, fields = fitted()
    assert fields['status'] == 'done', 'The default descent must complete from the committed start'
    # Recorded before the solver change; this is a regression witness, not a physical oracle.
    assert float(fields['rwp']) == pytest.approx(0.0164, rel=0.02), (
        'The default descent must reach the pre-change fast-descent regression witness'
    )
    oxygen = project.structures['lam7o3'].atom_sites['O1'].fract_x
    assert oxygen.value == pytest.approx(0.5078, abs=0.0022), (
        'The default descent must leave the premature O1 coordinate near the half position'
    )


def test_a_converged_result_cannot_gain_materially_on_an_immediate_default_refit():
    project, first = fitted()
    outcome = project.analysis.fit()
    record = edi.machine_report(project, outcome, edi.VerbosityEnum.FULL)
    second = dict(line.split('=', 1) for line in record.splitlines() if '=' in line)
    assert float(second['reduced_chi_square']) >= float(first['reduced_chi_square']) * (
        1 - 1e-3
    ), 'A convergence verdict must survive a fresh descent from its own polished state'


def test_default_variant_is_also_bound_to_the_independent_fullprof_reference():
    reference = ROOT / 'knowledge/fitting/fullprof/pd-xray-cwl_lam7o3-p021/reference.json'
    assert reference.is_file(), 'The default descent needs a same-start FullProf reference'
    expected = json.loads(reference.read_text())
    assert expected['program'] == 'FullProf' and expected['same_start'], (
        'The physical minimum claim must come from FullProf at the committed project start'
    )
    _project, fields = fitted()
    assert float(fields['rwp']) == pytest.approx(expected['r_wp'], rel=0.05), (
        'The default descent must fit within the FullProf agreement-factor tolerance'
    )
    for name, value in expected['parameters'].items():
        assert float(fields[f'param.{name}.value']) == pytest.approx(
            value, abs=2 * float(fields[f'param.{name}.uncertainty'])
        ), 'Shared fitted values must agree with FullProf within two standard uncertainties'
