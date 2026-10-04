"""gate 8: the actual CLI fit/save writes independent frozen result values."""

from __future__ import annotations

import json
import math
import shlex
import shutil
import subprocess
import sys
from operator import itemgetter
from pathlib import Path

import edi
import pytest

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
CASES = json.loads((ROOT / 'tests/fixtures/e05_t1/cli.json').read_text())['cases']
# Independent diffraction-lib selection, including fixed parameters and active profiles.
MODEL_COUNTS = {
    row['id']: row['n_parameters']
    for row in json.loads((ROOT / 'tests/fixtures/e05_t1/model_counts.json').read_text())['cases']
}
SELECTED = [c for c in CASES if c['id'] == 'pd-neut-cwl_lbco-hrpt_start-2']


def scalars(path):
    return dict(
        shlex.split(line)
        for line in path.read_text().splitlines()
        if line.startswith('_fit_result.') and len(shlex.split(line)) == 2
    )


@pytest.mark.parametrize('case', SELECTED, ids=itemgetter('id'))
def test_cli_fit_save_reopen_and_undo(case, tmp_path):
    run_cli_fit_save_reopen_and_undo(case, tmp_path)


def run_cli_fit_save_reopen_and_undo(case, tmp_path):
    source = tmp_path / 'project'
    corpus_id = 'lbco-hrpt-s2' if case['mode'] == 'single' else 'ncaf-wish-3bank-s5'
    authority = corpus_case_dir(corpus_id) / 'project'
    shutil.copytree(
        ROOT / case['path'], source, ignore=shutil.ignore_patterns('experiments', 'structures')
    )
    for category in ('experiments', 'structures'):
        expected = {p.name: p.read_bytes() for p in (ROOT / case['path'] / category).glob('*.edi')}
        actual = {p.name: p.read_bytes() for p in (authority / category).glob('*.edi')}
        assert actual == expected, (
            ' gate 8 CLI save oracle uses exactly the pinned corpus data and structures'
        )
        # A default CLI save writes these directories: never link to the shared SDK corpus.
        shutil.copytree(authority / category, source / category)
    authority_before = {
        p.relative_to(authority): p.read_bytes() for p in authority.rglob('*') if p.is_file()
    }
    run = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(source),
            '--report',
            'machine',
            '--verbosity',
            'full',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert run.returncode == 0, (
        ' gate 8 independent CLI fit-and-save succeeds on its registered project'
    )
    actual = scalars(source / 'analysis/analysis.edi')
    assert '_fit_result.iterations' in actual, (
        ' gate 8 CLI default save writes the persisted fit-result category'
    )
    reference = case['record']
    for field, record in [
        ('iterations', 'iterations'),
        ('reduced_chi_square', 'reduced_chi_square'),
        ('prof_wr_factor', 'rwp'),
        ('n_data_points', 'n_points_fitted'),
        ('n_free_parameters', 'n_free'),
    ]:
        assert math.isclose(
            float(actual['_fit_result.' + field]),
            float(reference[record]),
            rel_tol=5e-9,
            abs_tol=5e-10,
        ), ' gate 8 saved fit metrics equal the author-time CLI fixture'
    assert float(actual['_fit_result.fitting_time']) > 0, (
        ' gate 8 fit duration is present positive seconds and never a frozen expectation'
    )
    assert actual['_fit_result.success'].lower() == reference['converged'], (
        ' gate 8 saved success matches CLI convergence'
    )
    assert actual['_fit_result.result_kind'] == 'deterministic', (
        ' gate 8 saved least-squares kind uses diffraction-lib vocabulary'
    )
    check_projection(actual, reference, MODEL_COUNTS[case['id']])
    if case['mode'] == 'joint':
        check_banks(source / 'analysis/analysis.edi', reference)
    assert actual.get('_fit_result.descent') == reference['descent'], (
        ' gate 8 actual CLI save binds the producing minimizer to the result'
    )
    reopened = edi.Project.load(source)
    reopened.descent = 'fast_descent' if reference['descent'] != 'fast_descent' else 'ladder'
    saved = tmp_path / 'reopened'
    reopened.save_as(saved)
    assert scalars(saved / 'analysis/analysis.edi') == actual, (
        ' gate 8 reopening and saving restore all result metadata'
    )
    if case['mode'] == 'joint':
        check_banks(saved / 'analysis/analysis.edi', reference)
    undo = subprocess.run(
        [sys.executable, '-m', 'edi', 'undo', str(source), '--report', 'machine'],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert undo.returncode == 0, ' gate 8 the CLI Undo path accepts the persisted fit start'
    assert not scalars(source / 'analysis/analysis.edi'), (
        ' gate 8 Undo clears the saved last-fit category'
    )

    assert {
        p.relative_to(authority): p.read_bytes() for p in authority.rglob('*') if p.is_file()
    } == authority_before, ' gate 8 fit/save/reopen/Undo leave the shared corpus byte-identical'


def check_projection(actual, reference, parameter_count):
    required = {
        'success',
        'message',
        'iterations',
        'fitting_time',
        'reduced_chi_square',
        'result_kind',
        'objective_name',
        'objective_value',
        'n_data_points',
        'n_parameters',
        'n_free_parameters',
        'degrees_of_freedom',
        'covariance_available',
        'exit_reason',
        'prof_wr_factor',
        'profile_function',
        'background_function',
    }
    assert required <= {key.removeprefix('_fit_result.') for key in actual}, (
        ' gate 8 fit-and-save includes every computable diffraction-lib field'
    )
    unsupported = {
        'prof_r_factor',
        'prof_wr_expected',
        'correlation_available',
        'number_restraints',
        'number_constraints',
        'shift_over_su_max',
        'shift_over_su_mean',
        'r_factor_all',
        'wr_factor_all',
        'r_factor_gt',
        'wr_factor_gt',
    }
    assert not unsupported & {key.removeprefix('_fit_result.') for key in actual}, (
        ' gate 8 unavailable powder and single-crystal metrics are omitted'
    )
    dof = max(int(reference['n_points_fitted']) - int(reference['n_free']), 0)
    assert int(actual['_fit_result.degrees_of_freedom']) == dof, (
        ' gate 8 degrees of freedom uses fitted data minus CLI free parameters'
    )
    assert actual['_fit_result.objective_name'] == 'chi_square', (
        ' gate 8 objective identity matches diffraction-lib least-squares projection'
    )
    assert math.isclose(
        float(actual['_fit_result.objective_value']),
        float(reference['reduced_chi_square']) * dof,
        rel_tol=5e-9,
        abs_tol=5e-10,
    ), ' gate 8 objective is unreduced chi-square rather than reduced chi-square'
    assert int(actual['_fit_result.n_parameters']) == parameter_count, (
        ' gate 8 parameter count uses independent selected-model semantics'
    )
    for field in ('profile_function', 'background_function', 'message', 'exit_reason'):
        assert actual['_fit_result.' + field] not in {'', '?', '.'}, (
            ' gate 8 computed function and stop metadata have real values'
        )


def check_banks(path, reference):
    # : compare declared metrics, never numerical membership in a row.
    tokens = shlex.split(path.read_text(), comments=True)
    banks = []
    cursor = 0
    while cursor < len(tokens):
        if tokens[cursor] != 'loop_':
            cursor += 1
            continue
        cursor += 1
        tags = []
        while cursor < len(tokens) and tokens[cursor].startswith('_'):
            tags.append(tokens[cursor])
            cursor += 1
        is_bank = any(tag.startswith('_fit_result_bank.') for tag in tags)
        if is_bank:
            required = {
                '_fit_result_bank.experiment_id',
                '_fit_result_bank.n_data_points',
                '_fit_result_bank.prof_wr_factor',
                '_fit_result_bank.chi_square',
            }
            assert set(tags) == required, (
                ' gate 8 bank-result columns retain their exact declared identities'
            )
            assert len(tags) == len(required), ' gate 8 bank column identities are unique'
        while (
            tags
            and cursor < len(tokens)
            and not tokens[cursor].startswith(('_', 'data_', 'loop_'))
        ):
            row = tokens[cursor : cursor + len(tags)]
            assert len(row) == len(tags), ' gate 8 persisted loop rows have complete cardinality'
            if is_bank:
                banks.append(dict(zip(tags, row, strict=True)))
            cursor += len(tags)
    names = {key[5:-4] for key in reference if key.startswith('bank.') and key.endswith('.rwp')}
    identities = [row['_fit_result_bank.experiment_id'] for row in banks]
    assert len(identities) == len(names), (
        ' gate 8 persisted bank identities cover exactly the CLI banks without duplicates'
    )
    assert set(identities) == names, (
        ' gate 8 bank identities equal exactly the independent CLI set'
    )
    for row in banks:
        name = row['_fit_result_bank.experiment_id']
        for metric, column in (('rwp', 'prof_wr_factor'), ('chi_square', 'chi_square')):
            assert math.isclose(
                float(row['_fit_result_bank.' + column]),
                float(reference['bank.' + name + '.' + metric]),
                rel_tol=5e-9,
                abs_tol=5e-10,
            ), ' gate 8 each named bank metric retains its own independent CLI value'
        assert int(row['_fit_result_bank.n_data_points']) == int(
            reference['bank.' + name + '.n_points']
        ), ' gate 8 each bank retains its exact independently fitted point count'
