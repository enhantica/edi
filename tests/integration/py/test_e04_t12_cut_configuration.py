"""Recreate repository resources and admit the workflow's real event refs."""

from __future__ import annotations

import ast
import copy
import fnmatch
import importlib.util
import json
import subprocess
import sys
from itertools import starmap
from pathlib import Path
from urllib.parse import unquote

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def load_cutover():
    path = ROOT / 'tools/public-release/cutover.py'
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('cut_configuration_vehicle', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RepositoryAPI:
    def __init__(self):
        self.created = False
        self.mutations = []
        self.wanted = [
            {'name': 'bug', 'color': '123456', 'description': 'A defect'},
            {'name': 'analysis / science', 'color': 'abcdef', 'description': 'A data question'},
        ]
        self.labels = {
            'bug': {'name': 'bug', 'color': 'd73a4a', 'description': 'Default bug'},
            'unused': {'name': 'unused', 'color': 'ffffff', 'description': ''},
        }
        self.ruleset = {
            'id': 9,
            'name': 'Private policy',
            'target': 'branch',
            'enforcement': 'active',
            'conditions': {'ref_name': {'include': ['refs/heads/main'], 'exclude': []}},
            'rules': [
                {
                    'type': 'required_status_checks',
                    'parameters': {
                        'required_status_checks': [{'context': 'core'}],
                        'strict_required_status_checks_policy': True,
                    },
                }
            ],
        }
        self.real_run = subprocess.run

    def run(self, argv, *, input=None, **kwargs):  # noqa: PLR0912 - explicit API state machine
        argv = list(argv)
        if argv[:2] != ['gh', 'api']:
            if 'push' in argv:
                self.mutations.append(('PUSH', 'snapshot', None))
                return subprocess.CompletedProcess(argv, 0, '', '')
            return self.real_run(argv, input=input, **kwargs)
        method = argv[argv.index('-X') + 1] if '-X' in argv else 'GET'
        path = argv[argv.index('-X') + 2] if '-X' in argv else argv[2]
        body = json.loads(input) if input else None
        code, data, error = 0, {}, ''
        if method == 'GET':
            if 'edi-archive-' in path:
                code, error = 1, 'Not Found'
            elif path.endswith('/pulls?state=open&per_page=100'):
                data = []
            elif path.endswith('/labels?per_page=100'):
                data = list(self.labels.values()) if self.created else copy.deepcopy(self.wanted)
            elif path.endswith('/rulesets/9'):
                data = copy.deepcopy(self.ruleset)
            elif path.endswith('/rulesets'):
                data = [{'id': 9}]
            elif path.endswith('/runner-groups'):
                data = {
                    'runner_groups': [
                        {
                            'id': 4,
                            'name': 'Fleet',
                            'visibility': 'selected',
                            'allows_public_repositories': True,
                        }
                    ]
                }
            elif '/actions/secrets/' in path or '/actions/variables/' in path:
                data = {'name': path.rsplit('/', 1)[-1], 'visibility': 'selected'}
            elif path == 'repos/enhantica/edi':
                data = {
                    'id': 22 if self.created else 11,
                    'private': True,
                    'description': 'Diffraction',
                }
            else:
                code, error = 1, 'Unexpected read ' + path
        else:
            self.mutations.append((method, path, body))
            if method == 'POST' and path == 'orgs/enhantica/repos':
                self.created = True
            elif path == 'repos/enhantica/edi/labels' and method == 'POST':
                if body['name'] in self.labels:
                    code, error = 1, 'Validation Failed: label already exists'
                else:
                    self.labels[body['name']] = body
            elif path.startswith('repos/enhantica/edi/labels/'):
                raw = path.split('/labels/', 1)[1]
                assert ' ' not in raw and '/' not in raw, (
                    'label API segments must encode spaces and slashes'
                )
                name = unquote(raw)
                if name not in self.labels:
                    code, error = 1, 'Not Found'
                elif method == 'DELETE':
                    del self.labels[name]
                elif method == 'PATCH':
                    renamed = body.get('new_name', name)
                    fields = {key: value for key, value in body.items() if key != 'new_name'}
                    self.labels[renamed] = {**self.labels.pop(name), **fields, 'name': renamed}
                else:
                    code, error = 1, 'Unexpected label operation'
        return subprocess.CompletedProcess(argv, code, json.dumps(data), error)


@pytest.fixture
def cut_replay(tmp_path, monkeypatch):
    tool = load_cutover()
    root = tmp_path / 'snapshot'
    root.mkdir()
    original = subprocess.run
    for args in (['init', '-q', '-b', 'main'],):
        result = original(['git', '-C', str(root), *args], capture_output=True, check=False)
        assert result.returncode == 0, 'the cut replay requires a real fresh local repository'
    (root / 'README.md').write_text('Diffraction.\n')
    for args in (
        ['add', '.'],
        [
            '-c',
            'user.name=Contributor',
            '-c',
            'user.email=person@example.invalid',
            'commit',
            '-qm',
            'Start the project',
        ],
    ):
        result = original(['git', '-C', str(root), *args], capture_output=True, check=False)
        assert result.returncode == 0, 'the cut replay requires a committed public-safe snapshot'
    api = RepositoryAPI()
    monkeypatch.setattr(tool.subprocess, 'run', api.run)
    arguments = ['cut', '--date', '2026-10-04', '--snapshot', str(root)]
    return tool, api, arguments


@pytest.mark.parametrize('vehicle', ['ordinary', 'encoded'])
def test_e04_t12_recreation_reconciles_existing_labels_and_reaches_all_grants(cut_replay, vehicle):
    tool, api, arguments = cut_replay
    if vehicle == 'encoded':
        api.labels['analysis / science'] = {
            'name': 'analysis / science',
            'color': '000000',
            'description': 'Old colour',
        }
        api.labels['unused / default'] = {
            'name': 'unused / default',
            'color': 'ffffff',
            'description': '',
        }
    assert tool.main([*arguments, '--apply']) == 0, (
        'overlapping default labels must not interrupt the cut before its remaining settings'
    )
    assert api.labels == {label['name']: label for label in api.wanted}, (
        'recreated labels must preserve wanted colours/descriptions and remove unwanted defaults'
    )
    paths = {path for _method, path, _body in api.mutations}
    for path in (
        'repos/enhantica/edi/rulesets',
        'repos/enhantica/edi/environments/crysta-sdk',
        'repos/enhantica/edi/actions/permissions/fork-pr-contributor-approval',
        'orgs/enhantica/actions/runner-groups/4/repositories/22',
        'orgs/enhantica/actions/secrets/ENHANTICA_APP_KEY/repositories/22',
        'orgs/enhantica/actions/variables/ENHANTICA_APP_ID/repositories/22',
    ):
        assert path in paths, (
            'the cut must reach every later configuration and grant step: ' + path
        )


def test_e04_t12_check_only_cut_performs_no_mutation(cut_replay):
    tool, api, arguments = cut_replay
    before = copy.deepcopy(api.labels)
    assert tool.main(arguments) == 0, 'check-only must fully read and plan a valid cut'
    assert not api.mutations and not api.created and api.labels == before, (
        'check-only cut rehearsal must leave repositories, labels and grants untouched'
    )


def evaluate(node, values):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
        return evaluate(node.left, values) == evaluate(node.comparators[0], values)
    if isinstance(node, ast.BoolOp):
        result = evaluate(node.values[0], values)
        for operand in node.values[1:]:
            if isinstance(node.op, ast.And):
                result = evaluate(operand, values) if result else result
            else:
                result = result or evaluate(operand, values)
        return result
    pytest.fail('the event observer must explicitly interpret every workflow condition')


def condition(expression, *, fork, event):
    if not expression:
        return True
    text = str(expression).strip().removeprefix('${{').removesuffix('}}').strip()
    text = text.replace('github.event.pull_request.head.repo.fork', 'fork')
    text = text.replace('github.event_name', 'event')
    text = text.replace('false', 'False').replace('true', 'True')
    text = text.replace('&&', ' and ').replace('||', ' or ')
    return evaluate(ast.parse(text, mode='eval').body, {'fork': fork, 'event': event})


def environment_name(value, *, fork, event):
    if isinstance(value, dict):
        value = value.get('name', '')
    if not value or '${{' not in str(value):
        return value or ''
    text = str(value).strip().removeprefix('${{').removesuffix('}}').strip()
    text = text.replace('github.event.pull_request.head.repo.fork', 'fork')
    text = text.replace('github.event_name', 'event')
    text = text.replace('false', 'False').replace('true', 'True')
    return evaluate(
        ast.parse(text.replace('&&', ' and ').replace('||', ' or '), mode='eval').body,
        {'fork': fork, 'event': event},
    )


@pytest.mark.parametrize(
    ('event', 'fork', 'ref'),
    [
        ('push', False, 'refs/heads/main'),
        ('pull_request', False, 'refs/pull/17/merge'),
        ('pull_request', True, 'refs/pull/23/merge'),
    ],
)
def test_e04_t12_environment_policy_matches_workflow_events(cut_replay, event, fork, ref):
    tool, api, arguments = cut_replay
    # Keep label reconciliation from masking the independent environment escape.
    api.labels = {}
    assert tool.main([*arguments, '--apply']) == 0, (
        'the policy observer must reach actual environment configuration'
    )
    prepared = ROOT / 'tools/public-release/github/workflows/ci.yml'
    path = prepared if prepared.is_file() else ROOT / '.github/workflows/ci.yml'
    doc = yaml.safe_load(path.read_text())
    policies = [
        body['name']
        for _method, path, body in api.mutations
        if path.endswith('/deployment-branch-policies')
    ]
    prefix = 'refs/heads/'
    selector = ref.removeprefix(prefix) if ref.startswith(prefix) else ref
    admitted = any(
        len(selector.split('/')) == len(policy.split('/'))
        and all(
            starmap(fnmatch.fnmatchcase, zip(selector.split('/'), policy.split('/'), strict=True))
        )
        for policy in policies
    )
    settings = [
        body for _method, path, body in api.mutations if path.endswith('/environments/crysta-sdk')
    ]
    assert settings and settings[0]['deployment_branch_policy'] == {
        'protected_branches': False,
        'custom_branch_policies': True,
    }, 'the observed branch patterns must be the policy the environment actually uses'
    observe_jobs(doc, admitted=admitted, fork=fork, event=event)
    if event == 'pull_request':
        with pytest.raises(AssertionError, match='admit each assigned'):
            observe_jobs(doc, admitted=False, fork=fork, event=event)
    if fork:
        damaged = copy.deepcopy(doc)
        mint = next(
            step
            for step in damaged['jobs']['pin-currency']['steps']
            if 'create-github-app-token' in str(step.get('uses', ''))
        )
        mint['if'] = 'true'
        with pytest.raises(AssertionError, match='private token steps'):
            observe_jobs(damaged, admitted=admitted, fork=fork, event=event)


def observe_jobs(doc, *, admitted, fork, event):
    active = []
    for name, job in doc['jobs'].items():
        if not condition(job.get('if'), fork=fork, event=event):
            continue
        active.append(name)
        environment = environment_name(job.get('environment'), fork=fork, event=event)
        if environment == 'crysta-sdk':
            assert admitted, (
                'recreated environment must admit each assigned main/trusted-PR job: ' + name
            )
        for step in job.get('steps', []):
            token = 'create-github-app-token' in str(
                step.get('uses', '')
            ) or 'ENHANTICA_APP_KEY' in json.dumps(step)
            if token and condition(step.get('if'), fork=fork, event=event):
                assert not fork and environment == 'crysta-sdk', (
                    'private token steps require trusted events in the reviewed environment'
                )
    assert 'pin-currency' in active, (
        'fork events must retain the unconditional token-free pin check'
    )
    if not fork:
        for name in ('native', 'audit', 'core', 'notebooks', 'cli-python', 'docs', 'app'):
            assert name in active, (
                'the event control must reach every trusted SDK consumer job: ' + name
            )
