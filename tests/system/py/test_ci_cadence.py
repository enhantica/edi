"""The temporary macOS policy preserves the frozen Linux and nightly inventories."""

from __future__ import annotations

import ast
import copy
import itertools
import json
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = json.loads((ROOT / 'tests/fixtures/ci_cadence/baseline.json').read_text())
POLICY = ROOT / 'tests/test-groups.json'


def document(path):
    return yaml.safe_load(path.read_text())


def nodes():
    return [
        line.split('\t', 1)[1]
        for line in (ROOT / 'tests/per-pr-runtimes.tsv').read_text().splitlines()
        if line and not line.startswith('#')
    ]


def expand(group, inventory):
    selected = []
    for tier in group.get('tiers', []):
        selected.extend(
            node
            for node in inventory
            if node.split('::')[0].startswith('tests/' + tier.rstrip('/') + '/')
        )
    selected.extend(group.get('nodes', []))
    return selected


def selection_errors(group, inventory, required):
    selected = expand(group, inventory)
    errors = []
    if not selected:
        errors.append('empty')
    if len(selected) != len(set(selected)):
        errors.append('duplicate')
    if set(selected) - set(inventory):
        errors.append('unknown')
    if set(required) - set(selected):
        errors.append('omitted')
    return errors


def context(event, row=None):
    return {
        'github.event_name': event,
        'github.ref': 'refs/heads/main' if event == 'push' else 'refs/pull/42/merge',
        'github.event.pull_request.head.repo.fork': False,
        'github.event.pull_request.number': 42,
        'inputs.core_only': False,
        'needs.changes.result': 'success',
        'needs.changes.outputs.app_build': 'true',
        'steps.sdk-pack.outcome': 'success',
        **{'matrix.' + key: value for key, value in (row or {}).items()},
    }


def expression(value, ctx):
    if isinstance(value, bool) or value is None:
        return value is not False
    text = value.strip().removeprefix('${{').removesuffix('}}').strip()
    for key in sorted(ctx, key=len, reverse=True):
        text = re.sub(r'(?<![\w.])' + re.escape(key) + r'(?![\w.])', repr(ctx[key]), text)
    for call, replacement in [
        ('cancelled()', 'False'),
        ('success()', 'True'),
        ('always()', 'True'),
        ('failure()', 'False'),
    ]:
        text = text.replace(call, replacement)
    text = re.sub(r'\btrue\b', 'True', text)
    text = re.sub(r'\bfalse\b', 'False', text)
    text = text.replace('&&', ' and ').replace('||', ' or ')
    text = re.sub(r'!(?!=)', ' not ', text).strip()
    tree = ast.parse(text, mode='eval')
    allowed = (
        ast.Expression,
        ast.Constant,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Load,
    )
    assert all(isinstance(node, allowed) for node in ast.walk(tree)), (
        'CI policy: unsupported workflow condition cannot prove retained execution'
    )
    return bool(eval(compile(tree, '<workflow-condition>', 'eval'), {'__builtins__': {}}, {}))  # noqa: S307


def rendered(value, ctx):
    def replace(match):
        key = match[1].strip()
        assert key in ctx, (
            'CI policy: every matrix interpolation must have an independent concrete value'
        )
        return str(ctx[key])

    return re.sub(r'\$\{\{(.*?)\}\}', replace, str(value))


def jobs(workflow, event, platform):
    result = {}
    for key, job in workflow['jobs'].items():
        matrix = job.get('strategy', {}).get('matrix', {})
        axes = {k: v for k, v in matrix.items() if k not in {'include', 'exclude'}}
        rows = (
            [dict(zip(axes, row, strict=True)) for row in itertools.product(*axes.values())]
            if axes
            else []
        )
        rows += matrix.get('include', [])
        for row in rows or [{}]:
            if row.get('platform') not in {None, platform}:
                continue
            if any(
                all(row.get(k) == v for k, v in item.items()) for item in matrix.get('exclude', [])
            ):
                continue
            ctx = context(event, row)
            if not expression(job.get('if'), ctx):
                continue
            name = rendered(job.get('name', key), ctx)
            result[name] = (job, ctx)
    return result


def command_text(script):
    return '\n'.join(
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    )


