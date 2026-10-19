"""gate 8: persisted LSQ names from diffraction-lib, numbers from CLI.

Independent authoring sources: diffraction-lib develop fit_result/base.py and lsq.py;
its analysis.py defines objective chi_square and degrees of freedom n_data-n_free.
No production fit-result projection supplies these expectations.
"""

from __future__ import annotations

import json
import math
import re
import runpy
import shlex
import shutil
import sys
from operator import itemgetter
from pathlib import Path
from types import SimpleNamespace

import edi
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CASES = json.loads((ROOT / 'tests/fixtures/e05_t1/cli.json').read_text())['cases']
# Independent diffraction-lib selection, including fixed parameters and active profiles.
MODEL_COUNTS = {
    row['id']: row['n_parameters']
    for row in json.loads((ROOT / 'tests/fixtures/e05_t1/model_counts.json').read_text())['cases']
}


def scalars(text):
    output = {}
    for line in text.splitlines():
        tokens = shlex.split(line, comments=True)
        if len(tokens) == 2 and tokens[0].startswith('_fit_result.'):
            assert tokens[0] not in output, ' gate 8 persisted fit-result tags are unique'
            output[tokens[0]] = tokens[1]
    return output


def declared_background(case):
    # The authored project declaration owns identity, independently of its producer.
    models = set()
    for experiment in sorted((ROOT / case['path'] / 'experiments').glob('*.edi')):
        tags = [
            shlex.split(line)[1]
            for line in experiment.read_text().splitlines()
            if line.startswith('_background.type ')
        ]
        models.add(tags[0] if tags else 'line-segment')
    assert len(models) == 1, (
        ' gate 8 these registered codec witnesses declare one shared background'
    )
    return next(iter(models))


def projection(case):
    record = case['record']
    n = int(record['n_points_fitted'])
    free = int(record['n_free'])
    return {
        'success': record['converged'],
        'message': record['status'],
        'iterations': record['iterations'],
        'fitting_time': '123.375',  # Synthetic codec seam; a fit's duration is not a golden.
        'reduced_chi_square': record['reduced_chi_square'],
        'result_kind': 'deterministic',
        'objective_name': 'chi_square',
        'objective_value': str(float(record['reduced_chi_square']) * max(n - free, 0)),
        'n_data_points': str(n),
        'n_parameters': str(MODEL_COUNTS[case['id']]),
        'n_free_parameters': str(free),
        'degrees_of_freedom': str(max(n - free, 0)),
        'covariance_available': 'true',
        'exit_reason': record['status'],
        'prof_wr_factor': record['rwp'],
        'profile_function': 'cwl-tch-pseudo-voigt-fcj',
        'background_function': declared_background(case),
    }


def test_cli_fixture_inventory():
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    expected = {
        row['id']
        for row in registry
        if str(edi.Project.load(ROOT / 'docs/user/cli' / row['id'] / 'project').fitting_mode)
        in {'single', 'joint'}
    }
    assert len(CASES) == len(expected) and {row['id'] for row in CASES} == expected, (
        ' gate 1 every registered single and joint project has exactly one CLI fixture; '
        f'missing={sorted(expected - {row["id"] for row in CASES})}'
    )
    for row in CASES:
        record = ROOT / 'tests/fixtures/e05_t1' / (row['id'] + '.record')
        assert record.is_file(), (
            ' gate 1 every CLI fixture must retain its complete machine record'
        )
        assert (
            dict(line.split('=', 1) for line in record.read_text().splitlines()) == row['record']
        ), ' gate 1 the complete CLI record must match its frozen manifest witness'
    assert set(MODEL_COUNTS) == expected, (
        ' gate 8 every CLI fixture has an independent selected-model count'
    )
    assert all(MODEL_COUNTS[row['id']] > int(row['record']['n_free']) for row in CASES), (
        ' gate 8 selected-model counts include fixed parameters as well as fitted ones'
    )
    assert MODEL_COUNTS['pd-neut-cwl_lbco-hrpt_start-2'] < len(
        next(row for row in CASES if row['id'] == 'pd-neut-cwl_lbco-hrpt_start-2')['parameters']
    ), ' gate 8 inactive profile fields cannot inflate the CW selected-model count'
    native_ids = re.findall(
        r'^\{("[^"\n]+"),', (ROOT / 'tests/fixtures/e05_t1/cli.hpp').read_text(), re.MULTILINE
    )
    native_ids = [json.loads(token) for token in native_ids]
    assert len(native_ids) == len(expected) and set(native_ids) == expected, (
        ' gate 1 the actual-app native inventory contains every registered CLI project '
        'exactly once, including each newly registered background-model example'
    )
    assert {row['mode'] for row in CASES} == {'single', 'joint'}, (
        ' gate 1 fixture inventory exercises both declared fitting modes'
    )


