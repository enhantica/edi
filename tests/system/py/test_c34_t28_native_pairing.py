"""Native transport binds the committed SDK, source, ABI, run and every restored byte."""

import hashlib
import io
import json
import shutil
import subprocess
import sysconfig
import tarfile
from pathlib import Path

import pytest

from tests.fixtures.native_transport import run as native
from tests.fixtures.native_transport import world
from tests.integration.py.test_e09_t75_native_workflow import ROSTER


def independent_artifact(context):
    folder = Path(context.env['EDI_NATIVE_ARCHIVES'])
    folder.mkdir()
    asset = folder / 'edi-native.tar'
    with tarfile.open(asset, 'w') as archive:
        for relative, payload in context.payloads.items():
            info = tarfile.TarInfo(relative)
            info.size = len(payload)
            info.mode = mode(relative)
            archive.addfile(info, io.BytesIO(payload))
    prefix = context.root / 'build/crysta-prefix'
    record = {
        'source_sha': context.head,
        'source_tree': context.tree,
        'run_id': context.env['GITHUB_RUN_ID'],
        'run_attempt': '1',
        'job': 'native',
        'platform': context.platform,
        'workspace': str(context.root),
        'python_abi': sysconfig.get_config_var('SOABI'),
        'pixi_lock_sha256': digest(context.root / 'pixi.lock'),
        'crysta_source_sha': context.pin,
        'crysta_sdk_sha256': digest(prefix / 'share/crysta-sdk/manifest.json'),
        'crysta_library_sha256': digest(prefix / 'lib/libcrysta_core.a'),
        'crysta_linked_sha': context.pin,
        'sha256': digest(asset),
        'files': {
            name: hashlib.sha256(data).hexdigest() + f' {mode(name):o}'
            for name, data in context.payloads.items()
        },
    }
    (folder / 'edi-native.json').write_text(json.dumps(record), encoding='utf-8')
    return folder, record


