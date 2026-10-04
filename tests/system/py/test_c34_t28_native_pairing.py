"""F28: execute both native pack and every restore handoff with a stale pin.

The native payload is independently planted importable/executable protocol data,
not a live producer build. The real native tool and artifact-mode core dependency
run unchanged; run/head/platform/workspace and byte refusal remain required.
"""

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest
from ci_runner_contract import platform_job

from tests.fixtures.c34_t28_paired_sdk import commit, fetch, install_transport, paired_sdk
from tests.integration.py.test_e09_t75_native_workflow import (
    ROSTER,
    consumer_boundary,
    jobs,
)


def native_world(tmp_path, platform, event, *, matching_pin=False):
    context = paired_sdk(tmp_path, platform, event)
    root = context['root']
    if matching_pin:
        pin = root / 'pixi.toml'
        pin.write_text(
            pin
            .read_text()
            .replace(context['stale'], context['head'])
            .replace(context['declared_digest'], context['digest'])
        )
    (root / '.gitignore').write_text('build/\n__pycache__/\n')
    (root / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.28)\n')
    commit(
        root,
        context['history'].git,
        'Prepare independent native inputs',
        'tools',
        'pixi.toml',
        'pixi.lock',
        '.gitignore',
        'CMakeLists.txt',
    )
    head = subprocess.check_output(
        [context['history'].git, '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    tree = subprocess.check_output(
        [context['history'].git, '-C', str(root), 'rev-parse', 'HEAD^{tree}'], text=True
    ).strip()
    code, output = fetch(context)
    assert code == 0, (
        ' F28 native handoff first requires the real branch SDK acquisition: ' + output
    )
    payloads = {
        'build/ci/.crysta-linked-sha': (context['head'] + '\n').encode(),
        'build/ci/python/edi/__init__.py': (
            'from . import _edi\n__build_commit__ = ' + repr(head) + '\n'
        ).encode(),
        'build/ci/python/edi/_edi.py': b'WITNESS = "independent branch native handoff"\n',
        'build/ci/cli/easydiffraction': b'#!/bin/sh\necho easydiffraction-branch-witness\n',
        'build/ci/core/edi_tests': b'#!/bin/sh\necho branch-native-test-witness\n',
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o755 if relative.endswith(('edi_tests', 'easydiffraction')) else 0o644)
    # Prefix and corpus contain the SDK actually acquired, never the declared pin.
    sdk = root / 'build/crysta-sdk' / f'{context["head"]}-{platform}'
    prefix = root / 'build/crysta-prefix'
    prefix.mkdir()
    for entry in sdk.iterdir():
        if not entry.name.startswith('.'):
            (prefix / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    (prefix / '.crysta-sha').write_text(context['head'] + '\n')
    source = root / 'build/crysta-src'
    subprocess.run(
        [context['history'].git, 'clone', '-q', str(context['history'].sibling), str(source)],
        check=True,
        capture_output=True,
        timeout=2,
    )
    subprocess.run(
        [context['history'].git, '-C', str(source), 'checkout', '-q', context['head']],
        check=True,
        capture_output=True,
        timeout=2,
    )
    env = {
        **context['env'],
        'GITHUB_WORKSPACE': str(root),
        'GITHUB_SHA': head,
        'GITHUB_RUN_ID': '75134',
        'GITHUB_RUN_ATTEMPT': '2',
        'GITHUB_JOB': 'native',
        'RUNNER_TEMP': str(tmp_path),
        'PYTHONPATH': str(root / 'build/ci/python'),
        'EDI_NATIVE_DIR': str(tmp_path / 'edi-native'),
        'EDI_CORE_BUILD_LOCK_WAIT_S': '0',
    }
    # A restore dependency must compile nothing; the original refusing compiler
    # transports remain in place. Only the warm artifact GETs are served below.
    install_transport(context, env)
    env['GITHUB_ENV'] = str(tmp_path / 'job-env')
    return context, env, head, tree, payloads


def native(context, env, *args):
    return subprocess.run(
        [sys.executable, str(context['root'] / 'tools/ci/edi_native.py'), *args],
        cwd=context['root'],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=4,
    )


def independent_artifact(context, env, head, tree, payloads):
    folder = Path(env['EDI_NATIVE_DIR'])
    folder.mkdir()
    asset = folder / 'edi-native.tar'
    with tarfile.open(asset, 'w') as archive:
        for relative, payload in payloads.items():
            info = tarfile.TarInfo(relative)
            info.size = len(payload)
            info.mode = 0o755 if relative.endswith(('edi_tests', 'easydiffraction')) else 0o644
            archive.addfile(info, io.BytesIO(payload))
    pin = tomllib.loads((context['root'] / 'pixi.toml').read_text())['target'][
        context['platform']
    ]['activation']['env']
    record = {
        'source_sha': head,
        'source_tree': tree,
        'run_id': env['GITHUB_RUN_ID'],
        'run_attempt': '1',
        'job': 'native',
        'platform': context['platform'],
        'workspace': str(context['root']),
        'crysta_linked_sha': context['head'],
        'CRYSTA_SDK_TAG': pin['CRYSTA_SDK_TAG'],
        'CRYSTA_SDK_SHA256': pin['CRYSTA_SDK_SHA256'],
        'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
        'files': {
            name: hashlib.sha256(payload).hexdigest()
            + (' 755' if name.endswith(('edi_tests', 'easydiffraction')) else ' 644')
            for name, payload in payloads.items()
        },
    }
    (folder / 'edi-native.json').write_text(json.dumps(record))
    return folder, record


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
@pytest.mark.parametrize('mode', ['matching', 'stale'])
def test_intermediate_native_producer_packs_the_branch_sdk_without_repinning(
    tmp_path, platform, event, mode
):
    context, env, head, tree, _ = native_world(
        tmp_path, platform, event, matching_pin=mode == 'matching'
    )
    before = (context['root'] / 'pixi.toml').read_bytes()
    folder = env['EDI_NATIVE_DIR']
    result = native(context, env, 'pack', '--out', folder)
    assert result.returncode == 0, (
        ' F28 the real native pack must admit the branch build: ' + result.stdout + result.stderr
    )
    record = json.loads((Path(folder) / 'edi-native.json').read_text())
    assert record['crysta_linked_sha'] == context['head'], (
        ' F28 native packing records the branch SDK actually linked'
    )
    assert record['CRYSTA_SDK_TAG'] == 'build-' + (
        context['head'] if mode == 'matching' else context['stale']
    ), ' F28 native packing retains the distinct declared-pin obligation'
    assert record['source_sha'] == head, ' F28 the pack binds this edi source commit'
    assert record['source_tree'] == tree, ' F28 the pack binds this edi source tree'
    assert (context['root'] / 'pixi.toml').read_bytes() == before, (
        ' F28 native pack cannot silently repin an intermediate build'
    )
    assert not json.loads(Path(env['C34_PAIRED_API_RECORDS']).read_text(encoding='utf-8'))[
        'refusals'
    ], ' F5 native pack cannot swallow an unsupported transport request'


@pytest.mark.parametrize(('consumer', 'platform'), ROSTER)
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
@pytest.mark.usefixtures('private_native_workflow')
def test_every_native_consumer_restores_the_branch_build_and_rechecks_bytes(
    tmp_path, consumer, platform, event
):
    context, env, head, tree, payloads = native_world(tmp_path, platform, event)
    folder, _ = independent_artifact(context, env, head, tree, payloads)
    # Direct restore proves this route even when pack itself refuses on the old head.
    shutil.rmtree(context['root'] / 'build/ci')
    job = {**platform_job(jobs(), consumer, platform), '_consumer': consumer}
    _, step, _ = consumer_boundary(job, platform)
    assert step['run'].strip() == 'pixi run core-build', (
        ' F28 every actual consumer reaches the same native dependency'
    )
    env['EDI_NATIVE_ARTIFACT'] = '1'
    env['GITHUB_JOB'] = consumer
    for attempt in range(2):
        if attempt:
            (context['root'] / 'build/ci/cli/easydiffraction').write_text(
                'ordinary overwritten native cache bytes\n'
            )
        dependency = subprocess.run(
            ['bash', 'tools/ci/core-build.sh'],
            cwd=context['root'],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=4,
        )
        assert not json.loads(Path(env['C34_PAIRED_API_RECORDS']).read_text(encoding='utf-8'))[
            'refusals'
        ], ' F5 native dependency cannot swallow an unsupported transport request'
        assert dependency.returncode == 0, (
            ' F28 the real native dependency admits and revalidates its branch artifact: '
            + dependency.stdout
            + dependency.stderr
        )
        for relative, payload in payloads.items():
            assert (context['root'] / relative).read_bytes() == payload, (
                ' F28 restored native bytes equal independently packaged inputs'
            )
    assert folder.is_dir(), ' F28 consumer restoration retains its addressed artifact'
    assert not (context['home'] / 'commands').exists(), (
        ' F28 native consumers never compile a fallback'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
def test_native_tool_independently_restores_the_branch_artifact(tmp_path, platform, event):
    context, env, head, tree, payloads = native_world(tmp_path, platform, event)
    independent_artifact(context, env, head, tree, payloads)
    shutil.rmtree(context['root'] / 'build/ci')
    result = native(context, env, 'restore')
    assert not json.loads(Path(env['C34_PAIRED_API_RECORDS']).read_text(encoding='utf-8'))[
        'refusals'
    ], ' F5 direct native restoration cannot swallow a transport refusal'
    assert result.returncode == 0, (
        ' F28 the real restore admits the separately planted branch artifact: '
        + result.stdout
        + result.stderr
    )
    for relative, payload in payloads.items():
        assert (context['root'] / relative).read_bytes() == payload, (
            ' F28 direct restoration preserves independent payload bytes'
        )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize(
    'damage',
    [
        'run_id',
        'source_sha',
        'source_tree',
        'platform',
        'workspace',
        'sha256',
        'crysta_linked_sha',
        'CRYSTA_SDK_TAG',
        'CRYSTA_SDK_SHA256',
        'tar-bytes',
    ],
)
def test_branch_native_handoff_retains_every_independent_binding(tmp_path, platform, damage):
    good, control_env, control_head, control_tree, control_payloads = native_world(
        tmp_path / 'matching', platform, 'pull_request', matching_pin=True
    )
    independent_artifact(good, control_env, control_head, control_tree, control_payloads)
    admitted = native(good, control_env, 'restore')
    assert admitted.returncode == 0, (
        ' F28 unchanged matching-pin restoration must first admit: '
        + admitted.stdout
        + admitted.stderr
    )
    context, env, head, tree, payloads = native_world(
        tmp_path / 'branch', platform, 'pull_request'
    )
    folder, record = independent_artifact(context, env, head, tree, payloads)
    if damage == 'tar-bytes':
        with (folder / 'edi-native.tar').open('ab') as archive:
            archive.write(b'ordinary changed artifact bytes')
    else:
        record[damage] = 'incorrect independently supplied coordinate'
        (folder / 'edi-native.json').write_text(json.dumps(record))
    result = native(context, env, 'restore')
    assert result.returncode != 0, (
        ' F28 stale-pin branch mode keeps every run/head/platform/workspace/byte refusal'
    )
    assert not json.loads(Path(env['C34_PAIRED_API_RECORDS']).read_text(encoding='utf-8'))[
        'refusals'
    ], ' F5 failed native restore cannot swallow an unsupported transport request'