def codec_copy(case, target):
    shutil.copytree(ROOT / case['path'], target)
    # Persistence does not calculate a pattern: retain real measured rows and the
    # complete model, while historical result counts keep their CLI provenance.
    for experiment in (target / 'experiments').glob('*.edi'):
        lines = experiment.read_text().splitlines()
        first = next(i for i, line in enumerate(lines) if line.startswith('_data.'))
        while first < len(lines) and (not lines[first].strip() or lines[first].startswith('_')):
            first += 1
        experiment.write_text('\n'.join(lines[: first + 3]) + '\n')
    return target


@pytest.mark.parametrize('case', CASES, ids=itemgetter('id'))
def test_persisted_cli_projection_survives_load_and_save(case, tmp_path):
    source = tmp_path / 'source'
    codec_copy(case, source)
    analysis = source / 'analysis/analysis.edi'
    reference = projection(case)
    analysis.write_text(
        analysis.read_text()
        + '\n'
        + ''.join(f'_fit_result.{key} {shlex.quote(value)}\n' for key, value in reference.items())
    )
    project = edi.Project.load(source)
    saved = tmp_path / 'saved'
    project.save_as(saved)
    actual = scalars((saved / 'analysis/analysis.edi').read_text())
    assert set(actual) == {'_fit_result.' + key for key in reference}, (
        ' gate 8 load/save retains supported diffraction-lib result fields '
        'and omits unavailable metrics'
    )
    numeric = {
        'iterations',
        'fitting_time',
        'reduced_chi_square',
        'objective_value',
        'n_data_points',
        'n_parameters',
        'n_free_parameters',
        'degrees_of_freedom',
        'prof_wr_factor',
    }
    for key, expected in reference.items():
        value = actual['_fit_result.' + key]
        if key in numeric:
            assert math.isclose(float(value), float(expected), rel_tol=5e-9, abs_tol=5e-10), (
                ' gate 8 persisted CLI numbers survive reopening at parity precision'
            )
        else:
            assert value == expected, (
                ' gate 8 result identity status and model-function strings survive reopening'
            )
    reopened = edi.Project.load(saved)
    again = tmp_path / 'again'
    reopened.save_as(again)
    assert scalars((again / 'analysis/analysis.edi').read_text()) == actual, (
        ' gate 8 repeated reopening preserves the last-fit category without drift'
    )


@pytest.mark.parametrize('case', CASES, ids=itemgetter('id'))
def test_legacy_project_without_fit_result_keeps_model_state(case, tmp_path):
    project = edi.Project.load(codec_copy(case, tmp_path / 'source'))
    before = [(p.value, p.uncertainty, p.free) for p in project.parameters]
    target = tmp_path / 'saved'
    project.save_as(target)
    assert not scalars((target / 'analysis/analysis.edi').read_text()), (
        ' gate 8 saving a legacy project invents no fit result'
    )
    after = edi.Project.load(target)
    assert [(p.value, p.uncertainty, p.free) for p in after.parameters] == before, (
        ' gate 8 files lacking the category load with unchanged values errors and free flags'
    )


