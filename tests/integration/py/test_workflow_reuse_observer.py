"""Reusable SDK jobs retain visible runner and credential boundaries."""

from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import expanded_jobs
from tests.integration.py.ci_runner_contract import self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]


def test_actual_shared_sdk_exposes_all_platform_runners_and_only_source_read_scope():
    job = {'uses': './.github/workflows/crysta-sdk.yml'}
    runners = self_hosted_runners(job)
    assert {tuple(row) for row in runners} == {
        ('github-hosted', 'Linux', 'X64'),
        ('github-hosted', 'macOS', 'ARM64'),
        ('github-hosted', 'Windows', 'X64'),
    }, 'Actual shared sdk exposes all platform runners and only source read scope.'
    expanded = expanded_jobs({'jobs': {'sdk': job}}, ROOT)
    tokens = [
        step
        for _, child in expanded
        for step in child.get('steps', [])
        if 'create-github-app-token' in step.get('uses', '')
    ]
    assert len(tokens) == 1, (
        'Actual shared sdk exposes all platform runners and only source read scope.'
    )
    assert {
        key: value for key, value in tokens[0]['with'].items() if key.startswith('permission-')
    } == {'permission-contents': 'read'}, (
        'Actual shared sdk exposes all platform runners and only source read scope.'
    )


@pytest.mark.parametrize('damage', ['remote', 'missing', 'cycle', 'malformed'])
def test_unproved_reusable_workflow_cannot_hide_jobs(tmp_path, damage):
    reference = './.github/workflows/child.yml'
    child = tmp_path / reference
    child.parent.mkdir(parents=True)
    child.write_text(yaml.safe_dump({'jobs': {'runner': {'runs-on': 'ubuntu-24.04'}}}))
    if damage == 'remote':
        reference = 'outside/other/.github/workflows/child.yml@main'
    elif damage == 'missing':
        child.unlink()
    elif damage == 'cycle':
        child.write_text(yaml.safe_dump({'jobs': {'again': {'uses': reference}}}))
    else:
        child.write_text('jobs: []\n')
    with pytest.raises(AssertionError):
        expanded_jobs({'jobs': {'sdk': {'uses': reference}}}, tmp_path)
