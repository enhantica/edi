"""The project file drives automatic estimation through CLI and Python."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.background_estimate.settings import (
    DEFAULTS,
    configured_project,
    points,
    read_settings,
    require_reference,
    saved_points,
    write_settings,
)

ROOT = Path(__file__).resolve().parents[3]


def cli_command(project, operation):
    return [sys.executable, '-m', 'edi', operation, str(project)]


def run_cli(project, operation):
    result = subprocess.run(
        cli_command(project, operation),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        'The existing CLI command must consume automatic settings without new flags: '
        + result.stderr
    )


def test_auto_cli_and_python_calculate_the_same_reference_points(tmp_path):
    source = configured_project(tmp_path / 'source')
    project = engine.Project.load(source)
    project.analysis.calculate()
    expected = [row[:2] for row in points(project)]
    cli = tmp_path / 'cli'
    shutil.copytree(source, cli)
    run_cli(cli, 'calc')
    require_reference(expected, 'snip')
    assert saved_points(cli) == expected, (
        'CLI calculation and Python must persist identical automatic points from the same project'
    )
    assert read_settings(cli) == DEFAULTS, (
        'CLI calculation must preserve saved settings and derived blanks'
    )


def test_auto_estimation_precedes_cli_and_python_fit(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project', source)
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(
        re.sub(
            r'(?m)^_minimizer.max_iterations .*$',
            '_minimizer.max_iterations 1',
            analysis.read_text(),
        )
    )
    write_settings(source, DEFAULTS, experiment='hrpt')
    cli = tmp_path / 'cli'
    shutil.copytree(source, cli)
    run_cli(cli, 'fit')
    control = engine.Project.load(source)
    control.experiment.background.auto_estimate(
        method='snip', use_model=False, tolerance=2.0, in_peaks='drop'
    )
    expected = [row[:2] for row in points(control)]
    project = engine.Project.load(source)
    project.analysis.fit()
    assert [row[:2] for row in points(project)] == expected, (
        'A fit must resolve automatic background points before changing fit parameters'
    )
    assert saved_points(cli, experiment='hrpt') == expected, (
        'CLI and Python fits must start with the same data-only automatic points'
    )


def test_published_cli_project_records_manual_estimate_settings():
    settings = read_settings(
        ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project', experiment='hrpt'
    )
    assert settings['mode'] == 'manual', (
        'The published LBCO project must record manual mode and keep its saved free points'
    )
    assert settings['method'] in {'auto', 'arpls', 'snip', 'fabc'}, (
        'The published CLI example must declare a supported estimator method'
    )


@pytest.mark.parametrize('method', ['arpls', 'snip', 'fabc'])
def test_new_default_policy_and_exact_count_agree_in_cli_and_python(tmp_path, method):
    settings = {
        **DEFAULTS,
        'method': method,
        'tolerance': None,
        'in_peaks': 'move',
        'n_points': 17,
        'use_model': 'ignore',
    }
    source = configured_project(tmp_path / 'source', settings)
    project = engine.Project.load(source)
    project.analysis.calculate()
    expected = [row[:2] for row in points(project)]
    assert len(expected) == 17, 'Automatic saved n_points must place exactly seventeen anchors'
    cli = tmp_path / 'cli'
    shutil.copytree(source, cli)
    run_cli(cli, 'calc')
    assert saved_points(cli) == expected, (
        'Existing CLI and Python calculations must apply the same blank-tolerance move policy'
    )
    assert read_settings(cli) == settings, (
        'CLI saving must preserve the blank tolerance, exact count and data-only move settings'
    )


@pytest.mark.parametrize(
    ('authored', 'expected'),
    [
        ('auto', 'auto'),
        ('subtract', 'subtract'),
        ('ignore', 'ignore'),
        ('true', 'subtract'),
        ('false', 'ignore'),
    ],
)
def test_cli_accepts_all_policies_and_explicit_save_canonicalizes_legacy_booleans(
    tmp_path, authored, expected
):
    # Canonical committed inputs do not remove the explicit old-Boolean migration contract.
    # Only this disposable copy receives true/false; saving must canonicalize it.
    source = configured_project(tmp_path / 'source', {**DEFAULTS, 'mode': 'manual'})
    path = source / 'experiments/bank.edi'
    import re  # noqa: PLC0415

    path.write_text(
        re.sub(
            r'(?m)^_background_estimate\.use_model .*$',
            f'_background_estimate.use_model {authored}',
            path.read_text(),
        )
    )
    before = saved_points(source)
    run_cli(source, 'calc')
    loaded = engine.Project.load(source)
    assert loaded.experiment.background_estimate.use_model == expected, (
        'After CLI calculation, each authored policy must load with the declared canonical meaning'
    )
    # A Manual calc need not rewrite unchanged inputs. Explicit saving owns canonical bytes.
    destination = tmp_path / 'canonical'
    loaded.save_as(destination)
    saved = (destination / 'experiments/bank.edi').read_text()
    assert re.findall(r'(?m)^_background_estimate\.use_model\s+(\S+)', saved) == [expected], (
        'Explicit project saving must write canonical auto/subtract/ignore '
        'and map true/false without a new flag'
    )
    assert saved_points(source) == saved_points(destination) == before, (
        'Saving a manual project through the CLI must retain every existing background point'
    )