@pytest.mark.parametrize('status', ['done', 'cancelled', 'maxiter', 'nostep'])
def test_result_descent_provenance_survives_current_setting_change(status, tmp_path):
    case = next(row for row in CASES if row['id'] == 'pd-neut-cwl_lbco-hrpt_start-2')
    source = tmp_path / 'source'
    shutil.copytree(ROOT / case['path'], source)
    reference = projection(case)
    reference['descent'] = case['record']['descent']
    reference['exit_reason'] = reference['message'] = status
    reference['success'] = 'true' if status == 'done' else 'false'
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\n'
        + ''.join(f'_fit_result.{key} {shlex.quote(value)}\n' for key, value in reference.items())
    )
    project = edi.Project.load(source)
    project.descent = 'fast_descent' if reference['descent'] != 'fast_descent' else 'ladder'
    saved = tmp_path / 'saved'
    project.save_as(saved)
    actual = scalars((saved / 'analysis/analysis.edi').read_text())
    assert actual.get('_fit_result.descent') == reference['descent'], (
        ' gate 8 producing CLI minimizer remains attached '
        'to completed and cancelled historical results'
    )
    assert actual['_fit_result.exit_reason'] == status, (
        ' gate 8 provenance retention preserves the terminal reason'
    )
    again = tmp_path / 'again'
    reopened = edi.Project.load(saved)
    assert str(reopened.descent) != reference['descent'], (
        ' gate 8 current minimizer is an independent changed-setting control'
    )
    reopened.save_as(again)
    assert scalars((again / 'analysis/analysis.edi').read_text()) == actual, (
        ' gate 8 repeated reopen never reconstructs historical descent from mutable settings'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'cli-omission',
        'cli-duplicate',
        'count-omission',
        'native-omission',
        'record-omission',
        'record-change',
    ],
)
def test_registered_fit_inventory_refuses_missing_or_duplicate_witnesses(escape, monkeypatch):
    module = sys.modules[__name__]
    project_id = 'pd-neut-cwl_yap-spodi_3k'
    original_project = edi.Project
    observed_modes = {}

    def observed_load(path):
        project = original_project.load(path)
        observed_modes[path] = str(project.fitting_mode)
        return project

    # The positive caller loads every real registered input once. The negative
    # caller reuses those observed modes while changing only its fixture witness;
    # this avoids repeating unrelated scientific parsing for each escape.
    monkeypatch.setattr(
        module, 'edi', SimpleNamespace(Project=SimpleNamespace(load=observed_load))
    )
    test_cli_fixture_inventory()
    monkeypatch.setattr(
        module,
        'edi',
        SimpleNamespace(
            Project=SimpleNamespace(
                load=lambda path: SimpleNamespace(fitting_mode=observed_modes[path])
            )
        ),
    )
    if escape == 'cli-omission':
        monkeypatch.setattr(module, 'CASES', [row for row in CASES if row['id'] != project_id])
    elif escape == 'cli-duplicate':
        monkeypatch.setattr(
            module, 'CASES', [*CASES, next(r for r in CASES if r['id'] == project_id)]
        )
    elif escape == 'count-omission':
        monkeypatch.setattr(
            module, 'MODEL_COUNTS', {k: v for k, v in MODEL_COUNTS.items() if k != project_id}
        )
    elif escape.startswith('record-'):
        record = ROOT / 'tests/fixtures/e05_t1' / (project_id + '.record')
        if escape == 'record-omission':
            original_is_file = Path.is_file
            monkeypatch.setattr(
                Path, 'is_file', lambda path: False if path == record else original_is_file(path)
            )
        else:
            original_read = Path.read_text
            monkeypatch.setattr(
                Path,
                'read_text',
                lambda path, *a, **kw: (
                    'mode=wrong\n' if path == record else original_read(path, *a, **kw)
                ),
            )
    else:
        original_read = Path.read_text
        header = ROOT / 'tests/fixtures/e05_t1/cli.hpp'

        def without_native_case(path, *args, **kwargs):
            content = original_read(path, *args, **kwargs)
            if path == header:
                content = '\n'.join(
                    line
                    for line in content.splitlines()
                    if not line.startswith('{"' + project_id + '"')
                )
            return content

        monkeypatch.setattr(Path, 'read_text', without_native_case)
    with pytest.raises(AssertionError, match=r'gate [18]'):
        test_cli_fixture_inventory()


