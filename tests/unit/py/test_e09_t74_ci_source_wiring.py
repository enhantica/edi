"""development hub  unit 8: every CI consumer receives the same per-run resolution."""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONSUMERS = {'audit', 'core', 'notebooks', 'cli-python', 'cli-native', 'docs', 'app'}


def source_edges(document):
    jobs = document['jobs']
    # The shared value is recognized by its dataflow (needs.<job>.outputs.<key>),
    # not by requiring one new job, environment variable, or output spelling.
    links = {}
    for name, job in jobs.items():
        text = '\n'.join(step.get('run', '') for step in job.get('steps', []))
        builds = name in CONSUMERS or bool(
            re.search(r'(?:build-crysta|core-build|app-build|crysta-consumer|git.*crysta)', text)
        )
        if not builds:
            continue
        edges = set(re.findall(r'needs\.([\w-]+)\.outputs\.([\w-]+)', yaml.safe_dump(job)))
        source = {
            (owner, key)
            for owner, key in edges
            if owner in jobs
            and key in jobs[owner].get('outputs', {})
            and 'crysta' in yaml.safe_dump(jobs[owner]).lower()
        }
        assert source, f' unit 8: CI dependency consumer {name} needs the shared crysta resolution'
        needs = job.get('needs', [])
        needs = [needs] if isinstance(needs, str) else needs
        assert all(owner in needs for owner, _ in source), (
            f' unit 8: consumer {name} must wait for its source-resolution producer'
        )
        links[name] = source
    assert links.keys() >= CONSUMERS, (
        ' unit 8: retain every existing CI consumer in the source sweep'
    )
    common = set.intersection(*links.values())
    assert len(common) == 1, (
        ' unit 8: all consumers must receive one per-run crysta source identity'
    )
    return links


def test_every_ci_consumer_uses_one_shared_crysta_resolution():
    document = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    source_edges(document)


def crysta_token_permissions(document):
    """Inspect every App token minted for crysta, including future jobs."""
    found = []
    for name, job in document['jobs'].items():
        for step in job.get('steps', []):
            if not str(step.get('uses', '')).startswith('actions/create-github-app-token@'):
                continue
            inputs = step.get('with', {})
            scope = inputs.get('repositories')
            assert isinstance(scope, (str, list)) and scope, (
                f' unit 8: App token step {name} must name its repository scope'
            )
            repositories = scope if isinstance(scope, list) else scope.replace(',', ' ').split()
            assert all(isinstance(repo, str) and '${{' not in repo for repo in repositories), (
                f' unit 8: App token step {name} has an unprovable repository scope'
            )
            if 'crysta' not in repositories:
                continue
            requested = {
                key: value for key, value in inputs.items() if key.startswith('permission-')
            }
            assert requested == {'permission-contents': 'read', 'permission-actions': 'read'}, (
                f' unit 8: crysta token step {name}/{step.get("name", "unnamed")} '
                'may request only contents:read and actions:read for the pinned PR artifact'
            )
            found.append((name, step))
    assert found, ' unit 8: CI must mint a contents:read token for crysta'
    return found


def test_crysta_app_tokens_request_only_contents_read():
    # Before: the source step requested pull-requests:read for a PR-list lookup.
    # After : contents:read for refs, actions:read for the tested run artifact.
    document = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    crysta_token_permissions(document)


@pytest.mark.parametrize(
    'extra',
    [
        {'permission-pull-requests': 'read'},
        {'permission-actions': 'write'},
        {'permission-contents': 'write'},
        {'permission-contents': None},
    ],
)
def test_crysta_token_permission_counterfactuals(extra):
    step = {
        'name': 'Select crysta',
        'uses': 'actions/create-github-app-token@v2',
        'with': {
            'repositories': 'crysta',
            'permission-contents': 'read',
            'permission-actions': 'read',
            **extra,
        },
    }
    document = {'jobs': {'future-source': {'steps': [step]}}}
    with pytest.raises(AssertionError, match='may request only contents:read'):
        crysta_token_permissions(document)


def test_source_sweep_catches_a_new_consumer_bypassing_resolution():
    # Independent positive control plus a future-reader escape: the sweep must
    # discover a newly added fetching job, not only today's named consumers.
    producer = {
        'outputs': {'sha': '${{ steps.resolve.outputs.sha }}'},
        'steps': [{'run': 'resolve-crysta-source'}],
    }
    consumer = {
        'needs': ['source'],
        'env': {'CRYSTA_CI_SHA': '${{ needs.source.outputs.sha }}'},
        'steps': [{'run': 'pixi run core-build'}],
    }
    document = {
        'jobs': {'source': producer, **{name: copy.deepcopy(consumer) for name in CONSUMERS}}
    }
    source_edges(document)
    document['jobs']['future-consumer'] = {
        'steps': [{'run': 'git clone https://github.com/enhantica/c' + 'rysta'}]
    }
    with pytest.raises(AssertionError, match='future-consumer'):
        source_edges(document)