def mode(name):
    return (
        0o755
        if name.endswith(('easydiffraction', 'edi_tests', 'edi_integration_tests'))
        else 0o644
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
@pytest.mark.parametrize('mode', ['matching', 'stale'])
def test_intermediate_native_producer_packs_the_branch_sdk_without_repinning(
    tmp_path, platform, event, mode
):
    context = world(tmp_path, platform, event, matching_pin=mode == 'matching')
    before = (context.root / 'pixi.toml').read_bytes()
    result = native(context, 'pack', '--out', context.env['EDI_NATIVE_ARCHIVES'])
    assert (result.returncode == 0) == (mode == 'matching'), (
        'Native production admits its committed SDK and refuses a foreign candidate: '
        + result.stdout
        + result.stderr
    )
    if mode == 'matching':
        record = json.loads(
            (Path(context.env['EDI_NATIVE_ARCHIVES']) / 'edi-native.json').read_text()
        )
        assert record['crysta_source_sha'] == context.pin, (
            'Native packing binds its committed engine'
        )
        assert record['source_sha'] == context.head, (
            'Native packing binds its actual source commit'
        )
        assert record['source_tree'] == context.tree, 'Native packing binds its actual source tree'
    else:
        assert 'committed SDK pin' in result.stderr, 'Foreign SDK refusal names the pin boundary'
    assert (context.root / 'pixi.toml').read_bytes() == before, (
        'Native packing cannot rewrite its pin'
    )
    assert not context.commands.exists(), 'Native packaging performs no compiler fallback'


@pytest.mark.parametrize(('consumer', 'platform'), ROSTER)
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
def test_every_native_consumer_restores_the_branch_build_and_rechecks_bytes(
    tmp_path, consumer, platform, event
):
    context = world(tmp_path, platform, event)
    folder, _ = independent_artifact(context)
    shutil.rmtree(context.root / 'build/ci')
    context.env |= {'EDI_NATIVE_ARTIFACT': '1', 'GITHUB_JOB': consumer}
    for attempt in range(2):
        if attempt:
            (context.root / 'build/ci/cli/easydiffraction').write_text('overwritten cache bytes\n')
        dependency = subprocess.run(
            ['bash', 'tools/ci/core-build.sh'],
            cwd=context.root,
            env=context.env,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert dependency.returncode == 0, (
            'Every actual core dependency restores and rechecks native transport: '
            + dependency.stdout
            + dependency.stderr
        )
        for relative, payload in context.payloads.items():
            assert (context.root / relative).read_bytes() == payload, (
                'Every restore preserves the independent artifact payload including cache repair'
            )
    assert folder.is_dir(), 'Restoration retains its exact addressed artifact'
    assert not context.commands.exists(), (
        'Consumers restore without ever invoking a fallback compiler'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch'])
def test_native_tool_independently_restores_the_branch_artifact(tmp_path, platform, event):
    context = world(tmp_path, platform, event)
    independent_artifact(context)
    shutil.rmtree(context.root / 'build/ci')
    result = native(context, 'restore')
    assert result.returncode == 0, (
        'The real restore admits independently planted matching bytes: ' + result.stderr
    )
    for relative, payload in context.payloads.items():
        assert (context.root / relative).read_bytes() == payload, (
            'Restoration preserves independent native bytes'
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
        'python_abi',
        'pixi_lock_sha256',
        'crysta_library_sha256',
    ],
)
def test_branch_native_handoff_retains_every_independent_binding(tmp_path, platform, damage):
    context = world(tmp_path, platform, 'pull_request')
    folder, record = independent_artifact(context)
    admitted = native(context, 'restore')
    assert admitted.returncode == 0, (
        'The undamaged transport must admit before each challenge: ' + admitted.stderr
    )
    if damage == 'tar-bytes':
        with (folder / 'edi-native.tar').open('ab') as archive:
            archive.write(b'independent changed archive bytes')
    else:
        field = {
            'CRYSTA_SDK_TAG': 'crysta_source_sha',
            'CRYSTA_SDK_SHA256': 'crysta_sdk_sha256',
        }.get(damage, damage)
        record[field] = 'incorrect independently supplied coordinate'
        (folder / 'edi-native.json').write_text(json.dumps(record), encoding='utf-8')
    result = native(context, 'restore')
    assert result.returncode != 0, (
        'Every source, ABI, run, pin, manifest, library and byte binding refuses drift'
    )
    assert not context.commands.exists(), 'A refused artifact cannot invoke a fallback compiler'


@pytest.mark.parametrize('command', ['pack', 'restore'])
@pytest.mark.parametrize(
    'damage',
    [
        'missing-integration',
        'nonexecutable-integration',
        'dirty-source',
        'embedded-data',
        'untracked-data',
    ],
)
def test_native_transport_requires_the_declared_runners_and_clean_source(
    tmp_path, command, damage
):
    context = world(tmp_path, 'linux-64', 'pull_request')
    runner = context.root / 'build/ci/core/edi_integration_tests'
    if damage in {'embedded-data', 'untracked-data'}:
        path = context.root / 'data/report/report.js'
        path.parent.mkdir(parents=True)
        if damage == 'embedded-data':
            path.write_text('original embedded script\n', encoding='utf-8')
            from tests.fixtures.native_transport import git  # noqa: PLC0415

            git(context.root, 'add', 'data')
            git(context.root, 'commit', '-qm', 'Record independent embedded input')
            context.head = git(context.root, 'rev-parse', 'HEAD')
            context.tree = git(context.root, 'rev-parse', 'HEAD^{tree}')
            context.payloads['build/ci/python/edi/_edi.py'] = (
                '__build_commit__ = ' + repr(context.head) + '\n'
            ).encode()
        path.write_text('uncommitted embedded input\n', encoding='utf-8')
    elif damage == 'dirty-source':
        (context.root / 'CMakeLists.txt').write_text('uncommitted producer input\n')
    elif damage == 'missing-integration':
        runner.unlink()
        context.payloads.pop('build/ci/core/edi_integration_tests')
    else:
        runner.chmod(0o644)
    if command == 'restore':
        folder, record = independent_artifact(context)
        if damage == 'nonexecutable-integration':
            with tarfile.open(folder / 'edi-native.tar') as source:
                members = [(info, source.extractfile(info).read()) for info in source.getmembers()]
            with tarfile.open(folder / 'edi-native.tar', 'w') as archive:
                for info, data in members:
                    if info.name.endswith('edi_integration_tests'):
                        info.mode = 0o644
                        record['files'][info.name] = hashlib.sha256(data).hexdigest() + ' 644'
                    archive.addfile(info, io.BytesIO(data))
            record['sha256'] = digest(folder / 'edi-native.tar')
            (folder / 'edi-native.json').write_text(json.dumps(record), encoding='utf-8')
    result = native(
        context,
        command,
        *(['--out', context.env['EDI_NATIVE_ARCHIVES']] if command == 'pack' else []),
    )
    assert result.returncode != 0, (
        'Both producer and consumer require all declared runners and clean native input'
    )
    assert not context.commands.exists(), (
        'A missing artifact precondition never starts compilation'
    )


@pytest.mark.parametrize('escape', ['parent', 'absolute', 'symlink', 'hardlink', 'fifo'])
def test_native_restore_refuses_archive_containment_escapes_before_replacing_tree(
    tmp_path, escape
):
    context = world(tmp_path, 'linux-64', 'pull_request')
    folder, record = independent_artifact(context)
    entry = tarfile.TarInfo(
        '../outside'
        if escape == 'parent'
        else '/outside'
        if escape == 'absolute'
        else 'build/ci/escape'
    )
    if escape in {'symlink', 'hardlink'}:
        entry.type = tarfile.SYMTYPE if escape == 'symlink' else tarfile.LNKTYPE
        entry.linkname = '../../outside' if escape == 'symlink' else '../outside'
    elif escape == 'fifo':
        entry.type = tarfile.FIFOTYPE
    with tarfile.open(folder / 'edi-native.tar', 'a') as archive:
        archive.addfile(entry)
    record['sha256'] = digest(folder / 'edi-native.tar')
    (folder / 'edi-native.json').write_text(json.dumps(record), encoding='utf-8')
    before = (context.root / 'build/ci/cli/easydiffraction').read_bytes()
    result = native(context, 'restore')
    assert result.returncode != 0, (
        'Archive paths, links and special files cannot escape the native tree'
    )
    assert (context.root / 'build/ci/cli/easydiffraction').read_bytes() == before, (
        'Containment refusal precedes replacement of the admitted native tree'
    )
    assert not context.commands.exists(), 'A malformed native archive never invokes compilation'


@pytest.mark.parametrize('damage', ['bytes', 'mode', 'foreign-import', 'wrong-commit'])
def test_native_restore_rechecks_independent_file_modes_and_import_identity(tmp_path, damage):
    context = world(tmp_path, 'linux-64', 'pull_request')
    if damage == 'wrong-commit':
        context.payloads['build/ci/python/edi/_edi.py'] = b'__build_commit__ = "foreign-source"\n'
    elif damage == 'foreign-import':
        context.payloads['build/ci/python/edi/_edi.py'] += b'__file__ = "/outside/_edi.py"\n'
    folder, record = independent_artifact(context)
    if damage in {'bytes', 'mode'}:
        name = 'build/ci/cli/easydiffraction'
        record['files'][name] = (
            '0' * 64 if damage == 'bytes' else digest(context.root / name)
        ) + ' 644'
        (folder / 'edi-native.json').write_text(json.dumps(record), encoding='utf-8')
    result = native(context, 'restore')
    assert result.returncode != 0, (
        'Archive hashes cannot bypass file bytes, modes, imported source or module confinement'
    )
    assert not context.commands.exists(), (
        'A refused native import cannot trigger a compiler fallback'
    )
