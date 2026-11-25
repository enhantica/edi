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
    source_action = './.github/actions/crysta-source'
    calls = [
        step
        for _, child in expanded
        for step in child.get('steps', [])
        if step.get('uses') == source_action
    ]
    assert len(calls) == 1 and calls[0]['with'] == {
        'sha': '${{ needs.resolve.outputs.sha }}',
        'app-id': '${{ vars.ENHANTICA_APP_ID }}',
        'private-key': '${{ secrets.ENHANTICA_APP_KEY }}',
    }, 'The shared SDK delegates the exact pinned read to the local source action'
    action = yaml.safe_load((ROOT / source_action / 'action.yml').read_text())
    caller_steps = [step for _, child in expanded for step in child.get('steps', [])]
    tokens = [
        step
        for step in [*caller_steps, *action['runs']['steps']]
        if step.get('uses', '').startswith('actions/create-github-app-token@')
    ]
    assert len(tokens) == 1, 'One narrowly scoped token supplies the private source read'
    assert tokens[0]['with'] == {
        'app-id': '${{ inputs.app-id }}',
        'private-key': '${{ inputs.private-key }}',
        'owner': 'enhantica',
        'repositories': 'crysta',
        'permission-contents': 'read',
    }, 'The composite token can only read contents of the intended source repository'


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
