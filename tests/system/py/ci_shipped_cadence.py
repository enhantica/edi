"""Observe rendered suite steps without starting their builds or numerical suites."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tests.system.py.ci_execution_contract import (
    contexts,
    prerequisites_ready,
    render,
    run_settings,
    value,
)

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
        'if k.endswith("_SKIP_NIGHTLY_GROUP")}})+"\\n")\n'
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
    args = list(argv)
    if not args or args.pop(0) != 'run':
        return ''
    while args and args[0].startswith('-'):
        flag = args.pop(0)
        if flag in {'-e', '--environment'}:
            args.pop(0)
    return args[0] if args else ''


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
