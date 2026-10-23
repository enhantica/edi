"""Observe rendered suite steps without starting their builds or numerical suites."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tomllib

import yaml

from tests.system.py.ci_execution_contract import (
    contexts,
    prerequisites_ready,
    render,
    run_settings,
    task_commands,
    value,
)
from tests.system.py.ci_script_execution import retains_work

SUITE_STEPS = {
    'crysta': {'Hidden numerical suite (cpp surface)', 'Hidden numerical suite (Python tiers)'},
    'edi': {
        'Tests (declared group, C++ unit, unit and integration)',
        'Tests (declared group, system part)',
        'C++ unit tests',
        "The app group's Python tests (tests/integration/app)",
    },
}


def suite_steps(workflow, event, platform, repo):
    for name, job, ctx, actual in contexts(workflow, event, names=False):
        if (
            actual != platform
            or not value(job.get('if'), ctx)
            or not prerequisites_ready(workflow, job, ctx)
        ):
            continue
        for step in job.get('steps', []):
            if step.get('name') in SUITE_STEPS[repo] and value(step.get('if'), ctx):
                matrix = json.dumps(
                    {k: v for k, v in ctx.items() if k.startswith('matrix.')}, sort_keys=True
                )
                yield (name, matrix, step['name']), job, step, ctx


def invoke_step(tmp_path, workflow, job, step, ctx, *, failure=''):
    directory = tmp_path / str(len(list(tmp_path.iterdir())))
    directory.mkdir()
    calls = directory / 'calls.jsonl'
    program = directory / 'pixi'
    program.write_text(
        '#!' + sys.executable + '\n'
        'import json, os, sys\n'
        'with open(os.environ["CADENCE_CALLS"], "a") as f:\n'
        ' f.write(json.dumps({"argv":sys.argv[1:], "nightly":{k:v for k,v in os.environ.items() '
        'if k.endswith("_SKIP_NIGHTLY_GROUP") or k == "EDI_RUN_NIGHTLY_ONLY"}})+"\\n")\n'
        'sys.exit(23 if os.environ["CADENCE_FAILURE"] in sys.argv[1:] else 0)\n'
    )
    program.chmod(0o755)
    _shell, env = run_settings(workflow, job, step, ctx)
    result = subprocess.run(
        [
            '/bin/bash',
            '--noprofile',
            '--norc',
            '-e',
            '-o',
            'pipefail',
            '-c',
            render(step['run'], ctx),
        ],
        cwd=directory,
        env={
            **os.environ,
            **env,
            'PATH': str(directory) + ':/usr/bin:/bin',
            'CADENCE_CALLS': str(calls),
            'CADENCE_FAILURE': failure,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    observed = (
        [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    )
    return result.returncode, observed


def task_name(argv):
    args = iter(argv)
    if next(args, '') != 'run':
        return ''
    for token in args:
        if not token.startswith('-'):
            return token
        if token in {'-e', '--environment'}:
            next(args)
    return ''


def cadence_errors(tmp_path, baseline, actual, event, platform, repo):
    required = list(suite_steps(baseline, event, platform, repo))
    observed = {
        key: (job, step, ctx) for key, job, step, ctx in suite_steps(actual, event, platform, repo)
    }
    errors = []
    if not required:
        return ['empty accepted suite cohort']
    for key, old_job, old_step, old_ctx in required:
        if key not in observed:
            errors.append('missing suite ' + str(key))
            continue
        job, step, ctx = observed[key]
        if job.get('continue-on-error') or step.get('continue-on-error'):
            errors.append('advisory suite ' + str(key))
        before_rc, before = invoke_step(tmp_path, baseline, old_job, old_step, old_ctx)
        after_rc, after = invoke_step(tmp_path, actual, job, step, ctx)
        if before_rc or not before:
            errors.append('unobservable accepted suite ' + str(key))
            continue
        if after_rc or any(call not in after for call in before):
            errors.append('lost selected invocation ' + str(key))
        for task in {task_name(call['argv']) for call in before}:
            failed_rc, _ = invoke_step(tmp_path, actual, job, step, ctx, failure=task)
            if not task or not failed_rc:
                errors.append('masked suite failure ' + str(key))
    return errors


def linux_jobs(workflow, event):
    return {
        (
            name,
            json.dumps({k: v for k, v in ctx.items() if k.startswith('matrix.')}, sort_keys=True),
        ): (job, ctx, platform)
        for name, job, ctx, platform in contexts(workflow, event, names=False)
        if not job.get('name', name).startswith((
            'performance',
            'wheels',
            'publish',
            'cli-native',
        ))
        and value(job.get('if'), ctx)
        and prerequisites_ready(workflow, job, ctx)
    }


def linux_condition(condition, ctx):
    # The accepted Darwin-only bootstrap consults committed fixture files. Assign
    # their presence here; neither value can enable that step on the Linux axis.
    condition = (
        re.sub(r'hashFiles\([^)]*\)', "'fixture-present'", str(condition))
        if isinstance(condition, str)
        else condition
    )
    return value(condition, ctx)


def non_suite_gates(job, ctx, repo):
    for step in job.get('steps', []):
        title = step.get('name', '')
        if not title:
            continue
        if (
            title not in SUITE_STEPS[repo]
            and not title.startswith((
                'Report',
                'Compiler cache',
                'ccache',
                'Python harness',
                'Coverage job summary',
                'Prepare',
            ))
            and 'pixi run' in step.get('run', '')
            and not step.get('continue-on-error')
            and linux_condition(step.get('if'), ctx)
        ):
            yield step


def command_text(script):
    return '\n'.join(
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    )


def linux_gate_errors(baseline, actual, event, repo):
    expected = linux_jobs(baseline, event)
    observed = linux_jobs(actual, event)
    errors = []
    for key, (old_job, old_ctx, platform) in expected.items():
        if platform != 'linux-64':
            continue
        if key not in observed:
            errors.append('missing Linux job ' + str(key))
            continue
        job, ctx, current_platform = observed[key]
        if current_platform != 'linux-64' or job.get('continue-on-error'):
            errors.append('nonrequired Linux job ' + str(key))
        for step in non_suite_gates(old_job, old_ctx, repo):
            matches = [s for s in job.get('steps', []) if s.get('name') == step['name']]
            if len(matches) != 1:
                errors.append('missing or duplicated non-suite gate ' + step['name'])
                continue
            live = matches[0]
            if (
                live.get('if') != step.get('if')
                or not linux_condition(live.get('if'), ctx)
                or live.get('continue-on-error')
            ):
                errors.append('changed, skipped or advisory non-suite gate ' + step['name'])
            if command_text(render(live.get('run', ''), ctx)) != command_text(
                render(step['run'], old_ctx)
            ):
                errors.append('changed non-suite gate command ' + step['name'])
            if run_settings(actual, job, live, ctx) != run_settings(
                baseline, old_job, step, old_ctx
            ):
                errors.append('changed non-suite execution settings ' + step['name'])
    return errors


def linux_closure_errors(snapshot, actual_manifest, read_source, event):
    baseline = yaml.safe_load(snapshot['files']['.github/workflows/ci.yml'])
    manifest = snapshot['files']['pixi.toml']
    environments = {'default', *tomllib.loads(manifest).get('environments', {})}
    errors = []
    selected = selected_linux_tasks(baseline, event)
    # Preserve each accepted task's actual dependency commands, including feature
    # environments. Activation pins are separately governed and are not task code.
    for environment in sorted(environments):
        old = task_commands(manifest, environment)
        actual = task_commands(actual_manifest, environment)
        for task, commands in old.items():
            if task in selected and actual.get(task) != commands:
                errors.append('changed Linux task closure ' + environment + ':' + task)
    for path, source in snapshot['execution_sources'].items():
        if not retains_work(path, source, read_source(path)):
            errors.append('reduced frozen execution work ' + path)
    return errors


def selected_linux_tasks(workflow, event):
    tasks = set()
    for job, ctx, platform in linux_jobs(workflow, event).values():
        if platform != 'linux-64':
            continue
        for step in job.get('steps', []):
            if 'pixi run' not in step.get('run', '') or not linux_condition(step.get('if'), ctx):
                continue
            source = render(step.get('run', ''), ctx)
            if 'pixi run' not in source:
                continue
            source = source.replace('\\\n', '')
            for match in re.finditer(r'\bpixi\s+(run\s+[^\n]+)', source):
                # A task prefix can be inside command substitution; its closing shell
                # syntax is not part of the Pixi task name.
                words = shlex.shlex(match[1], posix=True)
                words.whitespace_split = True
                tasks.add(task_name(words))
    return tasks