def selection_trace(script, ctx):
    source = rendered(script, ctx)
    run = subprocess.run(
        ['/bin/bash', '-e', '-c', 'pixi() { printf "%s\\n" "$*"; };\n' + source],
        env={'PATH': '/usr/bin:/bin'},
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )
    assert run.returncode == 0, (
        'CI policy: the concrete Linux group command must execute without a hidden failing branch'
    )
    return run.stdout.splitlines()


@pytest.mark.parametrize('event', ['pull_request', 'push'])
def test_linux_keeps_frozen_groups_and_gate_commands(event):  # noqa: PLR0914
    policy = json.loads(POLICY.read_text())
    group = policy['groups']['quick' if event == 'pull_request' else 'full']
    inventory = nodes()
    selected = expand(group, inventory)
    if BASE['repo'] == 'edi':
        selected += expand(policy['groups']['app'], inventory)
    frozen_groups = json.loads(BASE['files']['tests/test-groups.json'])['groups']
    frozen = expand(frozen_groups['quick' if event == 'pull_request' else 'full'], BASE['nodes'])
    if BASE['repo'] == 'edi':
        frozen += expand(frozen_groups['app'], BASE['nodes'])
    errors = selection_errors({'nodes': selected}, inventory, frozen)
    assert not errors, (
        'CI policy: every frozen Linux test stays in regular PR and landed-head selections'
    )
    old = jobs(yaml.safe_load(BASE['files']['.github/workflows/ci.yml']), event, 'Linux')
    live = jobs(document(ROOT / '.github/workflows/ci.yml'), event, 'Linux')
    ignored = ('performance', 'wheels', 'publish', 'cli-native')
    suite_steps = {
        'Hidden numerical suite (cpp surface)',
        'Hidden numerical suite (Python tiers)',
        'Tests (declared group)',
        'Full Release suite on merge (GCC -O3, every case)',
    }
    for name, (job, ctx) in old.items():
        if name.startswith(ignored):
            continue
        assert name in live, (
            'CI policy: every baseline Linux gate job must remain executable on this event'
        )
        current, current_ctx = live[name]
        for step in job.get('steps', []):
            if (
                'run' not in step
                or 'pixi run' not in step['run']
                or step.get('continue-on-error')
                or not expression(step.get('if'), ctx)
            ):
                continue
            title = step.get('name')
            if not title or title.startswith((
                'Report',
                'Compiler cache',
                'ccache',
                'Python harness',
                'Coverage job summary',
                'Prepare',
            )):
                continue
            matches = [s for s in current.get('steps', []) if s.get('name') == title]
            assert len(matches) == 1, (
                'CI policy: a baseline Linux gate has exactly one matching executable step'
            )
            actual = matches[0]
            assert expression(actual.get('if'), current_ctx), (
                'CI policy: a Linux gate cannot become skipped or advisory'
            )
            assert not actual.get('continue-on-error'), (
                'CI policy: a Linux gate cannot become skipped or advisory'
            )
            if title in suite_steps:
                assert selection_trace(actual['run'], current_ctx) == selection_trace(
                    step['run'], ctx
                ), (
                    'CI policy: Linux executes the original full group for PR and '
                    'landed-head read-back'
                )
            else:
                assert command_text(actual.get('run', '')) == command_text(step['run']), (
                    'CI policy: baseline Linux non-selection gate commands remain intact'
                )


def test_macos_smoke_and_nightly_select_real_frozen_identities():
    policy = json.loads(POLICY.read_text())
    groups = policy['groups']
    assert {'macos-smoke', 'nightly-full'} <= groups.keys(), (
        'CI policy: visible fixture contract requires declared macos-smoke and nightly-full groups'
    )
    inventory = list(dict.fromkeys(nodes() + BASE.get('scale_nodes', [])))
    required = BASE['nodes'] + BASE.get('scale_nodes', [])
    errors = selection_errors(groups['nightly-full'], inventory, required)
    assert not errors, (
        'CI policy: nightly covers every frozen identity plus restored scale cases exactly once'
    )
    smoke = expand(groups['macos-smoke'], inventory)
    assert not selection_errors(groups['macos-smoke'], inventory, []), (
        'CI policy: macOS smoke is nonempty, unique and contains only collected identities'
    )
    native = {node for node in BASE['nodes'] if node.startswith('tests/unit/cpp/')}
    assert native <= set(smoke), (
        'CI policy: native unit and arm64 numeric-pin identities remain in the macOS smoke cohort'
    )
    python_smoke = [node.lower() for node in smoke if '.py::' in node]
    for witness in ('thread', 'scalar', 'simd', 'import', 'cli'):
        assert any(witness in node for node in python_smoke), (
            'CI policy: smoke carries thread, scalar/SIMD, import and CLI execution witnesses'
        )


