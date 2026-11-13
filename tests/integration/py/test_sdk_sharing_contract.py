"""Local producer sequencing and immutable run transport, independent of remote builds."""

from __future__ import annotations

import copy
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active

ROOT = Path(__file__).resolve().parents[3]
PRODUCER = '.github/workflows/crysta-sdk.yml'
INPUTS = (PRODUCER, 'tools/ci/crysta_source_receipt.py', '.github/actions/setup-pixi/action.yml')


def document(path):
    return yaml.safe_load((ROOT / path).read_text())


def expanded_identity(template, *, platform='linux-64', pin='a7' * 20, recipe='c9' * 32):
    for name, value in {
        'matrix.platform': platform,
        'needs.resolve.outputs.sha': pin,
        'needs.resolve.outputs.recipe': recipe,
    }.items():
        template = template.replace('${{ ' + name + ' }}', value)
    assert '${{' not in template, 'Producer identity cannot depend on another mutable context'
    return template


def current_run_download(action):
    steps = action['runs']['steps']
    downloads = [step for step in steps if step.get('uses') == 'actions/download-artifact@v4']
    assert len(downloads) == 1, 'Each consumer takes one exact platform artifact'
    assert not any('cache' in step.get('uses', '') for step in steps), (
        'A consumer uses its producer artifact rather than cache availability'
    )
    selected = downloads[0]['with']
    assert selected.get('name') == 'crysta-sdk-${{ inputs.platform }}'
    assert selected.get('path') == 'crysta-sdk-archives'
    assert selected.get('run-id') in {None, '${{ github.run_id }}'}, (
        'Ordinary consumers cannot take an SDK from a foreign run'
    )
    assert selected.get('repository') in {None, '${{ github.repository }}'}
    assert not selected.get('pattern') and not selected.get('merge-multiple')
    assert any(
        'CRYSTA_SDK_ARCHIVES=$GITHUB_WORKSPACE/crysta-sdk-archives' in step.get('run', '')
        for step in steps
    ), 'The actual reader receives the downloaded archive directory'


def test_sdk_producer_serializes_platform_pin_and_recipe_without_cancelling_waiters():
    workflow = document(PRODUCER)
    triggers = workflow.get('on', workflow.get(True))
    assert {'workflow_dispatch', 'workflow_call'} <= set(triggers)
    build = workflow['jobs']['build']
    assert build['needs'] == 'resolve'
    assert build['concurrency']['cancel-in-progress'] is False
    assert build['concurrency']['queue'] == 'max'
    group = build['concurrency']['group']
    cache = next(step for step in build['steps'] if step.get('id') == 'cache')
    assert not cache['with'].get('restore-keys'), 'Another recipe cannot satisfy the exact cache'
    for identity in (group, cache['with']['key']):
        keys = [
            expanded_identity(identity),
            expanded_identity(identity, platform='osx-arm64'),
            expanded_identity(identity, pin='b8' * 20),
            expanded_identity(identity, recipe='d0' * 32),
        ]
        assert len(set(keys)) == 4, 'Each platform, source or recipe change invalidates identity'
        for field in (
            'matrix.platform',
            'needs.resolve.outputs.sha',
            'needs.resolve.outputs.recipe',
        ):
            changed = identity.replace('${{ ' + field + ' }}', 'constant')
            assert changed != identity, 'The identity challenge reaches its declared dimension'


def test_sdk_cold_and_warm_producers_publish_required_artifacts_only_after_success():
    build = document(PRODUCER)['jobs']['build']
    steps = build['steps']
    package = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    upload = next(step for step in steps if step.get('uses') == 'actions/upload-artifact@v4')
    assert steps.index(package) < steps.index(upload)
    assert upload['with']['name'] == 'crysta-sdk-${{ matrix.platform }}'
    assert upload['with']['path'] == 'crysta-sdk-archives'
    assert upload['with'].get('if-no-files-found') == 'error', (
        'A producer with missing archives must fail rather than report artifact delivery'
    )
    for hit, packed in [('false', True), ('true', False)]:
        outputs = {('cache', 'cache-hit'): hit}
        assert active(package, 'workflow_dispatch', outputs=outputs) is packed
        assert active(upload, 'workflow_dispatch', outputs=outputs), (
            'A warm producer still exports qualified bytes for its own consumers'
        )
        assert not active(
            upload, 'workflow_dispatch', outputs=outputs, states={'qualification': 'failure'}
        ), 'A failed qualification cannot publish an SDK artifact'


