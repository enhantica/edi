"""Public CLI lifecycle and isolated numeric-domain boundaries."""

import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import edi as engine
import numpy as np
import pytest

from tests.conftest import corpus_case_dir, crysta_reference_prefix
from tests.fixtures.background_estimate.generate_saved_lifecycle import saved_digests
from tests.fixtures.background_estimate.lifecycle import (
    INVALID,
    edit,
    expected_background,
    model_input,
    persisted_points,
    prime,
)
from tests.fixtures.background_estimate.settings import points, read_settings

ROOT = Path(__file__).resolve().parents[3]
SOURCE = corpus_case_dir('lbco-hrpt-s2') / 'project'


def cli_command(project, operation='calc'):
    return [sys.executable, '-m', 'edi', operation, str(project)]


def run_cli(project, operation='calc'):
    command = cli_command(project, operation)
    completed = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    assert completed.returncode == 0, (
        'The ordinary CLI must finish the background lifecycle operation '
        'without invalid references: ' + completed.stderr
    )


@pytest.mark.parametrize('kind', ['position', 'intensity', 'free', 'add', 'remove'])
@pytest.mark.parametrize('transition', [False, True], ids=['loaded-auto', 'manual-to-auto'])
@pytest.mark.parametrize('operation', ['calc', 'fit'])
def test_cli_preserves_a_hand_edit_saved_before_the_first_estimate(
    tmp_path, kind, transition, operation
):
    source = model_input(tmp_path / 'input', SOURCE, mode='manual' if transition else 'auto')
    experiment = source / 'experiments/hrpt.edi'
    experiment.write_text(re.sub(r'(?<=\d)\(\)', '', experiment.read_text()))
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(
        re.sub(
            r'(?m)^_minimizer.max_iterations .*$',
            '_minimizer.max_iterations 1',
            analysis.read_text(),
        )
    )
    project = engine.Project.load(source)
    if transition:
        project.experiment.background_estimate.mode = 'auto'
    # Auto allows fit flags; the CLI persistence control then selects Manual explicitly.
    before = points(project)
    # Before: free was refused. After: either free/fixed direction is permitted in Auto.
    if kind == 'free':
        edit(project, engine, kind)
        expected_flag = [(*before[0][:-1], not before[0][-1]), *before[1:]]
        assert points(project) == expected_flag, (
            'Auto must permit a free/fixed toggle without changing point values or layout'
        )
        assert project.experiment.background_estimate.mode == 'auto', (
            'A permitted free/fixed toggle must preserve Auto before the next operation'
        )
        edit(project, engine, kind)
    else:
        with pytest.raises(ValueError, match=r'(?i)manual'):
            edit(project, engine, kind)
    assert points(project) == before, (
        'A reverse free toggle or refused value edit must preserve the original Auto points'
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'Permitted flag toggles and refused value edits must leave Auto selected'
    )
    project.experiment.background_estimate.mode = 'manual'
    edit(project, engine, kind)
    expected = [row[:2] for row in points(project)]
    project.save_as(tmp_path / 'saved')
    run_cli(tmp_path / 'saved', operation)
    assert read_settings(tmp_path / 'saved', experiment='hrpt')['mode'] == 'manual', (
        'Both CLI calculate and fit must retain manual mode after an edit '
        'before the first estimate'
    )
    actual = persisted_points(tmp_path / 'saved', experiment='hrpt')
    if operation == 'fit' and kind == 'free':
        assert [row[0] for row in actual] == [row[0] for row in expected], (
            'A fit may optimize a deliberately freed height but must preserve '
            'its manual row layout'
        )
        assert engine.Project.load(tmp_path / 'saved').experiment.background[0].intensity.free, (
            'The first CLI fit must retain the hand-edited free flag instead '
            'of estimating fixed points'
        )
        return
    assert actual == expected, (
        'The CLI must not overwrite pre-estimate hand-edited positions, heights or row counts'
    )


