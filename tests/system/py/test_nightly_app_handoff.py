# SPDX-License-Identifier: BSD-3-Clause
"""Nightly system coverage still receives an app when its optional observer fails."""

import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e04_t1 import project_actor
from tests.integration.app.test_single_crystal_views import app_result
from tests.system.py.ci_execution_contract import render, value

ROOT = Path(__file__).resolve().parents[3]
APP_BINARIES = {
    'build/app/app/edi_app',
    'build/app/app/edi_app_tests',
    'build/app/app/edi_assistant_guard',
}


def eligible(step, context):
    condition = step.get('if') or 'success()'
    qualified = re.search(r'\b(?:always|cancelled|failure|success)\(\)', condition)
    return (qualified or context['success()']) and value(condition, context)


@pytest.mark.parametrize(('job', 'platform'), [('app', 'Linux'), ('app-macos', 'macOS')])
def test_failed_observer_does_not_starve_the_nightly_system_shards(job, platform):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    app_steps = workflow['jobs'][job]['steps']
    observer = next(step for step in app_steps if 'tutorial-transactions' in step.get('run', ''))
    save = next(
        step
        for step in app_steps
        if step.get('uses', '').startswith(('actions/cache/save@', './.github/actions/store'))
        and set(step.get('with', {}).get('path', '').split()) >= APP_BINARIES
    )
    context = {
        'runner.os': platform,
        'env.APP_PLATFORM': platform,
        'github.run_id': 848,
        'github.event_name': 'schedule',
        'steps.inputs.outputs.run': 'true',
        'steps.apphost.outcome': 'success',
        'success()': False,
        'cancelled()': False,
        'failure()': True,
    }
    assert app_steps.index(observer) < app_steps.index(save) or eligible(
        save, {**context, 'success()': True, 'failure()': False}
    ), 'The app cache is saved before or independently of the observer'
    assert eligible(save, context) or app_steps.index(save) < app_steps.index(observer), (
        'The built app and runner are still saved if the tutorial observer fails'
    )
    assert not eligible(save, {**context, 'cancelled()': True}), (
        'A cancelled app job must not publish its nightly system-test inputs'
    )
    system = workflow['jobs']['system']
    restore = next(
        step
        for step in system['steps']
        if step.get('uses', '').startswith('actions/cache/restore@')
        and set(step.get('with', {}).get('path', '').split()) >= APP_BINARIES
    )
    assert render(save['with']['key'], context) == render(
        restore['with']['key'], {**context, 'matrix.platform': platform}
    ), 'The system shards restore the app from the same platform and run'
    assert restore['with'].get('fail-on-cache-miss') is True, (
        'A missing app is reported by the system job instead of skipping the native gates'
    )
    assert value(
        system.get('if'),
        {
            **context,
            'needs.changes.result': 'success',
            'needs.app.result': 'failure',
            'needs.app-macos.result': 'failure',
            'github.event.pull_request.head.repo.fork': False,
        },
    ), 'A failed app job is reported without preventing the nightly system shards from starting'


@pytest.mark.parametrize('actor', ['project-inventory', 'single-crystal-views'])
def test_qt_diagnostic_capture_preserves_the_child_status_and_valid_receipt(
    monkeypatch, tmp_path, actor
):
    marker = b'PASS   : completed-case'
    run = subprocess.run

    def launch_fixture(_command, **kwargs):
        return run(
            [
                sys.executable,
                '-c',
                'import os; os.write(1, ' + repr(marker + b'\ncut: \xe2\n') + ');'
                'os.write(2, ' + repr(b'error: \xb2\n') + '); raise SystemExit(17)',
            ],
            **kwargs,
        )

    monkeypatch.setattr(subprocess, 'run', launch_fixture)
    if actor == 'project-inventory':
        monkeypatch.setattr(project_actor, 'project_cases_for_session', lambda _: ('fixture',))
        result = project_actor.run_projects(object(), sys.executable, str(tmp_path))
    else:
        monkeypatch.setenv('EDI_APP_TEST_RUNNER', sys.executable)
        result = inspect.unwrap(app_result)()
    assert result.returncode == 17 and marker.decode() in result.stdout, (
        'The native actor preserves child failure and complete Qt receipt lines when output is cut'
    )
    assert r'\xe2' in result.stdout and r'\xb2' in result.stderr, (
        'Invalid diagnostic bytes remain identifiable without interrupting Qt receipt decoding'
    )


@pytest.mark.parametrize('job', ['app', 'app-macos'])
def test_optional_tutorial_observer_has_a_separate_handoff_from_the_required_app(job):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    app_steps = workflow['jobs'][job]['steps']
    observer_paths = {'build/tutorial-transactions'}
    saved = [
        step['with']
        for step in app_steps
        if step.get('uses', '').startswith(('actions/cache/save@', './.github/actions/store'))
        and 'with' in step
        and 'path' in step['with']
    ]
    base = [inputs for inputs in saved if set(inputs['path'].split()) >= APP_BINARIES]
    assert len(base) == 1 and not observer_paths.intersection(base[0]['path'].split()), (
        'The required app cache can be published without the optional observer directory'
    )
    optional = [inputs for inputs in saved if set(inputs['path'].split()) >= observer_paths]
    assert len(optional) == 1 and optional[0]['key'] != base[0]['key'], (
        'The observer has its own system-test cache and cannot replace the app handoff'
    )
    restored = [
        step['with']
        for step in workflow['jobs']['system']['steps']
        if step.get('uses', '').startswith('actions/cache/restore@')
        and set(step['with']['path'].split()) >= observer_paths
    ]
    assert len(restored) == 1 and not restored[0].get('fail-on-cache-miss', False), (
        'A missing observer cache must leave the ordinary system shards available'
    )
