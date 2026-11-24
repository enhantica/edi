"""Offline REST observations at the nightly timing and merged-PR cleanup boundaries."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REPO = 'example/edi'
HEAD, OLD, NEW = (letter * 40 for letter in 'abc')


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools/ci' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page(field, rows, total=None):
    return {'total_count': len(rows) if total is None else total, field: rows}


def run(rid, sha, timestamp):
    return {
        'id': rid,
        'head_sha': sha,
        'head_branch': 'main',
        'event': 'schedule',
        'path': '.github/workflows/ci.yml',
        'status': 'completed',
        'conclusion': 'success',
        'run_attempt': 1,
        'created_at': timestamp,
        'run_started_at': timestamp,
    }


def nightly_history():
    runs = {
        '31': run(31, HEAD, '2026-11-24T02:00:00Z'),
        '29': run(29, OLD, '2026-11-23T00:10:00+02:00'),
        '30': run(30, NEW, '2026-11-22T23:50:00-01:00'),
    }
    jobs = {
        rid: [
            page(
                'jobs',
                [
                    {
                        'id': 100 + int(rid),
                        'run_attempt': 1,
                        'run_id': int(rid),
                        'name': 'system · Linux · 1/1',
                        'status': 'completed',
                        'conclusion': 'success',
                        'started_at': '2026-11-24T02:00:00Z',
                        'completed_at': '2026-11-24T02:10:00Z',
                    }
                ],
            )
        ]
        for rid in runs
    }
    # The first listed earlier run sorts newer as text, but is older as an instant.
    return {
        'runs': runs,
        'jobs': jobs,
        'list': [page('workflow_runs', copy.deepcopy(list(runs.values())))],
        'shards': {sha: {'Linux': 1} for sha in (HEAD, OLD, NEW)},
    }


def check_replay(gate, tmp_path, history):
    saved = tmp_path / 'history.json'
    saved.write_text(json.dumps(history))
    return gate.main([
        '--nightly',
        '--history',
        str(saved),
        '--record',
        str(tmp_path / 'verdict.json'),
        '--run-id',
        '31',
        '--head-sha',
        HEAD,
    ])


def test_nightly_baseline_uses_parsed_order_and_complete_no_baseline(tmp_path, capsys):
    gate = tool('system_shard_time')
    history = nightly_history()
    assert check_replay(gate, tmp_path, history) == 0, 'A complete nightly admits comparison'
    assert 'baseline is run 30' in capsys.readouterr().out, (
        'The baseline is the newest earlier instant even when API order and text order differ'
    )
    history['list'][0] = page('workflow_runs', [history['runs']['31']])
    assert check_replay(gate, tmp_path, history) == 0, 'A complete empty prior history is allowed'
    receipt = json.loads((tmp_path / 'verdict.json').read_text())
    assert (receipt['baseline'], receipt['run'], receipt['head_sha']) == (None, 31, HEAD), (
        'Only a whole search can record no earlier baseline for the exact current run'
    )


@pytest.mark.parametrize(
    'fault',
    [
        'short',
        'duplicate-run',
        'missing-run-id',
        'cap',
        'moving-total',
        'duplicate-job',
        'current-identity',
        'current-time',
        'detail-head',
        'detail-path',
        'detail-time',
        'missing-detail',
        'missing-listed-head',
        'missing-listed-status',
        'different-job-attempt',
    ],
)
def test_nightly_never_judges_unobserved_or_inconsistent_history(tmp_path, capsys, fault):
    history = nightly_history()
    listed = history['list'][0]['workflow_runs']
    if fault in {'short', 'cap'}:
        history['list'][0]['total_count'] = 4 if fault == 'short' else 1000
    elif fault == 'duplicate-run':
        listed[1] = copy.deepcopy(listed[0])
    elif fault == 'missing-run-id':
        del listed[1]['id']
    elif fault == 'moving-total':
        rows = [run(rid, OLD, '2026-11-21T00:00:00Z') for rid in range(100, 200)]
        history['list'] = [page('workflow_runs', rows, 101), page('workflow_runs', listed)]
    elif fault == 'duplicate-job':
        jobs = history['jobs']['30'][0]['jobs']
        history['jobs']['30'][0] = page('jobs', [*jobs, {**jobs[0], 'name': 'unrelated'}])
    elif fault == 'current-identity':
        history['runs']['31']['event'] = 'push'
    elif fault == 'current-time':
        history['runs']['31']['created_at'] = '2026-11-24T02:00:00'
    elif fault == 'missing-detail':
        del history['runs']['30']
    elif fault in {'missing-listed-head', 'missing-listed-status'}:
        del listed[2]['head_sha' if fault.endswith('head') else 'status']
    elif fault == 'different-job-attempt':
        history['jobs']['30'][0]['jobs'][0]['run_attempt'] = 2
    else:
        field, value = {
            'detail-head': ('head_sha', OLD),
            'detail-path': ('path', '.github/workflows/other.yml'),
            'detail-time': ('created_at', '2026-11-21T06:00:00Z'),
        }[fault]
        history['runs']['30'][field] = value
    assert check_replay(tool('system_shard_time'), tmp_path, history) == 2, (
        'Each incomplete or conflicting GitHub history refuses before comparison'
    )
    assert 'no baseline' not in capsys.readouterr().out, (
        'A transport or identity defect cannot masquerade as an exhaustive search'
    )
    assert not (tmp_path / 'verdict.json').exists(), (
        'An unproved history must not produce a durable no-baseline record'
    )


def merged_pr_records():
    branch = 'feature/reused'
    head = {'ref': branch, 'repo': {'full_name': REPO}, 'sha': HEAD}
    selected = {
        'id': 41,
        'head_repository': {'full_name': REPO},
        'head_branch': branch,
        'head_sha': HEAD,
        'status': 'completed',
        'event': 'pull_request',
        'pull_requests': [{'number': 7, 'head': head}],
    }
    return {
        'pulls/7': {
            'number': 7,
            'commits': 2,
            'state': 'closed',
            'merged_at': 'now',
            'head': head,
        },
        'pulls/7/commits?per_page=100': ([{'sha': HEAD}], 'commits-page-2'),
        'commits-page-2': [{'sha': OLD}],
        'pulls?state=open&per_page=100': [
            {'number': 8, 'head': {**head, 'ref': 'different-branch', 'sha': OLD}}
        ],
        'actions/runs?branch=feature%2Freused&per_page=100': (
            page(
                'workflow_runs',
                [
                    selected,
                    {**selected, 'id': 42, 'head_sha': NEW},
                    {**selected, 'id': 43, 'head_repository': {'full_name': 'fork/edi'}},
                ],
                6,
            ),
            'runs-page-2',
        ),
        'runs-page-2': page(
            'workflow_runs',
            [
                {**selected, 'id': 44, 'status': 'in_progress'},
                {**selected, 'id': 45, 'head_sha': OLD},
                {**selected, 'id': 46, 'head_branch': 'different-branch'},
            ],
            6,
        ),
        'actions/runs/41/artifacts?per_page=100': (
            page(
                'artifacts',
                [
                    {'id': 77, 'name': 'unit-log'},
                    {'id': 78, 'name': 'release-plan-7'},
                ],
                4,
            ),
            'artifacts-page-2',
        ),
        'artifacts-page-2': page(
            'artifacts',
            [
                {'id': 79, 'name': 'crysta-sdk-pinned'},
                {'id': 80, 'name': 'expired', 'expired': True},
            ],
            4,
        ),
        'actions/runs/45/artifacts?per_page=100': page(
            'artifacts', [{'id': 82, 'name': 'active-head-log'}]
        ),
    }


@pytest.mark.parametrize(
    'fault',
    [
        'none',
        'unmerged',
        'open-shared',
        'short-commits',
        'short-runs',
        'duplicate-runs',
        'moving-total',
        'short-artifacts',
        'duplicate-artifacts',
        'same-commit-earlier-pr',
        'same-commit-dispatch',
        'incomplete-open-head',
        'unnamed-artifact',
    ],
)
def test_artifact_cleanup_admits_only_a_merged_requests_own_runs(monkeypatch, fault):
    gate = tool('branch_artifacts')
    records = merged_pr_records()
    if fault == 'unmerged':
        records['pulls/7']['merged_at'] = None
    elif fault == 'open-shared':
        records['pulls?state=open&per_page=100'][0]['head']['ref'] = 'feature/reused'
    elif fault == 'short-commits':
        records['commits-page-2'].clear()
    elif fault == 'short-runs':
        records['runs-page-2']['workflow_runs'].pop()
    elif fault == 'duplicate-runs':
        records['runs-page-2']['workflow_runs'][0]['id'] = 41
    elif fault == 'moving-total':
        records['runs-page-2']['total_count'] -= 1
    elif fault == 'short-artifacts':
        records['artifacts-page-2']['artifacts'].pop()
    elif fault == 'duplicate-artifacts':
        records['artifacts-page-2']['artifacts'][0]['id'] = 77
    elif fault == 'incomplete-open-head':
        del records['pulls?state=open&per_page=100'][0]['head']['sha']
    elif fault == 'unnamed-artifact':
        del records['artifacts-page-2']['artifacts'][0]['name']
    elif fault in {'same-commit-earlier-pr', 'same-commit-dispatch'}:
        previous = fault == 'same-commit-earlier-pr'
        records['runs-page-2']['workflow_runs'][0].update(
            status='completed',
            event='pull_request' if previous else 'workflow_dispatch',
            pull_requests=[{'number': 6}] if previous else [],
        )
        records['actions/runs/44/artifacts?per_page=100'] = page(
            'artifacts', [{'id': 81, 'name': 'other-run-log'}]
        )

    def fetch(path):
        relative = path.removeprefix(f'repos/{REPO}/')
        assert relative in records, f'The offline REST witness contains the requested {relative}'
        record = records[relative]
        return record if isinstance(record, tuple) else (record, '')

    deleted = []
    monkeypatch.setattr(gate, 'gh_fetch', fetch)
    monkeypatch.setattr(gate, 'delete', lambda _repo, artifacts: deleted.extend(artifacts))
    status = gate.main(['--repo', REPO, '--pr', '7'])
    scoped = {'none', 'same-commit-earlier-pr', 'same-commit-dispatch', 'unnamed-artifact'}
    expected = [77] if fault in scoped else []
    assert [artifact['id'] for artifact in deleted] == expected, (
        'Only debris owned by the merged request reaches the deletion boundary'
    )
    assert status == (0 if fault in scoped | {'unmerged', 'open-shared'} else 2), (
        'Incomplete or duplicate pagination fails closed before any deletion'
    )
