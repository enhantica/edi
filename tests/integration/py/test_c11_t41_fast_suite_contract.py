"""acceptance gates for edi's terminal test-suite structure and budget."""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest


def _repo_root() -> Path:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


ROOT = _repo_root()
TESTS = ROOT / 'tests'
LICENCE_MODULE = 'tests/system/py/test_distribution_licences.py'
CONDITION_FIELDS = {
    'status',
    'window_utc',
    'start_load_1m',
    'end_load_1m',
    'quiet_threshold_load_1m',
    'runner_listener',
    'runner_worker_samples',
    'runner_worker_max',
    'runner_worker_cadence_seconds',
}


def _condition_record(output: str) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    errors: list[str] = []
    for line in output.splitlines():
        match = re.fullmatch(r'measurement-condition\.([a-z0-9_]+)=(.+)', line.strip())
        if match is None:
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f'duplicate measurement-condition field: {key}')
        fields[key] = value
    missing = sorted(CONDITION_FIELDS - set(fields))
    extra = sorted(set(fields) - CONDITION_FIELDS)
    if missing:
        errors.append(f'missing measurement-condition fields: {missing}')
    if extra:
        errors.append(f'unknown measurement-condition fields: {extra}')
    return fields, errors


def _utc_window_errors(value: str) -> list[str]:
    errors: list[str] = []
    window = value.split(' .. ')
    if len(window) != 2 or not all(item.endswith('Z') for item in window):
        return ['UTC window must contain ISO-8601 start .. end in Z']
    try:
        start = datetime.fromisoformat(window[0])
        end = datetime.fromisoformat(window[1])
        if end < start:
            errors.append('UTC window ends before it starts')
    except ValueError:
        errors.append('UTC window is not ISO-8601')
    return errors


def _observation_numbers(
    fields: dict[str, str],
) -> tuple[dict[str, float], dict[str, int], list[str]]:
    errors: list[str] = []
    numeric: dict[str, float] = {}
    integers: dict[str, int] = {}
    for key in (
        'start_load_1m',
        'end_load_1m',
        'quiet_threshold_load_1m',
        'runner_worker_cadence_seconds',
    ):
        try:
            numeric[key] = float(fields[key])
        except ValueError:
            errors.append(f'{key} must be numeric')
    for key in ('runner_worker_samples', 'runner_worker_max'):
        try:
            integers[key] = int(fields[key])
        except ValueError:
            errors.append(f'{key} must be an integer')
    return numeric, integers, errors


def _observed_condition_errors(fields: dict[str, str]) -> list[str]:
    errors = _utc_window_errors(fields['window_utc'])
    numeric, integers, number_errors = _observation_numbers(fields)
    errors.extend(number_errors)
    if errors:
        return errors
    if fields['runner_listener'] not in {'present', 'absent'}:
        errors.append('Runner.Listener must be recorded as present or absent')
    if any(numeric[key] < 0 for key in ('start_load_1m', 'end_load_1m')):
        errors.append('load observations must be non-negative')
    if numeric['quiet_threshold_load_1m'] <= 0:
        errors.append('quiet threshold must be positive')
    if numeric['runner_worker_cadence_seconds'] <= 0:
        errors.append('worker sampling cadence must be positive')
    if integers['runner_worker_samples'] < 1 or integers['runner_worker_max'] < 0:
        errors.append('worker sampling count/max are out of domain')

    # These are truthful observations of this process's window, not a characterised runner box.
    # A locally chosen load threshold cannot turn them into a complete measurement condition.
    if fields['status'] != 'CONDITION-PROVISIONAL':
        errors.append(
            'an observed but uncharacterised runner must stay CONDITION-PROVISIONAL, '
            f'got {fields["status"]}'
        )
    return errors


