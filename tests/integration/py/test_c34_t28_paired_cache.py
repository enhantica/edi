"""F26: an ordinary selected-head warm cache cannot bypass fresh PR proof."""

import copy
import hashlib
import io
import json
import tarfile
import zipfile

import pytest

from tests.fixtures.c34_t28_paired_sdk import fetch, paired_sdk

NEW_LIBRARY = b'independently supplied replacement library\x00\x2b'


def supersede(context):
    api = context['api']
    artifact = copy.deepcopy(api.artifacts[75090][0])
    artifact.update(id=artifact['id'] + 100, created_at='2026-10-02T13:00:00Z')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(context['blob'])) as old:
        for member in old.getmembers():
            if member.isfile():
                files[member.name] = old.extractfile(member).read()
    files['lib/libcrysta_core.a'] = NEW_LIBRARY
    manifest = json.loads(files['share/crysta-sdk/manifest.json'])
    manifest['tested']['run_attempt'] = 3
    manifest['tested']['sha256']['lib/libcrysta_core.a'] = hashlib.sha256(NEW_LIBRARY).hexdigest()
    files['share/crysta-sdk/manifest.json'] = json.dumps(manifest).encode()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w:gz') as packed:
        for name, payload in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            member.mode = 0o755 if name == 'bin/crysta' else 0o644
            packed.addfile(member, io.BytesIO(payload))
    blob = raw.getvalue()
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, 'w') as packed:
        packed.writestr(context['name'], blob)
        packed.writestr(
            context['name'] + '.sha256', hashlib.sha256(blob).hexdigest() + '  ' + context['name']
        )
    api.artifacts[75090].append(artifact)
    api.archives[f'/actions/artifacts/{artifact["id"]}/zip'] = zipped.getvalue()
    return artifact['id'], hashlib.sha256(blob).hexdigest()


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
@pytest.mark.parametrize(
    'change', ['unchanged', 'failed-rerun', 'failed-later-run', 'missing', 'expired', 'superseded']
)
def test_selected_head_warm_cache_reproves_the_addressed_producer(
    tmp_path, platform, event, change
):
    context = paired_sdk(tmp_path, platform, event)
    root, api = context['root'], context['api']
    before = (root / 'pixi.toml').read_bytes()
    code, output = fetch(context)
    assert code == 0, ' F26 a cold qualified paired control must admit: ' + output
    cache = root / 'build/crysta-sdk' / f'{context["head"]}-{platform}'
    assert (cache / '.sdk-sha256').read_text().strip() == context['digest'], (
        ' F26 the escape starts with the normally fetched selected-head cache'
    )
    assert (
        cache / 'lib/libcrysta_core.a'
    ).read_bytes() == b'independent static library bytes\x00\x17', (
        ' F26 the warm cache starts with exactly the independently qualified old bytes'
    )
    if change in {'failed-rerun', 'superseded'}:
        api.runs[0]['run_attempt'] = 3
        job = copy.deepcopy(api.jobs[75090][-1])
        job.update(
            id=7509003,
            run_attempt=3,
            conclusion='success' if change == 'superseded' else 'failure',
        )
        api.jobs[75090].append(job)
    elif change == 'failed-later-run':
        run = copy.deepcopy(api.runs[0])
        run.update(id=75091, run_attempt=1, status='completed', conclusion='failure')
        api.runs.append(run)
        api.selectors[75091] = (context['head'], 'pull_request')
        api.jobs[75091] = [
            {
                **api.jobs[75090][-1],
                'id': 7509101,
                'run_id': 75091,
                'run_attempt': 1,
                'conclusion': 'failure',
            }
        ]
        api.artifacts[75091] = []
    elif change == 'missing':
        api.artifacts[75090] = []
    elif change == 'expired':
        api.artifacts[75090][0]['expired'] = True
    replacement, digest = supersede(context) if change == 'superseded' else (None, None)
    api.calls.clear()
    code, output = fetch(context)
    assert (root / 'pixi.toml').read_bytes() == before, (
        ' F26 a cache read or refusal must never rewrite the declared pin'
    )
    assert not api.releases, ' F26 paired cache qualification publishes nothing'
    if change not in {'unchanged', 'superseded'}:
        assert code != 0, (
            ' F26 a warm selected-head cache cannot borrow obsolete producer proof: ' + output
        )
        assert f'crysta-sdk-{platform}' in output or (
            change.startswith('failed-')
            and ('checks (' in output or 'pull-request runs' in output)
        ), ' F26 failed or expired selected artifacts refuse by their own name'
        return
    assert code == 0, ' F26 a current qualified paired cache must admit: ' + output
    assert any('/jobs?' in url for url in api.calls), (
        ' F26 a warm cache still observes the addressed producing execution'
    )
    assert any('/artifacts?' in url for url in api.calls), (
        ' F26 a warm cache still observes the addressed unexpired artifact'
    )
    if change == 'superseded':
        assert any(f'/actions/artifacts/{replacement}/zip' in url for url in api.calls), (
            ' F26 a successful re-run consumes its selected replacement artifact'
        )
        assert (cache / 'lib/libcrysta_core.a').read_bytes() == NEW_LIBRARY, (
            ' F26 a superseding artifact replaces the old selected-head bytes'
        )
        assert (cache / '.sdk-sha256').read_text().strip() == digest, (
            ' F26 the replacement cache marker binds the newly selected archive bytes'
        )