@pytest.mark.parametrize('stalled', [False, True], ids=['zero-gain', 'domain-stall'])
def test_zero_gain_converges_and_domain_blocked_positive_gain_stalls(stalled, tmp_path):
    materialize = runpy.run_path(str(ROOT / 'tests/fixtures/e05_t1/stop_projects.py'))[
        'materialize'
    ]
    source = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
    project = edi.Project.load(materialize(edi, source, tmp_path / 'source', stalled=stalled))
    outcome = project.analysis.fit()
    expected_status = edi.FitStatus.NO_STEP if stalled else edi.FitStatus.DONE
    assert outcome.status == expected_status, (
        'a zero-gain column must converge; a positive-gain column whose trials all leave '
        'the declared domain must remain a genuine stall'
    )
    assert outcome.converged == (not stalled), (
        'the predicted-gain distinction must agree with the public convergence flag'
    )
    if stalled:
        assert outcome.iterations == 1, (
            'the domain witness must reject every proposal in its first iteration'
        )
        assert outcome.reduced_chi_square == pytest.approx(1.5, rel=0.0, abs=1e-12), (
            'three residuals of one with one free parameter must retain chi-square over '
            'two degrees of freedom after the rejected descent'
        )
        assert project.structure.atom_sites[0].adp_iso.value == pytest.approx(
            0.0, rel=0.0, abs=0.0
        ), 'rejected negative proposals must preserve the declared zero driver'
    project.save_as(str(tmp_path / 'saved'))
    persisted = scalars((tmp_path / 'saved/analysis/analysis.edi').read_text())
    assert persisted.get('_fit_result.exit_reason') == ('no_step' if stalled else 'done'), (
        'saving a live stop result must preserve the actual terminal reason'
    )
    assert persisted.get('_fit_result.success') == ('false' if stalled else 'true'), (
        'saving a live stop result must preserve the predicted-gain success distinction'
    )


def test_committed_nostep_witness_has_positive_gain_and_only_domain_rejections():
    cases = json.loads((ROOT / 'tests/fixtures/e05_t1/stops.json').read_text())['cases']
    case = next(row for row in cases if row['id'] == 'stop-nostep')
    record = case['record']
    assert record['status'] == 'no_step' and record['converged'] == 'false', (
        'the committed app witness must remain a genuine nonconverged stop'
    )
    assert int(record['iterations']) == 1 and int(record['n_free']) == 1, (
        'the app stall must retain one free driver and no accepted iteration'
    )
    assert int(record['terminal_unevaluable_trials']) > 0, (
        'the app stall must reject real out-of-domain proposals rather than a zero-gain column'
    )
    assert record['terminal_unevaluable_trials'] == record['unevaluable_trials'], (
        'every domain rejection must belong to the only executed iteration'
    )
    assert record['nonfinite_trials'] == '0', (
        'the authored stall must arise from its declared domain with finite arithmetic'
    )
    assert int(record['n_points_fitted']) == 3 and float(record['reduced_chi_square']) == 1.5, (
        'the app witness must retain the independently declared three unit residuals'
    )
    expected = case['closed_form']
    assert expected['predicted_gain'] == 3.0 and expected['chi_square'] == 3.0, (
        'the independently derived scalar gradient and normal matrix give positive gain three'
    )