@pytest.mark.parametrize('damage', ['omitted', 'duplicate', 'empty', 'unknown'])
def test_selection_auditor_reaches_each_inventory_escape(damage):
    inventory = [
        'tests/unit/py/test_pin.py::test_arm64',
        'tests/system/py/test_scan.py::test_full_scan',
    ]
    good = {'nodes': list(inventory)}
    assert not selection_errors(good, inventory, inventory), (
        'CI policy: a complete independently planted identity list is admitted'
    )
    bad = copy.deepcopy(good)
    if damage == 'omitted':
        bad['nodes'].pop()
    elif damage == 'duplicate':
        bad['nodes'].append(inventory[0])
    elif damage == 'empty':
        bad['nodes'].clear()
    else:
        bad['nodes'][0] = 'tests/unit/py/test_pin.py::invented'
    assert damage in selection_errors(bad, inventory, inventory), (
        'CI policy: each inventory escape reaches and fails its matching property'
    )


def test_moved_tests_gain_no_skip_or_xfail():
    for path in {node.split('::')[0] for node in BASE['nodes'] if '.py::' in node}:
        file = ROOT / path
        assert file.is_file(), (
            'CI policy: a moved Python test source remains available to the nightly collector'
        )
        tree = ast.parse(file.read_text())
        calls = Counter(
            ast.dump(node, include_attributes=False)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and any(token in ast.unparse(node.func) for token in ('skip', 'xfail'))
        )
        assert not calls - Counter(BASE['nonexecution'].get(path, [])), (
            'CI policy: moving tests does not add skips or expected failures to the frozen sources'
        )


def test_nightly_and_regular_workflows_cannot_cancel_each_other_or_active_rounds():
    regular = document(ROOT / '.github/workflows/ci.yml')
    path = ROOT / '.github/workflows/ci-nightly.yml'
    assert path.is_file(), (
        'CI policy: visible fixture contract requires scheduled and '
        'manually dispatched main nightlies'
    )
    nightly = document(path)
    trigger = nightly.get('on', nightly.get(True, {}))
    assert trigger.get('schedule'), (
        'CI policy: nightly has both a clock trigger and an on-demand repair route'
    )
    assert 'workflow_dispatch' in trigger, (
        'CI policy: nightly has both a clock trigger and an on-demand repair route'
    )
    for workflow in (regular, nightly):
        assert workflow.get('concurrency', {}).get('cancel-in-progress') is False, (
            'CI policy: an informative CI or nightly run survives subsequent triggers'
        )
    a = regular['concurrency']['group']
    b = nightly['concurrency']['group']
    a = a.replace('${{ github.workflow }}', str(regular['name']))
    b = b.replace('${{ github.workflow }}', str(nightly['name']))
    assert a != b, 'CI policy: regular and nightly runs have disjoint concurrency identities'
    assert 'github.ref' in a or 'pull_request.number' in a, (
        'CI policy: two task branches do not share a cancellation identity'
    )
    text = path.read_text()
    assert 'nightly-full' in text, (
        'CI policy: the nightly workflow executes the declared full selection'
    )
    if BASE['repo'] == 'edi':
        assert 'Linux' in text, (
            'CI policy: restored scale cases execute in both Linux and macOS nightly jobs'
        )
        assert 'macOS' in text, (
            'CI policy: restored scale cases execute in both Linux and macOS nightly jobs'
        )
    else:
        assert 'macOS' in text, (
            'CI policy: the full numerical nightly executes on the macOS runner'
        )
    assert 'execution_report' in json.loads(POLICY.read_text()), (
        'CI policy: the selection authority declares the executed-result validator interface'
    )


def test_restored_scale_assertions_and_regular_small_scan_are_preserved():
    if BASE['repo'] != 'edi':
        return
    target = ROOT / 'tests/system/py/test_scan_scale.py'
    assert target.is_file(), (
        'CI policy: restore the deferred scale checks to the system tier '
        'for both nightly platforms'
    )
    expected = ast.parse(BASE['scale_source']).body[1:]
    actual = ast.parse(target.read_text()).body[1:]
    assert [ast.dump(node) for node in actual] == [ast.dump(node) for node in expected], (
        'CI policy: scale execution retains every existing assertion, fixture and numeric limit'
    )
    for group in ('quick', 'full'):
        selected = expand(json.loads(POLICY.read_text())['groups'][group], nodes())
        assert any('test_scan_app_execution.py::' in node for node in selected), (
            'CI policy: the small real scan remains on regular CI'
        )


