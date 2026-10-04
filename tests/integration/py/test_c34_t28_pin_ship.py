"""F8: artifact pin writing, committed consumption and release-only ship check."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from unittest.mock import patch

import pytest
import yaml

from tests.integration.py.test_c34_t28_pr_artifact import SHA, acquisition


def paired(tmp_path):
    contexts = {}
    for platform in ('linux-64', 'osx-arm64'):
        folder = tmp_path / platform
        folder.mkdir(parents=True)
        contexts[platform] = acquisition(folder, platform=platform, prepare_only=True)
    context = contexts['linux-64']
    api = context['api']
    other = contexts['osx-arm64']
    api.jobs[75090] += other['api'].jobs[75090]
    api.artifacts[75090] += other['api'].artifacts[75090]
    api.archives.update(other['api'].archives)
    root = context['root']
    lock = yaml.safe_load((root / 'pixi.lock').read_text())
    other_lock = yaml.safe_load((other['root'] / 'pixi.lock').read_text())
    lock['platforms'] += other_lock['platforms']
    lock['environments']['default']['packages'].update(
        other_lock['environments']['default']['packages']
    )
    lock['packages'] += other_lock['packages']
    (root / 'pixi.lock').write_text(yaml.safe_dump(lock, sort_keys=False))
    context['digests'] = {p: c['digest'] for p, c in contexts.items()}
    context['archives'] = {p: c['blob'] for p, c in contexts.items()}
    # The starting pin cannot already equal the result of the pin writer.
    (root / 'pixi.toml').write_text((root / 'pixi.toml').read_text().replace(SHA, 'b8' * 20))
    context['env']['GH_TOKEN'] = 'independent-fixture-token'  # noqa: S105 — synthetic credential
    return context


def pin_call(context, args, release=None):
    root, sdk, api = context['root'], context['module'], context['api']
    spec = importlib.util.spec_from_file_location('c34_pin', root / 'tools/ci/crysta_sdk_pin.py')
    pin = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'crysta_sdk': sdk}):
        spec.loader.exec_module(pin)
    requests = []

    def release_transport(*argv, absent_ok=False):
        requests.append(argv)
        assert argv == ('repos/enhantica/crysta/releases/tags/build-' + SHA,), (
            ' F8 the pin writer must address exactly the selected source release'
        )
        assert absent_ok, ' F8 release absence is an explicit, bounded lookup result'
        return None if release is None else json.dumps(release).encode()

    output = io.StringIO()
    with (
        patch.dict(os.environ, context['env'], clear=True),
        patch.object(sdk, 'curl', api),
        patch.object(pin, 'gh', release_transport),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        code = pin.main(args)
    assert not api.refusals, ' F5 pinning cannot swallow an unsupported artifact request'
    return code, output.getvalue(), requests


def release_for(context, defect=None, target='osx-arm64'):
    assets = []
    for platform, digest in context['digests'].items():
        if defect == 'incomplete' and platform == target:
            continue
        assets.append({
            'name': f'crysta-sdk-{SHA}-{platform}.tar.gz',
            'digest': 'sha256:'
            + ('9' * 64 if defect == 'different' and platform == target else digest),
        })
    return {'tag_name': 'build-' + SHA, 'assets': assets}


def pin_and_commit(context):
    code, output, _ = pin_call(context, [SHA])
    assert code == 0, ' F8 both qualified PR artifacts must create the pin: ' + output
    root = context['root']
    actual = tomllib.loads((root / 'pixi.toml').read_text())
    for platform, digest in context['digests'].items():
        env = actual['target'][platform]['activation']['env']
        assert env['CRYSTA_SDK_TAG'] == 'build-' + SHA, (
            ' F8 the artifact-selected source must become the declared pin'
        )
        assert env['CRYSTA_SDK_SHA256'] == digest, (
            ' F8 every pinned digest must derive from the independently held archive'
        )
    # The pin used by the consumer is committed in a real isolated repository.
    for args in (
        ['init', '-q'],
        ['add', 'pixi.toml', 'pixi.lock'],
        [
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            '-c',
            'core.hooksPath=/dev/null',
            'commit',
            '-qm',
            'Pin the tested artifacts',
        ],
    ):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
    return (root / 'pixi.toml').read_bytes()


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_artifact_pin_is_committed_then_consumed_without_publication(tmp_path, platform):
    context = paired(tmp_path)
    before = pin_and_commit(context)
    with (
        patch.dict(os.environ, context['env'], clear=True),
        patch.object(context['module'], 'curl', context['api']),
    ):
        code = context['module'].main(['fetch', '--platform', platform])
    assert not context['api'].refusals, ' F5 fetch cannot swallow an unsupported artifact request'
    assert code == 0, ' F8 the real consumer must accept the artifact-written committed pin'
    assert (context['root'] / 'pixi.toml').read_bytes() == before, (
        ' F8 consumption cannot rewrite its authorizing committed pin'
    )
    assert not context['api'].releases, ' F8 the paired pin/fetch loop publishes nothing'


@pytest.mark.parametrize(
    ('defect', 'target'),
    [
        (None, None),
        ('absent', None),
        ('incomplete', 'linux-64'),
        ('incomplete', 'osx-arm64'),
        ('different', 'linux-64'),
        ('different', 'osx-arm64'),
    ],
)
def test_ship_check_compares_every_released_archive_and_never_rewrites_pin(
    tmp_path, defect, target
):
    context = paired(tmp_path)
    before = pin_and_commit(context)
    context['api'].calls.clear()
    release = None if defect == 'absent' else release_for(context, defect, target)
    code, output, requests = pin_call(context, ['--check'], release)
    assert (code == 0) == (defect is None), (
        ' I11/F8 ship admits exactly the release matching both committed archive digests: '
        + output
    )
    assert requests, ' F8 ship must actually read the durable release'
    assert not context['api'].calls, ' F8 the ship check cannot fall back to PR artifacts'
    assert (context['root'] / 'pixi.toml').read_bytes() == before, (
        ' F8 a ship check is read-only on both admission and refusal'
    )


@pytest.mark.parametrize('defect', ['missing', 'expired'])
@pytest.mark.parametrize('entry', ['pin', 'fetch'])
def test_unavailable_selected_artifact_never_borrows_an_available_decoy(  # noqa: PLR0914
    tmp_path, defect, entry
):
    context = paired(tmp_path)
    pin_and_commit(context)
    api, root = context['api'], context['root']
    before = (root / 'pixi.toml').read_bytes()
    selected = next(a for a in api.artifacts[75090] if a['name'] == 'crysta-sdk-osx-arm64')
    # An older execution of the same producing job remains available, with
    # different archive bytes. The current manifest's run_attempt is changed in
    # the zip itself so the escape reaches the producer-attempt check.
    archive = io.BytesIO()
    with (
        tarfile.open(fileobj=io.BytesIO(context['archives']['osx-arm64'])) as source,
        tarfile.open(fileobj=archive, mode='w:gz') as target,
    ):
        for member in source.getmembers():
            payload = source.extractfile(member).read()
            if member.name.endswith('/manifest.json'):
                manifest = json.loads(payload)
                manifest['tested']['run_attempt'] = 1
                payload = json.dumps(manifest).encode()
                member.size = len(payload)
            target.addfile(member, io.BytesIO(payload))
    name = f'crysta-sdk-{SHA}-osx-arm64.tar.gz'
    zipdata = io.BytesIO()
    with zipfile.ZipFile(zipdata, 'w') as packed:
        packed.writestr(name, archive.getvalue())
        packed.writestr(
            name + '.sha256', hashlib.sha256(archive.getvalue()).hexdigest() + '  ' + name
        )
    decoy = {**selected, 'id': 2799, 'created_at': '2026-09-30T22:00:00Z', 'expired': False}
    api.archives['/actions/artifacts/2799/zip'] = zipdata.getvalue()
    if defect == 'missing':
        api.artifacts[75090].remove(selected)
    else:
        selected['expired'] = True
    api.artifacts[75090].append(decoy)
    # A different source/run is also listed, but never authorizes this pin.
    foreign = {**api.runs[0], 'id': 74980, 'head_sha': 'c3' * 20}
    api.runs.append(foreign)
    api.jobs[74980] = copy.deepcopy(api.jobs[75090])
    api.artifacts[74980] = [
        {**decoy, 'id': 2798, 'workflow_run': {'id': 74980, 'head_sha': 'c3' * 20}}
    ]
    api.archives['/actions/artifacts/2798/zip'] = zipdata.getvalue() + b'foreign run bytes'
    # This witness exercises older artifacts and foreign-run lookup only.
    # It makes no claim about selection of an independently usable foreign cache.
    api.calls.clear()
    if entry == 'pin':
        code, output, _ = pin_call(context, [SHA])
    else:
        output_stream = io.StringIO()
        with (
            patch.dict(os.environ, context['env'], clear=True),
            patch.object(context['module'], 'curl', api),
            contextlib.redirect_stderr(output_stream),
            contextlib.redirect_stdout(output_stream),
        ):
            code = context['module'].main(['fetch', '--platform', 'osx-arm64'])
        output = output_stream.getvalue()
    assert not api.refusals, ' F5 expected expiry must not hide unsupported transport operations'
    assert code != 0, ' F8 an available older or foreign archive cannot rescue expiry: ' + output
    assert 're-pin' in output and 're-run' in output, (
        ' I13 a rejected fallback must still name the producing-job and pin repair'
    )
    assert (root / 'pixi.toml').read_bytes() == before, (
        ' F8 refusal cannot bless an alternative archive by rewriting the pin'
    )
    assert not any('/74980/' in call or '/2798/' in call for call in api.calls), (
        ' F8 a different available build must never be selected for the requested pin'
    )