@pytest.mark.parametrize('route', ['direct', 'setting', 'load'])
@pytest.mark.parametrize(('field', 'token'), INVALID)
def test_invalid_overrides_refuse_without_mutation_in_an_isolated_process(
    tmp_path, route, field, token
):
    source = model_input(tmp_path / 'input', SOURCE)
    command = [
        sys.executable,
        '-m',
        'tests.fixtures.background_estimate.lifecycle',
        'edi',
        str(source),
        route,
        field,
        token,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert completed.returncode == 0, (
        'Invalid numeric overrides must produce an ordinary refusal '
        'rather than crash or overflow: ' + completed.stderr
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result['refused'], (
        'Direct calls, stored settings and loaders must refuse nonfinite '
        'or unrepresentable overrides: ' + field + '=' + token + ' through ' + route
    )
    assert result['unchanged'], 'Refusing an override must preserve every point and stored setting'


@pytest.mark.parametrize('method', ['arpls', 'fabc'])
@pytest.mark.parametrize('token', ['inf', '8589934592.25'])
def test_each_estimator_refuses_bad_windows_before_mutation(tmp_path, method, token):
    source = model_input(tmp_path / 'input', SOURCE)
    completed = subprocess.run(
        [
            sys.executable,
            '-m',
            'tests.fixtures.background_estimate.lifecycle',
            'edi',
            str(source),
            'direct',
            'width',
            token,
            method,
        ],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert completed.returncode == 0, (
        'Every Stage-1 method must reject invalid windows without undefined conversion: '
        + completed.stderr
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result['refused'], (
        'Every method must enforce the same finite representable width domain'
    )
    assert result['unchanged'], (
        'A refused method-specific override must leave model state unchanged'
    )


def saved_auto_input():
    directory = ROOT / 'tests/fixtures/background_estimate'
    receipt = json.loads((directory / 'placed-lifecycle.json').read_text())
    assert receipt['claim'].startswith('REGRESSION INPUT:'), (
        'Engine-authored saved state must remain explicitly labelled as a regression input'
    )
    seed = ROOT / receipt['project']
    settings = read_settings(seed, experiment='hrpt')
    assert settings['mode'] == 'auto' and settings['use_model'] == 'subtract', (
        'The saved stability witness must declare automatic model-guided estimation'
    )
    observed = {
        p.relative_to(seed).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in seed.rglob('*')
        if p.is_file()
    }
    assert observed == receipt['sha256'], (
        'The saved-auto witness must retain its complete independently authored '
        'file inventory and bytes'
    )
    assert saved_digests(seed) == receipt['saved_digests'], (
        'The saved-auto input must retain both recorded nonzero provenance digests exactly'
    )
    return seed


def calculate_with_consumer(source, consumer):
    if consumer == 'edi':
        run_cli(source)
        return
    result = subprocess.run(
        [str(crysta_reference_prefix() / 'bin/crysta'), str(source), 'calc'],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 0, 'The matching native CLI must calculate its auto-project copy'


@pytest.mark.parametrize('consumer', ['crysta', 'edi'])
def test_same_nonzero_saved_auto_project_is_stable_in_either_cli(tmp_path, consumer):

    # Digestless files estimate on first calculation; this labelled state input
    # has already completed that calculation and persists both provenance digests.
    # Before: the retained earlier input held five points for n_points=9.
    # After: a newly labelled flow input obeys the exact placed-count contract;
    # the original receipt/project bytes remain untouched.
    seed = saved_auto_input()
    expected = persisted_points(seed, experiment='hrpt')
    provenance = saved_digests(seed)
    source = tmp_path / 'reloaded'
    shutil.copytree(seed, source)
    calculate_with_consumer(source, consumer)
    assert persisted_points(source, experiment='hrpt') == expected, (
        'Both products must retain points whose unchanged data and settings have saved digests'
    )

    assert saved_digests(source) == provenance, (
        'Calculating an unchanged saved-auto file must retain both provenance digests exactly'
    )


def test_both_cli_loaders_produce_the_same_points_from_one_calculated_auto_file(tmp_path):

    # Digestless files estimate on first calculation; this labelled state input
    # has already completed that calculation and persists both provenance digests.
    # Before: the retained earlier input held five points for n_points=9.
    # After: a newly labelled flow input obeys the exact placed-count contract;
    # the original receipt/project bytes remain untouched.
    seed = saved_auto_input()
    observed = []
    for consumer in ['crysta', 'edi']:
        target = tmp_path / consumer
        shutil.copytree(seed, target)
        calculate_with_consumer(target, consumer)
        observed.append(persisted_points(target, experiment='hrpt'))
    assert observed[0] == observed[1], (
        'The same saved nonzero-model auto project must mean the same points to both CLI loaders'
    )


@pytest.mark.parametrize('consumer', ['crysta', 'edi'])
def test_digestless_auto_input_estimates_once_then_retains_its_saved_baseline(tmp_path, consumer):
    seed = ROOT / 'tests/fixtures/background_estimate/projects/lifecycle-auto'
    source = tmp_path / 'digestless'
    shutil.copytree(seed, source)
    before = persisted_points(source)
    calculate_with_consumer(source, consumer)
    after = persisted_points(source)
    assert after != before, (
        'A file without provenance digests must execute its first model-guided estimate'
    )
    provenance = saved_digests(source)
    calculate_with_consumer(source, consumer)
    assert persisted_points(source) == after, (
        'The first persisted digest baseline must prevent another unchanged-input estimate'
    )
    assert saved_digests(source) == provenance, (
        'A second unchanged calculation must retain the first saved provenance exactly'
    )


@pytest.mark.parametrize('dry', [False, True], ids=['save', 'dry-publication'])
def test_warm_cli_calculation_publishes_the_live_model_guided_background(
    tmp_path, monkeypatch, dry
):

    project = prime(engine, tmp_path / 'input', SOURCE)
    cli = importlib.import_module('edi.__main__')
    # Supply a real already-calculated project to isolate the CLI calculation boundary
    # from the separately gated loss of model availability in the loader.
    monkeypatch.setattr(cli.edi, 'Project', SimpleNamespace(load=lambda _path: project))
    command = ['calc', str(tmp_path / 'input')] + (['--dry'] if dry else [])
    assert cli.main(command) == 0, (
        'The public CLI dispatcher must calculate and save the real warm model'
    )
    data = project.experiment.data
    included = np.asarray(data.calc_status) == 'incl'
    assert np.allclose(
        np.asarray(data.intensity_bkg)[included],
        expected_background(project)[included],
        rtol=1e-12,
        atol=1e-9,
    ), (
        'CLI publication must use the live model-guided points without '
        'estimating in the converted engine'
    )
    if not dry:
        assert persisted_points(tmp_path / 'input', experiment='hrpt') == [
            row[:2] for row in points(project)
        ], (
            'CLI delegated saving must persist the same guided points that '
            'the live facade publishes'
        )


@pytest.mark.parametrize(
    ('field', 'token'),
    [
        ('width', 'inf'),
        ('width', '1e309'),
        ('width', '8589934592.25'),
        ('smoothness', 'inf'),
        ('smoothness', '1e309'),
    ],
)
def test_cli_numeric_refusal_keeps_the_complete_project_unchanged(tmp_path, field, token):
    source = model_input(tmp_path / 'input', SOURCE, mode='auto')
    experiment = source / 'experiments/hrpt.edi'
    experiment.write_text(
        re.sub(
            r'(?m)^_background_estimate\.' + field + r' .*$',
            '_background_estimate.' + field + ' ' + token,
            experiment.read_text(),
        )
    )
    before = {
        p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()
    }
    completed = subprocess.run(
        cli_command(source), capture_output=True, text=True, timeout=3, check=False
    )
    assert completed.returncode > 0, (
        'CLI load/calculate must refuse invalid overrides ordinarily, '
        'without accepting or crashing: ' + field + '=' + token
    )
    assert {
        p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()
    } == before, 'Refusing an invalid persisted override must preserve every project file byte'