def _pretimed_condition_errors(fields: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if fields['status'] != 'CONDITION-PROVISIONAL':
        errors.append('a pre-timed value without a measured box must stay provisional')
    unrecorded = CONDITION_FIELDS - {'status', 'quiet_threshold_load_1m'}
    if {key for key in unrecorded if fields[key] != 'UNRECORDED'}:
        errors.append('pre-timed condition fields must say UNRECORDED, never be invented')
    try:
        if float(fields['quiet_threshold_load_1m']) <= 0:
            errors.append('quiet threshold must be positive')
    except ValueError:
        errors.append('quiet threshold must be numeric')
    return errors


def _condition_errors(output: str, *, observed: bool) -> list[str]:
    fields, errors = _condition_record(output)
    if errors:
        return errors
    if observed:
        return _observed_condition_errors(fields)
    return _pretimed_condition_errors(fields)


def _render_condition_record(**overrides: str) -> str:
    values = {
        'status': 'CONDITION-PROVISIONAL',
        'window_utc': '2026-08-24T01:00:00Z .. 2026-08-24T01:00:01Z',
        'start_load_1m': '0.50',
        'end_load_1m': '0.75',
        'quiet_threshold_load_1m': '2.0',
        'runner_listener': 'present',
        'runner_worker_samples': '4',
        'runner_worker_max': '0',
        'runner_worker_cadence_seconds': '0.25',
    }
    values.update(overrides)
    return '\n'.join(f'measurement-condition.{key}={values[key]}' for key in sorted(values))


def _worker_build_sandbox(root: Path) -> tuple[Path, Path, Path]:
    (root / 'tools/ci').mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/core-build.sh', root / 'tools/ci/core-build.sh')
    (root / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\n', encoding='utf-8'
    )
    marker = root / 'entered-shared-build.txt'
    shared = root / 'build/shared-worker-artifact'
    stand_in = root / 'tools/ci/build-crysta.sh'
    stand_in.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "${PYTEST_XDIST_WORKER:-main}" >> "$C11_T41_BUILD_ENTRY_MARKER"\n'
        'mkdir -p build/shared-worker-artifact\n'
        'exit 91\n',
        encoding='utf-8',
    )
    stand_in.chmod(0o755)
    return marker, shared, root / 'tools/ci/core-build.sh'