def test_sdk_producer_rejects_missing_empty_changed_and_misdirected_outputs(tmp_path):
    steps = document(PRODUCER)['jobs']['build']['steps']
    guard = next(
        step
        for step in steps
        if step.get('env', {}).get('PLATFORM') == '${{ matrix.platform }}'
        and 'crysta-sdk-archives' in step.get('run', '')
    )
    upload = next(step for step in steps if step.get('uses') == 'actions/upload-artifact@v4')
    assert steps.index(guard) < steps.index(upload)
    for hit in ('false', 'true'):
        assert active(guard, 'workflow_dispatch', outputs={('cache', 'cache-hit'): hit}), (
            'Every cold and warm artifact crosses the same complete-output boundary'
        )
    assert guard['env']['SHA'] == '${{ needs.resolve.outputs.sha }}'
    assert guard['env']['PLATFORM'] == '${{ matrix.platform }}'
    for platform in ('linux-64', 'osx-arm64'):
        pin = 'a7' * 20
        archive = f'crysta-sdk-{pin}-{platform}.tar.gz'
        checksum = archive + '.sha256'
        source = f'crysta-src-{pin}.tar.gz'
        authored = b'independent opaque archive transport, not a scientific SDK'
        files = {
            archive: authored,
            checksum: (hashlib.sha256(authored).hexdigest() + '  ' + archive + '\n').encode(),
            source: b'independent source transport',
        }
        mutations = [
            (None, None),
            *[(name, None) for name in files],
            *[(name, b'') for name in files],
            (archive, b'changed archive'),
            (checksum, b'0' * 64 + b'  ' + archive.encode() + b'\n'),
            (checksum, files[checksum] * 2),
            (checksum, files[checksum] + b'extra record\n'),
            (checksum, files[checksum].replace(archive.encode(), b'../external.tar.gz')),
            (
                checksum,
                (hashlib.sha256(authored).hexdigest() + '  other-archive.tar.gz\n').encode(),
            ),
        ]
        for index, (name, replacement) in enumerate(mutations):
            world = tmp_path / platform / str(index)
            destination = world / 'crysta-sdk-archives'
            destination.mkdir(parents=True)
            for member, data in files.items():
                if member != name or replacement is not None:
                    (destination / member).write_bytes(replacement if member == name else data)
            if name == checksum and b'other-archive' in (replacement or b''):
                (destination / 'other-archive.tar.gz').write_bytes(authored)
                (destination / archive).write_bytes(b'unverified replacement')
            result = subprocess.run(
                ['bash', '-e', '-c', guard['run']],
                cwd=world,
                env={**os.environ, 'SHA': pin, 'PLATFORM': platform},
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            assert (result.returncode == 0) == (name is None), (
                'The actual producer must reject missing, empty, corrupt or wrong-file '
                f'checksum transport: {platform} {name}'
            )


@pytest.mark.parametrize('changed', INPUTS)
def test_sdk_recipe_invalidates_every_local_producer_build_input(tmp_path, changed):
    steps = document(PRODUCER)['jobs']['resolve']['steps']
    recipe = next(step['run'] for step in steps if step.get('id') == 'recipe')
    for name in INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    output = tmp_path / 'output'

    def resolve():
        output.write_text('')
        result = subprocess.run(
            ['bash', '-e', '-c', recipe],
            cwd=tmp_path,
            env={**os.environ, 'GITHUB_OUTPUT': str(output)},
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert result.returncode == 0, 'The actual declared producer recipe must execute'
        fields = dict(line.split('=', 1) for line in output.read_text().splitlines())
        assert len(fields['sha']) == 64
        return fields['sha']

    before = resolve()
    path = tmp_path / changed
    path.write_bytes(path.read_bytes() + b'\n# independent recipe invalidation control\n')
    assert resolve() != before, 'Changed producer build inputs cannot reuse an older SDK recipe'


def test_sdk_consumers_bind_same_run_artifacts_and_refuse_foreign_transport():
    action = document('.github/actions/crysta-sdk/action.yml')
    current_run_download(action)
    for mutation in ('run-id', 'repository', 'name', 'cache'):
        changed = copy.deepcopy(action)
        download = next(
            step
            for step in changed['runs']['steps']
            if step.get('uses') == 'actions/download-artifact@v4'
        )
        if mutation == 'cache':
            download['uses'] = 'actions/cache/restore@v4'
        else:
            download['with'][mutation] = 'foreign'
        with pytest.raises(AssertionError):
            current_run_download(changed)


def test_release_sdk_download_uses_the_exact_qualified_installer_run():
    steps = document('.github/workflows/release-publish.yml')['jobs']['publish']['steps']
    promotion = next(step for step in steps if 'tools/release/promote.py' in step.get('run', ''))
    download = next(
        step
        for step in steps
        if step.get('uses') == 'actions/download-artifact@v4'
        and step.get('with', {}).get('pattern') == 'crysta-sdk-*'
    )
    assert steps.index(promotion) < steps.index(download)
    assert promotion['env']['INSTALLER_RUN'] == '${{ inputs.installer_run }}'
    assert download['with']['run-id'] == '${{ inputs.installer_run }}'
    assert download['with']['github-token'] == '${{ github.token }}'
    assert download['with']['merge-multiple'] is True
    assert download['with']['path'] == 'crysta-sdk-archives'
    assert not any('cache' in step.get('uses', '') for step in steps), (
        'Publication must not substitute an opportunistic cache for qualified run artifacts'
    )
