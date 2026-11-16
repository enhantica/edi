"""Real publication, credential and workflow counterfactuals retain PR core cadence."""

import shutil
import subprocess
import sys

import pytest
import yaml

from tests.integration.py.test_e04_t12_public_content import (
    CONTRACT,
    ROOT,
    check,
    commit,
    event,
    git,
    observe_content_workflows,
    specimen,
    synthetic_credential,
)


def test_e04_t12_transformed_snapshot_keeps_the_content_workflow_observer(tmp_path):
    root, _base = specimen(tmp_path)
    prepared = root / 'tools/public-release/github/workflows'
    source = ROOT / 'tools/public-release/github/workflows'
    if not source.is_dir():
        source = ROOT / '.github/workflows'
    shutil.copytree(source, prepared)
    head = commit(root, 'Prepare public checks')
    output = tmp_path / 'published'
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/public-release/snapshot.py'),
            '--source',
            str(root),
            '--ref',
            head,
            '--output',
            str(output),
            '--skip-hidden',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )
    assert result.returncode == 0, (
        'the workflow observer control must use the actual snapshot transformation'
    )
    assert git(output, 'rev-list', '--count', 'HEAD') == '1', (
        'the published workflow control must have one fresh commit'
    )
    assert not (output / 'tools/public-release/github').exists(), (
        'the observer must run after the preparation directory has been removed'
    )
    observe_content_workflows(output)

    folder = output / '.github/workflows'
    for workflow in folder.glob('*.yml'):
        original = workflow.read_text()
        document = yaml.safe_load(original)
        jobs = [
            job
            for job in document['jobs'].values()
            if any(CONTRACT['script'] in str(step.get('run', '')) for step in job.get('steps', []))
        ]
        if not jobs:
            continue
        for trigger in ('push', 'pull_request'):
            damaged = yaml.safe_load(original)
            damaged.get('on', damaged.get(True)).pop(trigger)
            workflow.write_text(yaml.safe_dump(damaged))
            with pytest.raises(AssertionError, match='pushes and PR'):
                observe_content_workflows(output)
            workflow.write_text(original)
        for argument, diagnostic in (
            ('--title', 'PR text'),
            ('--body-file', 'PR text'),
            ('--base', 'actual PR head'),
            ('pull_request.head.sha', 'actual PR head'),
            ('fetch-depth', 'actual PR head'),
        ):
            workflow.write_text(original.replace(argument, 'missing-input'))
            with pytest.raises(AssertionError, match=diagnostic):
                observe_content_workflows(output)
            workflow.write_text(original)


@pytest.mark.parametrize(
    'kind', ['aws-id', 'github', 'github-fine', 'slack', 'google', 'private-key', 'aws-secret']
)
@pytest.mark.parametrize('channel', ['commit-root', 'commit-push', 'commit-pr', 'title', 'body'])
def test_e04_t12_credentials_are_refused_and_redacted_in_metadata(tmp_path, kind, channel):
    root, base = specimen(tmp_path)
    payload = event()
    start = None if channel == 'commit-root' else base
    assert check(root, start, base, payload, tmp_path).returncode == 0, (
        'safe metadata must pass before independently constructed credentials are introduced'
    )
    token = synthetic_credential(kind)
    if channel.startswith('commit'):
        head = commit(root, token)
        payload = event() if channel == 'commit-pr' else {}
    else:
        head = base
        payload['pull_request'][channel] = token
    result = check(root, start, head, payload, tmp_path)
    assert result.returncode != 0, (
        'every metadata channel must refuse recognised credential shapes'
    )
    output = result.stdout + result.stderr
    assert token not in output, (
        'credential refusals must redact the credential rather than repeat it'
    )
    assert any(word in output.lower() for word in ('credential', 'secret', 'token', 'key')), (
        'metadata credentials need an explicit policy diagnostic'
    )