def _start_core_build(
    root: Path,
    script: Path,
    marker: Path,
    worker: str | None,
) -> subprocess.Popen[str]:
    bash = shutil.which('bash')
    assert bash is not None
    env = os.environ.copy()
    env['C11_T41_BUILD_ENTRY_MARKER'] = str(marker)
    if worker is None:
        env.pop('PYTEST_XDIST_WORKER', None)
    else:
        env['PYTEST_XDIST_WORKER'] = worker
    return subprocess.Popen(
        [bash, str(script)],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _tracked(*pathspecs: str) -> list[str]:
    """Repo-relative paths git actually CARRIES, which is what a layout claim is about."""
    result = subprocess.run(
        ['git', 'ls-files', '-z', '--', *pathspecs],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry for entry in result.stdout.split('\0') if entry]


def test_c11_t41_edi_uses_only_the_ruled_category_language_layout() -> None:
    """Ask git, not the filesystem: the layout claim is about the COMMITTED tree.

    `Path.exists()` answers it for one working copy only, and it was wrong in both directions.
    It tripped on the owner's machine on an untracked `__pycache__` left inside a retired
    directory - junk no clone has - and it can NEVER fail in CI, which starts from a fresh
    checkout where the retired paths are absent by construction. A gate that is impossible to
    fail where it runs and easy to trip where it does not is inverted; `git ls-files` is the
    same assertion against the bytes the repo carries.
    """
    for retired in ('acceptance', 'fitting', 'hidden', 'public'):
        stale = _tracked(f'tests/{retired}')
        assert not stale, f'retired layout remains: tests/{retired} carries {stale[:5]}'

    for required in ('unit/py', 'unit/cpp', 'integration/py', 'system/py', 'fixtures'):
        assert _tracked(f'tests/{required}'), f'required tier is empty or absent: tests/{required}'

    assert not _tracked('examples/refine-*'), (
        'edi is a corpus consumer only; fitting-shaped examples must move to crysta or retire'
    )

    misplaced = [
        path
        for path in _tracked('tests/**/test*.py')
        if not path.startswith((
            'tests/unit/py/',
            'tests/integration/py/',
            'tests/integration/app/',
            'tests/system/py/',
        ))
    ]
    assert not misplaced, f'test modules outside repo/category/language layout: {misplaced}'


def test_c11_t41_edi_hidden_unit_location_is_repo_declared_and_total() -> None:
    declaration = TESTS / 'hidden-surface.txt'
    assert declaration.is_file()
    globs = [
        line.strip()
        for line in declaration.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    assert globs == ['tests/unit/**']

    hidden = sorted(path for path in (TESTS / 'unit').rglob('*') if path.is_file())
    assert hidden, 'tests/unit must govern a non-empty hidden surface'
    assert not list(TESTS.rglob('*_hidden.py')), 'the retired hidden filename suffix returned'


def test_c11_t41_two_pytest_workers_cannot_enter_the_shared_core_build(
    tmp_path: Path,
) -> None:
    control_marker, control_shared, control_script = _worker_build_sandbox(tmp_path / 'control')
    control = _start_core_build(
        tmp_path / 'control',
        control_script,
        control_marker,
        worker=None,
    )
    control_stdout, control_stderr = control.communicate(timeout=10)
    assert control.returncode == 91, control_stdout + control_stderr
    assert control_marker.read_text(encoding='utf-8').splitlines() == ['main']
    assert control_shared.exists(), 'the input mutation did not reach the shared build path'

    worker_root = tmp_path / 'workers'
    worker_marker, worker_shared, worker_script = _worker_build_sandbox(worker_root)
    workers = {
        worker: _start_core_build(worker_root, worker_script, worker_marker, worker)
        for worker in ('gw0', 'gw1')
    }
    results = {
        worker: (process.communicate(timeout=10), process.returncode)
        for worker, process in workers.items()
    }
    assert not worker_marker.exists(), 'a pytest worker entered the shared build producer'
    assert not worker_shared.exists(), 'pytest workers wrote the same build/artifact path'
    for worker, ((stdout, stderr), returncode) in results.items():
        output = stdout + stderr
        assert returncode != 0
        assert worker in output
        assert 'worker' in output.lower()
        assert 'build' in output.lower() or 'artifact' in output.lower()


def _partition_transport(groups, omitted):
    with tempfile.TemporaryDirectory(prefix='system-part-contract-') as scratch:
        replay = Path(scratch)
        (replay / 'tests').mkdir()
        (replay / 'tests/test-groups.json').write_text(json.dumps({'groups': groups}))
        bindir = replay / 'bin'
        bindir.mkdir()
        shim = bindir / 'python'
        shim.write_text(
            '#!' + sys.executable + '\nimport json, subprocess, sys\n'
            'if sys.argv[1] == "-c":\n'
            '    sys.exit(subprocess.call([sys.executable, *sys.argv[1:]]))\n'
            'print(json.dumps(sys.argv[1:]))\n'
        )
        shim.chmod(0o755)
        env = {
            **os.environ,
            'PATH': str(bindir) + os.pathsep + os.defpath,
            'EDI_RUN_NIGHTLY_ONLY': 'false' if omitted else 'true',
            'EDI_TEST_DURATIONS': str(replay / 'no-prior-durations.json'),
        }
        result = subprocess.run(
            ['/bin/bash', str(ROOT / 'tools/ci/system-tests-part.sh'), '1', '3'],
            cwd=replay,
            env=env,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    assert result.returncode == 0, (
        'the actual system partition runner reaches its pytest transport'
    )
    return result


def _assert_nightly_inclusion(switch, active):
    # Include literals from the switch so a newly named event cannot escape the check.
    events = {'pull_request', 'push', 'schedule', 'workflow_dispatch', 'other-event'}
    events.update(re.findall(r"['\"]([^'\"]+)['\"]", str(switch)))
    for platform in ('Linux', 'macOS'):
        expression = str(switch).replace('matrix.platform', repr(platform))
        for event in sorted(events):
            for core_only in (False, True):
                included = active({'if': expression}, event, core_only=core_only)
                expected = event == 'schedule' or (event == 'workflow_dispatch' and not core_only)
                assert included is expected, (
                    'Nightly app builders run only on schedules and full manual runs; '
                    'PR, push, core-only manual and every other event exclude them'
                )


def _assert_licence_delivery(jobs, active):
    job = jobs.get('app-wasm')
    assert job and not job.get('continue-on-error'), (
        'Delegated licence checks require the mandatory staged-artifact job'
    )
    commands = [step.get('run', '').split() for step in job['steps']]
    required = [
        'pixi run core-build',
        'pixi run -e app --skip-deps wasm-build',
        'pixi run -e app app-build',
        'pixi run --skip-deps python tests/fixtures/distribution_licences/stage.py',
        'pixi run --skip-deps python -m pytest ' + LICENCE_MODULE,
    ]
    positions = []
    for command in required:
        tokens = command.split()
        assert commands.count(tokens) == 1, (
            'Delegated licence checks retain every actual build, staging and consumer command'
        )
        positions.append(commands.index(tokens))
    assert positions == sorted(positions), (
        'Delegated licence checks build and stage the real artifacts before consuming them'
    )
    for event in ('push', 'schedule', 'workflow_dispatch'):
        for core_state in ('success', 'failure'):
            context = {'states': {'changes': 'success', 'core': core_state}}
            assert active(job, event, **context), (
                'Delegated licence checks remain reachable on main, nightly and full manual runs'
            )
            for index in positions:
                step = job['steps'][index]
                assert not step.get('continue-on-error'), (
                    'Delegated licence checks cannot forgive a failed producer or consumer'
                )
                # Staging and checks report missing inputs even after a build fails.
                if index in positions[-2:]:
                    assert active(step, event, **context), (
                        'Delegated licence staging and checks execute after preceding failures'
                    )


def _assert_licence_delivery_controls(jobs, active):
    for mutation in (
        'missing-job',
        'missing-stage',
        'missing-check',
        'order',
        'job-off',
        'stage-off',
        'check-off',
        'job-optional',
        'stage-optional',
        'check-optional',
    ):
        changed = copy.deepcopy(jobs)
        job = changed['app-wasm']
        stage, check = [
            next(step for step in job['steps'] if fragment in step.get('run', ''))
            for fragment in ('distribution_licences/stage.py', 'pytest ' + LICENCE_MODULE)
        ]
        if mutation == 'missing-job':
            del changed['app-wasm']
        elif mutation in {'missing-stage', 'missing-check'}:
            job['steps'].remove(stage if mutation == 'missing-stage' else check)
        elif mutation == 'order':
            job['steps'].remove(stage)
            job['steps'].append(stage)
        else:
            target = {'job': job, 'stage': stage, 'check': check}[mutation.split('-')[0]]
            target[
                'if' if mutation.endswith('-off') else 'continue-on-error'
            ] = not mutation.endswith('-off')
        with pytest.raises(AssertionError, match='Delegated licence'):
            _assert_licence_delivery(changed, active)


def _assert_platform_nightly_partition(groups, tasks, jobs, active):
    nightly_paths = [
        'tests/system/py/test_scan_app_execution.py',
        'tests/system/py/test_scan_accident_paths.py',
        'tests/system/py/test_plain_data_app.py',
    ]
    assert set(nightly_paths) <= set(groups['nightly-only']['paths']), (
        'The exclusive nightly cohort retains all original app-builder witnesses'
    )
    nightly_paths = groups['nightly-only']['paths']
    parts = [
        step
        for step in jobs['system']['steps']
        if 'pixi run system-tests-part' in step.get('run', '')
    ]
    assert len(parts) == 1, 'every system part invokes one required production partition runner'
    switch = parts[0]['env']['EDI_RUN_NIGHTLY_ONLY']
    _assert_nightly_inclusion(switch, active)
    for omitted in (False, True):
        result = _partition_transport(groups, omitted)
        ignores = ['--ignore=' + path for path in nightly_paths] if omitted else []
        ignores.append('--ignore=' + LICENCE_MODULE)
        assert json.loads(result.stdout) == [
            '-m',
            'pytest',
            'tests/system',
            '-q',
            *ignores,
            '--splits',
            '3',
            '--group',
            '1',
            '--splitting-algorithm',
            'least_duration',
            '--durations-path',
            'build/test-durations-1.json',
            '--store-durations',
        ], (
            'Production partitions retain the complete tier '
            'with exactly the nightly omissions and the staged-artifact licence delegation'
        )

    assert tasks['nightly-only-tests']['cmd'] == [
        'python',
        '-m',
        'pytest',
        *nightly_paths,
        '-q',
    ], 'The local exclusive-nightly entry point must execute every declared nightly file'


def test_c11_t41_edi_ci_tiers_name_pr_merge_and_local_surfaces() -> None:
    workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert re.search(r'(?m)^\s*pull_request:\s*$', workflow)
    assert re.search(r'(?ms)^\s*push:\s*\n\s*branches:\s*\[main\]', workflow)
    import yaml  # noqa: PLC0415 - defer cross-module test wiring

    from tests.integration.py.ci_runner_contract import (  # noqa: PLC0415 - avoid test-module import cycles
        platform_job,
        self_hosted_runners,
    )

    jobs = yaml.safe_load(workflow)['jobs']
    declared = yaml.safe_load(workflow)
    triggers = declared.get('on', declared.get(True))
    assert {'pull_request', 'push', 'schedule', 'workflow_dispatch'} <= set(triggers), (
        'complete system selections retain PR, main, nightly and on-demand workflow triggers'
    )
    for name in ('native', 'core', 'cli-python', 'app'):
        runners = [
            runner
            for platform in ('linux-64', 'osx-arm64')
            for runner in self_hosted_runners(platform_job(jobs, name, platform))
            if runner[1] == ('Linux' if platform == 'linux-64' else 'macOS')
        ]
        assert {tuple(r[1:]) for r in runners} == {('Linux', 'X64'), ('macOS', 'ARM64')}, (
            'CI tiers must actually bind both prescribed operating systems and architectures'
        )
    import json  # noqa: PLC0415 - scoped contract input
    import tomllib  # noqa: PLC0415 - scoped contract input

    groups = json.loads((ROOT / 'tests/test-groups.json').read_text())['groups']
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
    for group in ('quick', 'full'):
        task = groups[group]['task']
        assert task in tasks, 'both cadences retain a declared executable local test-group task'
        assert {'unit/py', 'unit/cpp', 'integration/py', 'system'} <= set(
            groups[group]['tiers']
        ), 'Both CI cadences must retain the complete unit, integration and system selections'
        if 'system' not in jobs:
            assert 'pixi run ' + task in workflow, (
                'Both PR and merge CI must invoke their declared executable test-group tasks'
            )
    if 'system' in jobs:
        # Before: one event-selected aggregator. After the parallel-jobs
        # decision: the exact same tier selection across required core and parts.
        from tests.fixtures.e09_t75_workflow import active  # noqa: PLC0415
        from tests.integration.py.test_e04_t11_ci_order import (  # noqa: PLC0415
            assert_core_failure_reporting,
        )
        from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415
            public_build_boundary,
        )

        for group, python_task in (('quick', 'quick-tests'), ('full', 'test')):
            assert tasks[groups[group]['task']]['depends-on'] == [python_task, 'cpp-test'], (
                'both local declared groups retain their executable Python and C++ selections'
            )
        assert tasks['quick-tests']['cmd'] == [
            'python',
            '-m',
            'pytest',
            'tests/unit',
            'tests/integration',
            'tests/system',
            '--ignore=tests/integration/app',
            '-q',
        ], 'the unsplit local group and split CI jobs must retain identical tier selections'
        assert tasks['test']['cmd'] == [
            'bash',
            'tools/ci/pytest-lenient.sh',
            '--ignore=tests/integration/app',
        ], 'the local merge group retains its complete default collection outside the app tier'
        assert tasks['core-tests']['cmd'] == [
            'python',
            '-m',
            'pytest',
            'tests/unit',
            'tests/integration',
            '--ignore=tests/integration/app',
            '-q',
        ], 'the split core task must retain all declared unit and integration selections'
        assert tasks['system-tests-part']['cmd'] == ['bash', 'tools/ci/system-tests-part.sh'], (
            'each system part invokes the actual declared partition executable'
        )
        partition = (ROOT / 'tools/ci/system-tests-part.sh').read_text()
        assert re.search(r'exec python -m pytest tests/system -q "\$@"\s*\\', partition), (
            'the actual partition runner must execute the complete system tier'
        )
        for option in (
            '--splits "$parts"',
            '--group "$part"',
            '--splitting-algorithm least_duration',
        ):
            assert option in partition, (
                'system partitioning retains the complete duration-based split'
            )
        _assert_platform_nightly_partition(groups, tasks, jobs, active)
        _assert_licence_delivery(jobs, active)
        _assert_licence_delivery_controls(jobs, active)
        for name in ('core', 'system'):
            assert_core_failure_reporting(jobs[name])
            for platform in ('linux-64', 'osx-arm64'):
                public_build_boundary(jobs, name, platform)
            for event in ('pull_request', 'push', 'schedule', 'workflow_dispatch'):
                assert active(jobs[name], event, states={'changes': 'success'}) == (
                    name == 'core' or event != 'pull_request'
                ), 'PRs execute core; full events also execute every system part'
        durations = jobs['system-durations']
        assert (
            durations.get('if') == "github.event_name == 'push'" and durations['needs'] == 'system'
        ), 'duration refresh follows all system parts on main pushes only'
    assert 'edi verification' in workflow.lower() or 'crysta-consumer' in workflow
    local = ROOT / 'tools/ci/local-ci.sh'
    assert local.is_file()
    local_text = local.read_text(encoding='utf-8')
    assert 'tests/system' in local_text and 'tests/integration' in local_text
