"""Real publication, credential and workflow counterfactuals retain PR core cadence."""

import shutil

import pytest
import yaml

from tests.integration.py.test_e04_t12_public_content import (
    CONTRACT,
    ROOT,
    check,
    commit,
    event,
    observe_content_workflows,
    specimen,
    synthetic_credential,
)


def test_current_public_workflows_keep_the_content_observer(tmp_path):
    output, _base = specimen(tmp_path)
    shutil.copytree(ROOT / '.github/workflows', output / '.github/workflows')
    commit(output, 'Install current public workflows')
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