def test_regular_macos_keeps_native_build_and_sdk_qualification():
    frozen = yaml.safe_load(BASE['files']['.github/workflows/ci.yml'])
    current = document(ROOT / '.github/workflows/ci.yml')
    witnesses = (
        'Build C++ extension',
        'Pack and qualify',
        'SDK consumer smoke',
        'Build the native code',
        'The crysta consumer proof',
    )
    for event in ('pull_request', 'push'):
        old = jobs(frozen, event, 'macOS')
        live = jobs(current, event, 'macOS')
        for name, (job, _ctx) in old.items():
            if 'macOS' not in name:
                continue
            for step in job.get('steps', []):
                if not str(step.get('name', '')).startswith(witnesses):
                    continue
                assert name in live, (
                    'CI policy: macOS build and qualification retain their platform job'
                )
                actual, current_ctx = live[name]
                matches = [s for s in actual['steps'] if s.get('name') == step['name']]
                assert len(matches) == 1, (
                    'CI policy: each macOS qualification witness remains present once'
                )
                assert expression(matches[0].get('if'), current_ctx), (
                    'CI policy: a macOS qualification step must execute on the current event'
                )
                assert not matches[0].get('continue-on-error'), (
                    'CI policy: macOS qualification failures must gate the SDK consumer'
                )
                assert command_text(matches[0]['run']) == command_text(step['run']), (
                    'CI policy: macOS SDK packing and consumer qualification retain '
                    'their baseline commands'
                )


def test_nightly_workflow_executes_the_group_and_retains_result_artifacts():
    path = ROOT / '.github/workflows/ci-nightly.yml'
    assert path.is_file(), (
        'CI policy: nightly workflow exists before its execution wiring can be judged'
    )
    workflow = document(path)
    commands = [
        command_text(step['run'])
        for job in workflow['jobs'].values()
        for step in job.get('steps', [])
        if 'run' in step
    ]
    group = json.loads(POLICY.read_text())['groups']['nightly-full']
    task = group.get('task')
    assert isinstance(task, str), (
        'CI policy: nightly selection names its executable declared group task'
    )
    assert any(
        re.search(r'\bpixi\s+run\b[^\n]*\b' + re.escape(task) + r'\b', command)
        for command in commands
    ), (
        'CI policy: a comment or unused group declaration cannot stand '
        'for the nightly suite invocation'
    )
    upload = [
        step.get('with', {})
        for job in workflow['jobs'].values()
        for step in job.get('steps', [])
        if str(step.get('uses', '')).startswith('actions/upload-artifact@')
    ]
    assert any(
        'ci-selection-' in str(item.get('name', '')) and item.get('if-no-files-found') == 'error'
        for item in upload
    ), 'CI policy: nightly uploads executed-identity records and refuses a missing report'
    validator = json.loads(POLICY.read_text())['execution_report']['command']
    target = next((word for word in validator if word.endswith('.py')), '')
    assert target, 'CI policy: the execution report command has a concrete validator source'

    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    tasks = dict(manifest.get('tasks', {}))
    for feature in manifest.get('feature', {}).values():
        tasks.update(feature.get('tasks', {}))
    seen = set()

    def closure(name):
        assert name not in seen, 'CI policy: executable group dependencies contain no cycle'
        seen.add(name)
        spec = tasks[name]
        if isinstance(spec, str):
            return [spec]
        own = spec.get('cmd', '')
        result = [' '.join(own) if isinstance(own, list) else own]
        for child in spec.get('depends-on', []):
            result.extend(closure(child if isinstance(child, str) else child['task']))
        seen.remove(name)
        return result

    invoked = commands + closure(task)
    assert any(target in command for command in invoked), (
        'CI policy: the full nightly execution path actually invokes the result validator'
    )
    if any('crysta-sdk-' in str(item.get('name', '')) for item in upload):
        assert any('sdk-pack' in command or 'pack-sdk' in command for command in commands), (
            'CI policy: a nightly SDK upload retains the normal pack-and-qualify producer'
        )
