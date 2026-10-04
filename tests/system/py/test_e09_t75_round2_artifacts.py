"""Review-14 F03/F04 accident paths: absent binary/hash pairs and dropped execute bits.

An incomplete diagnostic SDK can omit both coordinates; copying a native cache
can preserve every byte while removing its executable permissions.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile

import pytest

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal
from tests.integration.py.test_e09_t75_sdk_consumer import consumer
from tests.system.py.test_e09_t75_native_execution import restore


def run_sdk(env, repo, sdk, route):
    if route.startswith('install-'):
        argv = ['bash', 'tools/ci/build-crysta.sh']
    else:
        argv = [sys.executable, 'tools/ci/crysta_sdk.py', route, '--platform', 'osx-arm64']
        if route == 'check':
            argv += ['--sdk', str(sdk)]
    result = subprocess.run(
        argv, cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=3
    )
    assert_no_swallowed_refusal(repo.parent, result.returncode == 0)
    return result


def repack_download(bad_home, repo, sdk):
    state_path = bad_home / 'download.json'
    state = json.loads(state_path.read_text())
    asset = bad_home / 'published-sdk.tar.gz'
    with tarfile.open(asset, 'w:gz') as archive:
        for file in sorted(sdk.rglob('*')):
            if file.is_file():
                archive.add(file, arcname=str(file.relative_to(sdk)))
    old = state['metadata']['assets'][0]['digest'].removeprefix('sha256:')
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    state['metadata']['assets'][0]['digest'] = 'sha256:' + digest
    state_path.write_text(json.dumps(state))
    pin = repo / 'pixi.toml'
    pin.write_text(pin.read_text().replace(old, digest))


@pytest.mark.parametrize('route', ['check', 'fetch', 'install-check', 'install-fetch'])
@pytest.mark.parametrize('member', ['lib/libcrysta_core.a', 'bin/crysta'])
@pytest.mark.parametrize('record', ['absent', 'null', 'malformed'])
def test_required_sdk_bytes_and_recorded_digests_cannot_qualify_by_joint_absence(
    tmp_path, route, member, record
):
    download = route.endswith('fetch')
    good_home = tmp_path / 'control'
    good_home.mkdir()
    env, repo, sdk = consumer(good_home, download=download, prepare_only=True)
    good = run_sdk(env, repo, sdk, route)
    assert good.returncode == 0, (
        f' I23/I26 complete SDK must qualify through {route}: {good.stderr}'
    )
    bad_home = tmp_path / 'incomplete'
    bad_home.mkdir()
    env, repo, sdk = consumer(bad_home, download=download, prepare_only=True)
    (sdk / member).unlink()
    manifest_path = sdk / 'share/crysta-sdk/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    digests = manifest['tested']['sha256']
    if record == 'absent':
        del digests[member]
    else:
        digests[member] = None if record == 'null' else 'not-a-sha256'
    manifest_path.write_text(json.dumps(manifest))
    if download:
        repack_download(bad_home, repo, sdk)
    bad = run_sdk(env, repo, sdk, route)
    assert bad.returncode != 0, (
        f' I23/I26 {route} must refuse missing tested {member} with {record} digest'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('member', ['cli', 'tests'])
@pytest.mark.usefixtures('private_native_workflow')
def test_native_cache_restoration_reproves_runnable_permissions(tmp_path, platform, member):
    result = restore(tmp_path, 'core', platform, defect='mode-' + member)
    runs = result[0]
    assert runs[0].returncode == 0, (
        ' I34 the native permission challenge must first restore its qualified control'
    )
    assert len(runs) == 2, ' I34 execute-bit loss must reach actual repeated restore'
    if runs[-1].returncode:
        return
    target = (
        tmp_path
        / 'edi/build/ci'
        / ('cli/easydiffraction' if member == 'cli' else 'core/edi_tests')
    )
    assert os.access(target, os.X_OK), (
        ' I34 successful reuse must preserve the independently required executable mode'
    )
    result = subprocess.run([str(target)], capture_output=True, text=True, check=False, timeout=2)
    assert result.returncode == 0, (
        ' I34 successful reuse must leave the actual CLI/test-runner runnable'
    )
