"""The temporary macOS policy preserves the frozen Linux and nightly inventories."""

from __future__ import annotations

import ast
import copy
import itertools
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest
import yaml

from tests.system.py.ci_execution_contract import (
    concurrency_errors,
    contexts,
    execution_errors,
    smoke_errors,
)

ROOT = Path(__file__).resolve().parents[3]
BASE = json.loads((ROOT / 'tests/fixtures/ci_cadence/baseline.json').read_text())
POLICY = ROOT / 'tests/test-groups.json'
EXPECTED = json.loads((ROOT / 'tests/fixtures/ci_cadence/policy.json').read_text())


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
        observed = [
            p
            for n, _, _, p in contexts(document(ROOT / '.github/workflows/ci.yml'), event)
            if n == name
        ]
        assert observed == ['linux-64'], (
            'CI policy: every retained Linux gate executes on an actual Linux runner'
        )
        assert not current.get('continue-on-error'), (
            'CI policy: every baseline Linux job is required rather than advisory'
        )
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
            if title not in suite_steps:
                assert command_text(actual.get('run', '')) == command_text(step['run']), (
                    'CI policy: baseline Linux non-selection gate commands remain intact'
                )


def test_macos_smoke_and_nightly_select_real_frozen_identities():
    policy = json.loads(POLICY.read_text())
    groups = policy['groups']
    assert {'macos-smoke', 'nightly-full'} <= groups.keys(), (
        'CI policy: visible fixture contract requires declared macos-smoke and nightly-full groups'
    )
    inventory = list(
        dict.fromkeys(
            nodes()
            + BASE.get('scale_nodes', [])
            + [node for cohort in EXPECTED['smoke_witnesses'].values() for node in cohort]
        )
    )
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
    assert not smoke_errors(smoke, EXPECTED['smoke_witnesses']), (
        'CI policy: macOS smoke retains independently reviewed behavioral execution witnesses'
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
    assert not concurrency_errors([regular, nightly]), (
        'CI policy: effective workflow and job identities preserve active and '
        'queued runs across slots'
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
                observed = [p for n, _, _, p in contexts(current, event) if n == name]
                assert observed == ['osx-arm64'], (
                    'CI policy: retained macOS build and qualification jobs use arm64 runners'
                )
                assert not actual.get('continue-on-error'), (
                    'CI policy: macOS build and qualification jobs remain required'
                )
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


@pytest.mark.parametrize('event', ['schedule', 'workflow_dispatch'])
def test_nightly_workflow_executes_the_group_and_retains_result_artifacts(event):
    path = ROOT / '.github/workflows/ci-nightly.yml'
    assert path.is_file(), 'CI policy: nightly workflow exists for execution-path validation'
    policy = json.loads(POLICY.read_text())
    for platform, expected in EXPECTED['nightly'].items():
        assert not execution_errors(
            ROOT, document(path), policy, event, platform, 'nightly-full', expected
        ), (
            'CI policy: every required platform executes, validates and uploads its '
            'own full selection'
        )


@pytest.mark.parametrize('event', ['pull_request', 'push'])
def test_regular_macos_invokes_the_real_smoke_group(event):
    assert not execution_errors(
        ROOT,
        document(ROOT / '.github/workflows/ci.yml'),
        json.loads(POLICY.read_text()),
        event,
        'osx-arm64',
        'macos-smoke',
    ), 'CI policy: regular macOS invokes the same collector and validator as its smoke group'


@pytest.mark.parametrize('event', ['pull_request', 'push'])
def test_linux_task_closure_cannot_reduce_the_frozen_execution(event):
    live = document(ROOT / '.github/workflows/ci.yml')
    for path, source in BASE['execution_sources'].items():
        assert (ROOT / path).read_text() == source, (
            'CI policy: unchanged Linux and qualified SDK task commands retain their '
            'frozen executable source closure'
        )
    group = 'quick' if event == 'pull_request' else 'full'
    assert not execution_errors(
        ROOT, live, json.loads(POLICY.read_text()), event, 'linux-64', group
    ), 'CI policy: preserved Linux identities have collected execution receipts on both events'
