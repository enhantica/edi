"""Owner 46d227799: intermediate edi builds the branch artifact without a repin.

Real Git prescribes branch and stale pin. Addressed GitHub records prescribe the
producer artifact and tested bytes; none of these records is live CI evidence.
"""

import contextlib
import importlib
import io
import os
import shutil
import subprocess
from unittest.mock import patch

import pytest

from tests.integration.py.test_c34_t28_pr_artifact import acquisition
from tests.system.py.test_e09_t75_pin_currency import currency_world


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
@pytest.mark.parametrize('availability', ['available', 'missing', 'expired'])
def test_intermediate_stale_pin_builds_the_current_branch_artifact(  # noqa: PLR0914, PLR0915
    tmp_path, platform, event, availability
):
    history, stale = currency_world(tmp_path / 'history', 'paired-stale')
    head = history._git('rev-parse', 'paired-topic').strip()
    assert stale != head, ' pin currency control must contain genuinely different inputs'
    base = tmp_path / 'control'
    base.mkdir()
    code, output, _, _ = acquisition(base, platform=platform)
    assert code == 0, (
        ' intermediate artifact fixture must first admit its qualified control: ' + output
    )
    producer = importlib.import_module('tests.integration.py.test_c34_t28_pr_artifact')
    consumer = importlib.import_module('tests.integration.py.test_e09_t75_sdk_consumer')
    candidate = tmp_path / 'candidate'
    candidate.mkdir()
    with (
        patch.object(producer, 'SHA', head),
        patch.object(consumer, 'SHA', head),
        patch.object(consumer, 'TREE', history._git('rev-parse', head + '^{tree}').strip()),
    ):
        context = acquisition(candidate, platform=platform, prepare_only=True)
    root, api = context['root'], context['api']
    old = tmp_path / 'old'
    old.mkdir()
    with (
        patch.object(producer, 'SHA', stale),
        patch.object(consumer, 'SHA', stale),
        patch.object(consumer, 'TREE', history._git('rev-parse', stale + '^{tree}').strip()),
    ):
        previous = acquisition(old, platform=platform, prepare_only=True)
    # A usable cache of the DECLARED old pin is an ordinary intermediate input.
    # Its archive digest and all binary qualifications are checked, not invented.
    cached = root / 'build/crysta-sdk' / f'{stale}-{platform}'
    shutil.copytree(old / 'sdk', cached)
    (cached / '.sdk-sha256').write_text(previous['digest'] + '\n')
    pin = root / 'pixi.toml'
    pin.write_text(
        pin.read_text().replace(head, stale).replace(context['digest'], previous['digest'])
    )
    if availability == 'missing':
        api.artifacts[75090] = []
    elif availability == 'expired':
        for artifact in api.artifacts[75090]:
            artifact['expired'] = True
    shutil.copytree(history.edi / '.git', root / '.git')
    subprocess.run(
        [history.git, '-C', str(root), 'add', 'pixi.toml'],
        check=True,
        capture_output=True,
        timeout=2,
    )
    subprocess.run(
        [
            history.git,
            '-C',
            str(root),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-qm',
            'Commit the intermediate stale pin',
        ],
        check=True,
        capture_output=True,
        timeout=2,
    )
    # Only transport is substituted: Git reads the real independently planted history.
    git = candidate / 'bin/git'
    git.unlink()
    git.symlink_to(history.git)
    env = {
        **context['env'],
        'GIT_CONFIG_GLOBAL': history.env['GIT_CONFIG_GLOBAL'],
        'GIT_CONFIG_NOSYSTEM': '1',
        'GITHUB_EVENT_NAME': event,
        'GITHUB_HEAD_REF': 'paired-topic' if event == 'pull_request' else '',
        'GITHUB_REF_NAME': 'paired-topic',
        'GITHUB_TOKEN': 'fixture-token',
        'CRYSTA_SOURCE_SHA': head,
    }
    env.pop('CRYSTA_SDK_DIR', None)
    before = pin.read_bytes()
    output = io.StringIO()
    with (
        patch.dict(os.environ, env, clear=True),
        patch.object(context['module'], 'curl', api),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        old_manifest = context['module'].check(cached, platform)
        assert old_manifest['source_sha'] == stale, (
            ' old-pin cache must pass the real SDK qualification before attempting fallback'
        )
        code = context['module'].main(['fetch', '--platform', platform])
    assert not api.refusals, (
        ' F5 intermediate acquisition cannot swallow a refused resource request'
    )
    if availability != 'available':
        assert code != 0, (
            ' unavailable branch artifacts cannot borrow an otherwise valid old-pin cache'
        )
        assert f'crysta-sdk-{platform}' in output.getvalue(), (
            ' an unavailable branch artifact must be refused by its own name'
        )
        assert pin.read_bytes() == before, (
            ' an unavailable branch artifact cannot rewrite the committed pin'
        )
        return
    assert code == 0, (
        ' intermediate rows must consume the current PR artifact despite a stale pin: '
        + output.getvalue()
    )
    assert 'crysta: using SDK build-' + head in output.getvalue(), (
        ' intermediate provenance must name the branch head rather than the stale pin'
    )
    installed = root / 'build/crysta-sdk' / f'{head}-{platform}'
    assert (
        installed / 'lib/libcrysta_core.a'
    ).read_bytes() == b'independent static library bytes\x00\x17', (
        ' intermediate native input must contain the addressed producer tested library'
    )
    assert any('/actions/artifacts/' in url and url.endswith('/zip') for url in api.calls), (
        ' intermediate build must traverse the addressed branch artifact acquisition'
    )
    assert not api.releases, ' intermediate rows acquire artifacts without publishing a release'
    assert pin.read_bytes() == before, ' intermediate acquisition must preserve the committed pin'
