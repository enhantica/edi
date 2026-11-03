"""Exercise the assistant's pull request route to the real WebAssembly build task."""

import fnmatch
from pathlib import Path

import pytest
import yaml

from tests.system.py.ci_execution_contract import contexts, task_commands, value
from tests.system.py.ci_shipped_cadence import invoke_step, task_name

ROOT = Path(__file__).resolve().parents[3]


def apply_changed_path(workflow, context, path):
    filter_step = next(
        step
        for step in workflow['jobs']['changes']['steps']
        if step.get('uses', '').startswith('dorny/paths-filter@')
    )
    filters = yaml.safe_load(filter_step['with']['filters'])
    filter_id = filter_step['id']
    context.update({
        f'steps.{filter_id}.outputs.{name}': str(
            any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
        ).lower()
        for name, patterns in filters.items()
    })
    for name, expression in workflow['jobs']['changes']['outputs'].items():
        if f'steps.{filter_id}.outputs.' in expression:
            result = value(expression, context)
            context[f'needs.changes.outputs.{name}'] = str(result).lower()


@pytest.mark.parametrize(
    'path', ['app/src/assistant_view_model.cpp', 'app/src/assistant_work_report.hpp']
)
def test_assistant_pull_request_runs_wasm_compiler_task(tmp_path, path):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    manifest = (ROOT / 'pixi.toml').read_text()
    for _, job, context, _ in contexts(workflow, 'pull_request', 'slot-a', names=False):
        apply_changed_path(workflow, context, path)
        if not value(job.get('if'), context):
            continue
        for step in job.get('steps', []):
            if 'wasm-build' not in step.get('run', '') or not value(step.get('if'), context):
                continue
            status, observed = invoke_step(tmp_path, workflow, job, step, context)
            if not any(task_name(call['argv']) == 'wasm-build' for call in observed):
                continue
            assert status == 0, 'The actual workflow step must complete with a successful builder'
            assert task_commands(manifest, 'app')['wasm-build'][-1][1] == (
                'bash tools/ci/wasm-build.sh'
            ), 'The selected Pixi task must dispatch the project WebAssembly build script'
            failed, _ = invoke_step(tmp_path, workflow, job, step, context, failure='wasm-build')
            assert failed != 0 and not step.get('continue-on-error'), (
                'A compiler failure must make the assistant PR check fail'
            )
            assert not job.get('continue-on-error'), (
                'A compiler failure must fail the workflow job'
            )
            return
    pytest.fail(f'An assistant-only PR changing {path} must reach an enabled wasm-build step')
