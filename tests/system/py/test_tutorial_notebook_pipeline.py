"""Gate 3: execute in fresh kernels, fail on errors, then convert without execution."""

import json
import re
import sys
import tomllib

import pytest
import yaml

from tests.fixtures.tutorial_cases.contract import ROOT, cases_for
from tests.fixtures.tutorial_cases.pipeline import (
    convert,
    executed_inputs,
    run_notebooks,
    runner_sources,
    stage,
)
from tests.fixtures.tutorial_cases.presentation import text

CASES = cases_for('python')


@pytest.fixture(scope='module')
def all_run(tmp_path_factory):
    root = stage(tmp_path_factory.mktemp('notebook-task') / 'source')
    runner_sources(root)
    result = run_notebooks(root)
    return root, result


def test_run_task_executes_every_case_and_writes_real_outputs(all_run):
    root, result = all_run
    assert result.returncode == 0, (
        'Gate 3: the run task must execute every authored control and write its outputs: '
        + result.stdout
        + result.stderr
    )
    for case in CASES:
        path = root / 'docs/user/tutorials' / (case + '.ipynb')
        assert path.is_file(), (
            'Gate 3: default notebook execution must include every case: ' + case
        )
        cells = json.loads(path.read_text())['cells']
        proof = [
            text({'source': output.get('text', '')})
            for cell in cells
            for output in cell.get('outputs', [])
        ]
        assert any('RUNNER_PROOF ' in output for output in proof), (
            'Gate 3: outputs must come from executing the cell, not from an execution flag'
        )


def test_each_notebook_uses_a_fresh_kernel_and_working_folder(all_run):
    root, result = all_run
    assert result.returncode == 0, 'Gate 3: the namespace-isolation control must run successfully'
    proofs = []
    for case in CASES:
        notebook = json.loads((root / 'docs/user/tutorials' / (case + '.ipynb')).read_text())
        source = ''.join(
            text({'source': output.get('text', '')})
            for cell in notebook['cells']
            for output in cell.get('outputs', [])
        )
        match = re.search(r'RUNNER_PROOF (\{[^\n]+\})', source)
        assert match is not None, (
            'Gate 3: each real kernel emits its own process and folder witness'
        )
        proofs.append(json.loads(match[1]))
    assert len({proof['pid'] for proof in proofs}) == len(CASES), (
        'Gate 3: notebooks never reuse another notebook kernel or its global namespace'
    )
    assert len({proof['cwd'] for proof in proofs}) == len(CASES), (
        'Gate 3: each notebook executes in an independent fresh folder'
    )
    assert {proof['prefix'] for proof in proofs} == {sys.prefix}, (
        'Gate 3: fresh kernels use the requested task environment rather than an unrelated Python'
    )


def test_a_failing_cell_fails_the_run_task_and_names_the_case(tmp_path):
    root = stage(tmp_path / 'source')
    case = CASES[-1]
    runner_sources(root, failed=case)
    result = run_notebooks(root, [case])
    assert result.returncode != 0 and case in result.stdout + result.stderr, (
        'Gate 3: a failed notebook cell fails notebooks-run and identifies its case'
    )
    assert 'DELIBERATE_NOTEBOOK_CELL_FAILURE' in result.stdout + result.stderr, (
        'Gate 3: failure must reach the actual failing cell rather than a setup error'
    )


@pytest.mark.parametrize('invalid', ['unrun', 'error'])
def test_strict_converter_refuses_unrun_or_failed_notebooks(tmp_path, invalid):
    root = stage(tmp_path / 'source')
    case = 'pd-neut-cwl_lbco-hrpt'
    executed_inputs(root, **{invalid: case})
    result = convert(root, require_outputs=True)
    assert result.returncode != 0 and case in result.stdout + result.stderr, (
        'Gate 3: strict publication conversion refuses unrun or failed notebooks and names them'
    )
    assert 'notebooks-run' in result.stdout + result.stderr, (
        'Gate 3: conversion refusal tells the user to run the separate notebook task'
    )


def test_conversion_preserves_outputs_drops_hidden_cells_and_never_executes(tmp_path):
    root = stage(tmp_path / 'source')
    executed_inputs(root)
    result = convert(root)
    assert result.returncode == 0, (
        'Gate 3: convert-only succeeds despite code that would fail if executed: '
        + result.stdout
        + result.stderr
    )
    pages = list((root / 'website/surfaces/docs/python/tutorials/cases').glob('*.md'))
    assert pages, 'Gate 3: the converter must produce native Markdown pages'
    for path in pages:
        source = path.read_text()
        assert 'CONVERTED_OUTPUT_SENTINEL' in source and '<table>' in source, (
            'Gate 3: native pages preserve actual HTML/table outputs from the run notebook'
        )
        assert 'HIDDEN_INPUT_SENTINEL' not in source and 'HIDDEN_OUTPUT_SENTINEL' not in source, (
            'Gate 3: conversion omits the input and output of every hidden cell'
        )


def task_closure(tasks, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        return seen
    seen.add(name)
    task = tasks.get(name, {})
    dependencies = task.get('depends-on', []) if isinstance(task, dict) else []
    for dependency in dependencies:
        task_closure(tasks, dependency, seen)
    return seen


def test_run_and_convert_tasks_are_separate_and_ci_runs_tutorials_before_publishing():
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
    assert {'notebooks-run', 'site-build', 'site-serve'} <= tasks.keys(), (
        'Gate 3: local and CI workflows expose separate run, convert and preview tasks'
    )
    assert 'notebooks-run' not in task_closure(tasks, 'site-build'), (
        'Gate 3: site-build never starts the notebook run task, directly or by dependency'
    )
    workflow = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())
    jobs = [
        job
        for job in workflow['jobs'].values()
        if any('pixi run site-build' in step.get('run', '') for step in job.get('steps', []))
    ]
    assert jobs, 'Gate 3: the published docs CI job must run the actual site build'
    for job in jobs:
        steps = job['steps']
        build = next(
            index
            for index, step in enumerate(steps)
            if 'pixi run site-build' in step.get('run', '')
        )
        runs = [step for step in steps[:build] if 'pixi run notebooks-run' in step.get('run', '')]
        assert runs and all(not step.get('continue-on-error', False) for step in runs), (
            'Gate 3: CI executes all tutorial notebooks first and a failing cell fails CI'
        )
        assert all('if' not in step or step['if'] == steps[build].get('if') for step in runs), (
            'Gate 3: a docs build cannot bypass notebook execution through a different condition'
        )
