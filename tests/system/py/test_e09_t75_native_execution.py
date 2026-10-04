"""I34: independently packaged native bytes exercise restore/import/refusal.

The planted Python module is a transport witness, not a numerical engine or
live compile-count measurement. It supplies independent embedded commit bytes.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest
from ci_runner_contract import platform_job

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal, checked_program
from tests.fixtures.e09_t75_workflow import workflow_cwd, workflow_env
from tests.integration.py.test_e09_t75_native_workflow import (
    ROSTER,
    consumer_boundary,
    jobs,
    producer_boundary,
)
from tests.integration.py.test_e09_t75_sdk_consumer import consumer as sdk_fixture

ROOT = Path(__file__).resolve().parents[3]


def restore(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
    tmp_path,
    consumer,
    platform,
    defect=None,
    job_override=None,
    entry_override=None,
    layout='repository',
    *,
    repeat_dependency=False,
    pin_transform=None,
):
    job = {**(job_override or platform_job(jobs(), consumer, platform)), '_consumer': consumer}
    download, step, leg = consumer_boundary(job, platform)
    repo = tmp_path / 'edi'
    shutil.copytree(
        ROOT / 'tools/ci', repo / 'tools/ci', ignore=shutil.ignore_patterns('__pycache__')
    )
    (repo / '.gitignore').write_text('__pycache__/\n')
    if entry_override is not None:
        (repo / 'tools/ci/core-build.sh').write_text(entry_override)
    (repo / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.28)\n')
    pin = {'CRYSTA_SDK_TAG': 'build-' + 'a7' * 20, 'CRYSTA_SDK_SHA256': '7' * 64}
    (repo / 'pixi.toml').write_text(
        '[target.'
        + platform
        + '.activation.env]\n'
        + ''.join(key + '="' + value + '"\n' for key, value in pin.items())
    )
    # Supply the real SDK check with an independently qualified downloadable asset;
    # no compiler or SDK checker is replaced by this transport preparation.

    sdk_home = tmp_path / 'sdk-download'
    sdk_home.mkdir()
    sdk_env, sdk_repo, _ = sdk_fixture(
        sdk_home, platform=platform, download=True, prepare_only=True
    )
    (repo / 'pixi.lock').write_bytes((sdk_repo / 'pixi.lock').read_bytes())
    (repo / 'pixi.toml').write_bytes((sdk_repo / 'pixi.toml').read_bytes())
    if defect == 'single-quoted-pin':
        pin_path = repo / 'pixi.toml'
        pin_path.write_text(pin_path.read_text().replace(chr(34), chr(39)))
    pin = __import__('tomllib').loads((repo / 'pixi.toml').read_text())['target'][platform][
        'activation'
    ]['env']
    pin = {k: pin[k] for k in ('CRYSTA_SDK_TAG', 'CRYSTA_SDK_SHA256')}
    if pin_transform is not None:
        pin_path = repo / 'pixi.toml'
        pin_path.write_text(pin_transform(pin_path.read_text()))
    realgit = shutil.which('git')

    def git(*args):
        return subprocess.run(
            [
                realgit,
                '-C',
                str(repo),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=f@example.invalid',
                *args,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()

    git('init', '-q', '-b', 'independent')
    git('add', '.')
    git('commit', '-qm', 'Independent native source')
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    payloads = {
        'build/ci/.crysta-linked-sha': ('a7' * 20 + '\n').encode(),
        'build/ci/python/edi/__init__.py': (
            'from . import _edi\n__build_commit__ = '
            + repr('f' * 40 if defect == 'embedded-commit' else head)
            + '\n'
        ).encode(),
        'build/ci/python/edi/_edi.py': b'WITNESS = "independently packaged native content"\n',
        'build/ci/cli/easydiffraction': b'#!/bin/sh\necho easydiffraction-independent-version\n',
        'build/ci/core/edi_tests': b'#!/bin/sh\necho "independent native test witness"\n',
    }
    dest = str(download.get('with', {}).get('path', '.'))
    dest = dest.replace('${{ github.workspace }}', str(repo)).replace(
        '${{ runner.temp }}', str(tmp_path)
    )
    assert '${{' not in dest, ' I34 native download destination must resolve independently'
    folder = Path(dest) if Path(dest).is_absolute() else repo / dest
    folder.mkdir(parents=True, exist_ok=True)
    asset = folder / 'edi-native.tar'
    with tarfile.open(asset, 'w') as archive:
        for name, payload in payloads.items():
            archive_name = name.removeprefix('build/ci/') if layout == 'contents' else name
            if defect == 'archive-root':
                archive_name = 'foreign/' + archive_name
            info = tarfile.TarInfo(archive_name)
            info.size = len(payload)
            info.mode = 0o755 if name.endswith(('edi_tests', 'easydiffraction')) else 0o644
            archive.addfile(info, io.BytesIO(payload))
        if defect == 'parent-member':
            info = tarfile.TarInfo('build/ci/../../escaped.txt')
            payload = b'ordinary incorrectly rebased archive member'
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        if defect in {'symlink-destination', 'hardlink-destination'}:
            info = tarfile.TarInfo('build/ci/escape')
            info.type = tarfile.SYMTYPE if defect == 'symlink-destination' else tarfile.LNKTYPE
            info.linkname = '../../pixi.toml' if info.issym() else 'pixi.toml'
            archive.addfile(info)
    manifest = {
        'source_sha': head,
        'source_tree': tree,
        'run_id': '75134',
        'run_attempt': '1',
        'job': 'native',
        'crysta_linked_sha': 'a7' * 20,
        'files': {
            name: hashlib.sha256(payload).hexdigest()
            + (' 755' if name.endswith(('edi_tests', 'easydiffraction')) else ' 644')
            for name, payload in payloads.items()
        },
        'platform': platform,
        'workspace': str(repo),
        **pin,
        'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
        # The plan binds the tar digest, not one metadata field spelling.
        'tar_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
    }
    # All expected values come from the consumer, never from this mutable metadata.
    if defect == 'sha256':
        manifest['tar_sha256'] = 'wrong-independent-coordinate'
    if defect in manifest:
        manifest[defect] = 'wrong-independent-coordinate'
    if defect == 'tar-bytes':
        asset.write_bytes(asset.read_bytes() + b'corrupt tar bytes')
    (folder / 'edi-native.json').write_text(json.dumps(manifest))
    if defect == 'missing-tar':
        asset.unlink()
    if defect == 'missing-manifest':
        (folder / 'edi-native.json').unlink()
    binary = tmp_path / 'bin'
    binary.mkdir()
    for name in ('cmake', 'ninja', 'make', 'c++', 'clang++', 'g++'):
        command = binary / name
        command.write_text('#!/bin/sh\necho "$0 $*" >> "$NATIVE_COMPILES"\nexit 91\n')
        command.chmod(0o755)
    pixi = binary / 'pixi'
    pixi.write_text(
        '#!/bin/sh\n[ "$*" = "run core-build" ] || exit 64\nexec bash tools/ci/core-build.sh\n'
    )
    pixi.chmod(0o755)
    uname = binary / 'uname'
    uname.write_text(
        '#!/bin/sh\ncase "$1" in -m) echo '
        + ('arm64' if platform == 'osx-arm64' else 'x86_64')
        + ';; *) echo '
        + ('Darwin' if platform == 'osx-arm64' else 'Linux')
        + ';; esac\n'
    )
    uname.chmod(0o755)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(('GIT_', 'EDI_', 'CRYSTA_', 'PIXI_', 'GITHUB_', 'HUB_', 'RELAY_'))
    }
    env.update(
        PYTHONDONTWRITEBYTECODE='1',
        PATH=str(binary) + ':' + str(Path(sys.executable).parent) + ':' + os.defpath,
        EDI_NATIVE_ARTIFACT='1',
        GITHUB_RUN_ID='75134',
        GITHUB_JOB=consumer,
        GITHUB_ENV=str(tmp_path / 'job-env'),
        GITHUB_RUN_ATTEMPT='2',
        GITHUB_SHA=head,
        GITHUB_WORKSPACE=str(repo),
        RUNNER_TEMP=str(tmp_path),
        PIXI_PLATFORM=platform,
        CONDA_SUBDIR=platform,
        RUNNER_OS='macOS' if platform == 'osx-arm64' else 'Linux',
        RUNNER_ARCH='ARM64' if platform == 'osx-arm64' else 'X64',
        NATIVE_COMPILES=str(tmp_path / 'compiles'),
        PYTHONPATH=str(repo / 'build/ci/python'),
    )
    shutil.copy2(sdk_home / 'bin/curl', binary / 'curl')
    env.update(
        DOWNLOAD_FIXTURE=str(sdk_home),
        GITHUB_TOKEN=sdk_env['GITHUB_TOKEN'],
        PIXI_ENVIRONMENT_NAME='default',
        MACOSX_DEPLOYMENT_TARGET='11.0',
    )
    source = repo / 'build/crysta-src'
    source.mkdir(parents=True)
    (source / 'CRYSTA_SOURCE_SHA').write_text('a7' * 20)
    git_transport = binary / 'git'
    git_transport.write_text(
        '#!'
        + sys.executable
        + '\n'
        + 'import os,sys\na=sys.argv[1:]\nargs=a\n'
        + 'if args == '
        + repr(['-C', str(source), 'rev-parse', 'HEAD'])
        + ':\n'
        + '    print('
        + repr('a7' * 20)
        + '); sys.exit(0)\n'
        + 'if any(x in args for x in ("fetch","clone","ls-remote","push")):sys.exit(64)\n'
        + 'os.execv('
        + repr(realgit)
        + ', ['
        + repr(realgit)
        + ',*args])\n'
    )
    git_transport.write_text(checked_program(git_transport.read_text(), 'git'))
    git_transport.chmod(0o755)

    def resolve(value):
        value = str(value).replace(
            '${{ steps.crysta-token.outputs.token }}', sdk_env['GITHUB_TOKEN']
        )
        value = value.replace('${{ needs.changes.outputs.crysta_sha }}', 'a7' * 20)
        for key, item in leg.items():
            value = value.replace('${{ matrix.' + key + ' }}', str(item))
        return value

    runs = []
    commands = [step, step]
    if repeat_dependency:
        # Replay the actual core job's separate Pixi dependency invocation.
        # Only its core-build dependency is in scope; the C++ smoke leaf is covered separately.

        tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
        use = next(
            s for s in job['steps'] if s.get('run', '').strip() == 'pixi run crysta-consumer'
        )
        assert 'core-build' in tasks['crysta-consumer']['depends-on'], (
            ' I6 the actual later job step must repeat the declared native dependency'
        )
        commands[1] = {**use, 'run': ' '.join(tasks['core-build']['cmd'])}
    for attempt in range(
        2
    ):  # Repeated dependencies must validate without compiling; prior attempt stays valid.
        if attempt == 1 and defect in {'cache-cli', 'cache-tests'}:
            target = repo / (
                'build/ci/cli/easydiffraction'
                if defect == 'cache-cli'
                else 'build/ci/core/edi_tests'
            )
            target.unlink()
        if attempt == 1 and defect in {'mode-cli', 'mode-tests'}:
            target = repo / (
                'build/ci/cli/easydiffraction'
                if defect == 'mode-cli'
                else 'build/ci/core/edi_tests'
            )
            target.chmod(target.stat().st_mode & ~0o111)
        r = subprocess.run(
            ['bash', '-eu', '-c', commands[attempt]['run']],
            cwd=workflow_cwd(job, commands[attempt], repo, resolve),
            env=workflow_env(job, commands[attempt], env, resolve),
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        runs.append(r)
        exported = Path(env['GITHUB_ENV'])
        if exported.exists():
            for line in exported.read_text(encoding='utf-8').splitlines():
                key, sep, value = line.partition('=')
                assert sep and key, (
                    ' I6 bounded job replay requires observable environment assignments'
                )
                env[key] = value
            exported.write_text('', encoding='utf-8')
        if r.returncode:
            break
    imported = subprocess.run(
        [
            sys.executable,
            '-c',
            'import edi,edi._edi; print(edi.__build_commit__); print(edi._edi.WITNESS)',
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    if runs and all(r.returncode == 0 for r in runs):
        assert all(
            (repo / name).is_file() and (repo / name).read_bytes() == payload
            for name, payload in payloads.items()
        ), ' I34 restore must preserve independent packaged bytes'
    assert_no_swallowed_refusal(sdk_home, all(r.returncode == 0 for r in runs))
    return runs, imported, head, tmp_path / 'compiles'


def assert_restored(result):
    runs, imported, head, compiles = result
    assert len(runs) == 2, (
        ' I34 prior-attempt artifact restores and revalidates without rebuilding'
    )
    assert all(r.returncode == 0 for r in runs), (
        ' I34 prior-attempt artifact restores and revalidates without rebuilding'
    )
    assert imported.returncode == 0, (
        ' I34 successful restore must import the packaged content and exact embedded commit'
    )
    assert imported.stdout.splitlines() == [
        head,
        'independently packaged native content',
    ], ' I34 successful restore must import the packaged content and exact embedded commit'
    assert not compiles.exists(), ' I34 consumer and repeated restore must compile nothing'


NATIVE_ESCAPES = (
    'missing-tar',
    'missing-manifest',
    'archive-root',
    'source_sha',
    'source_tree',
    'run_id',
    'platform',
    'workspace',
    'CRYSTA_SDK_TAG',
    'CRYSTA_SDK_SHA256',
    'sha256',
    'tar-bytes',
    'embedded-commit',
)


@pytest.fixture(scope='module')
def native_layout_controls(tmp_path_factory):
    cache = {}

    def admitted(consumer, platform):
        key = (consumer, platform)
        if key in cache:
            return cache[key]
        base = tmp_path_factory.mktemp('native-control')
        # D6 prescribes the build bytes, not an internal tar member prefix.
        # Observe every allowed representation against independent restored bytes.
        controls = []
        for layout in ('repository', 'contents'):
            control = base / layout
            control.mkdir()
            result = restore(control, consumer, platform, layout=layout)
            if (
                len(result[0]) == 2
                and all(r.returncode == 0 for r in result[0])
                and result[1].returncode == 0
            ):
                assert_restored(result)
                controls.append(layout)
        assert controls, ' I34 one prescribed archive form must restore without compiling'
        cache[key] = controls
        return controls

    return admitted


@pytest.mark.parametrize(('consumer', 'platform'), ROSTER)
@pytest.mark.parametrize('defect', NATIVE_ESCAPES)
@pytest.mark.usefixtures('private_native_workflow')
def test_native_every_consumer_restores_imports_and_refuses_each_bound_escape(
    tmp_path, consumer, platform, defect, native_layout_controls
):
    for layout in native_layout_controls(consumer, platform):
        bad = tmp_path / (layout + '-' + defect)
        bad.mkdir()
        runs, _, _, compiles = restore(bad, consumer, platform, defect, layout=layout)
        assert runs, ' I34 missing or mismatched native artifact must refuse'
        assert runs[-1].returncode != 0, ' I34 missing or mismatched native artifact must refuse'
        assert (
            defect == 'archive-root'
            or (
                defect == 'missing-manifest'
                and 'edi-native.json' in (runs[-1].stdout + runs[-1].stderr)
            )
            or (defect == 'tar-bytes' and 'sha256' in (runs[-1].stdout + runs[-1].stderr))
            or (defect == 'embedded-commit' and 'HEAD' in (runs[-1].stdout + runs[-1].stderr))
            or defect.replace('missing-', '').lower()
            in (runs[-1].stdout + runs[-1].stderr).lower()
            or 'mismatch' in (runs[-1].stdout + runs[-1].stderr).lower()
        ), ' I34 native refusal must diagnose the missing or mismatched bound value'
        assert not compiles.exists(), ' I34 native refusal must never compile a fallback'


CONTROL_ENTRY = """#!/bin/bash
set -euo pipefail
python3 - <<'CONTROL'
import hashlib,json,os,pathlib,subprocess,tarfile,sys,tomllib,importlib
root=pathlib.Path.cwd()
asset=root/'edi-native.tar';meta=root/'edi-native.json'
if not asset.is_file() or not meta.is_file():sys.exit('missing tar or manifest')
d=json.loads(meta.read_text())
def git(ref):return subprocess.check_output(['git','rev-parse',ref],text=True).strip()
platform=os.environ['PIXI_PLATFORM']
expected={'source_sha':git('HEAD'),'source_tree':git('HEAD^{tree}'),
    'run_id':os.environ['GITHUB_RUN_ID'],'platform':platform,'workspace':os.environ['GITHUB_WORKSPACE'],
    **{k:v for k,v in tomllib.loads((root/'pixi.toml').read_text())
       ['target'][platform]['activation']['env'].items()
       if k in ('CRYSTA_SDK_TAG','CRYSTA_SDK_SHA256')},
    'sha256':hashlib.sha256(asset.read_bytes()).hexdigest()}
for key,value in expected.items():
    if d.get(key)!=value:sys.exit('mismatch '+key)
with tarfile.open(asset) as archive:archive.extractall(root,filter='data')
sys.path.insert(0,str(root/'build/ci/python'))
importlib.invalidate_caches()
import edi,edi._edi
if edi.__build_commit__!=git('HEAD'):sys.exit('mismatch embedded-commit')
CONTROL
"""


def control_job(consumer, platform):
    runner = (
        ['self-hosted', 'macOS', 'ARM64']
        if platform == 'osx-arm64'
        else ['self-hosted', 'Linux', 'X64']
    )
    return {
        'runs-on': runner,
        'env': {'EDI_NATIVE_ARTIFACT': '1'},
        'steps': [
            {'uses': 'actions/download-artifact@v4', 'with': {'name': 'edi-native-' + platform}},
            {'name': 'Restore and validate the native artifact', 'run': 'pixi run core-build'},
            {
                'run': 'pixi run '
                + {
                    'audit': 'per-pr-audit',
                    'core': 'crysta-consumer',
                    'notebooks': 'notebook-tests',
                    'cli-python': 'cli-projects',
                    'docs': 'notebook-exec-ci',
                    'app': 'app-build',
                    'app-wasm': 'wasm-build',
                }[consumer]
            },
        ],
    }


@pytest.fixture(scope='module')
def native_oracle_controls(tmp_path_factory):
    cache = set()

    def admitted(consumer, platform):
        if (consumer, platform) not in cache:
            good = tmp_path_factory.mktemp('oracle-control')
            assert_restored(
                restore(
                    good,
                    consumer,
                    platform,
                    job_override=control_job(consumer, platform),
                    entry_override=CONTROL_ENTRY,
                )
            )
            cache.add((consumer, platform))

    return admitted


@pytest.mark.parametrize(('consumer', 'platform'), ROSTER)
@pytest.mark.parametrize('defect', [d for d in NATIVE_ESCAPES if d != 'archive-root'])
def test_native_fixture_matching_import_and_every_independent_field_refusal(
    tmp_path, consumer, platform, defect, native_oracle_controls
):
    native_oracle_controls(consumer, platform)
    job = control_job(consumer, platform)
    bad = tmp_path / defect
    bad.mkdir()
    runs, _, _, compiles = restore(
        bad, consumer, platform, defect, job_override=job, entry_override=CONTROL_ENTRY
    )
    assert runs[-1].returncode != 0, (
        ' I34 each native resource/content escape must reach refusal without compiling'
    )
    assert not compiles.exists(), (
        ' I34 each native resource/content escape must reach refusal without compiling'
    )


@pytest.mark.parametrize(
    'coordinate',
    ['name', 'repository', 'run-id', 'download-if', 'restore-if', 'operation', 'order'],
)
def test_native_job_path_oracle_rejects_wrong_resource_or_restore_operation(coordinate):
    job = control_job('app', 'osx-arm64')
    job['_consumer'] = 'app'
    consumer_boundary(job, 'osx-arm64')
    if coordinate in {'name', 'repository', 'run-id'}:
        job['steps'][0]['with'][coordinate] = {
            'name': 'edi-native-linux-64',
            'repository': 'other/edi',
            'run-id': '75133',
        }[coordinate]
    elif coordinate == 'download-if':
        job['steps'][0]['if'] = False
    elif coordinate == 'restore-if':
        job['steps'][1]['if'] = False
    elif coordinate == 'operation':
        job['steps'][1]['run'] = 'pixi run --help'
    else:
        job['steps'][1], job['steps'][2] = job['steps'][2], job['steps'][1]
    with pytest.raises(AssertionError, match=' I34'):
        consumer_boundary(job, 'osx-arm64')


def native_producer(tmp_path, platform, defect=None):  # noqa: PLR0914, PLR0915
    # Seed transport bytes independently; the actual producer packs and proves them.
    job = control_job('audit', platform)
    result = restore(tmp_path, 'audit', platform, job_override=job, entry_override=CONTROL_ENTRY)
    assert_restored(result)
    repo = tmp_path / 'edi'
    cli = repo / 'build/ci/cli/easydiffraction'
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text('#!/bin/sh\necho easydiffraction-independent-version\n')
    cli.chmod(0o755)
    expected = {
        str(p.relative_to(repo)): p.read_bytes()
        for p in (repo / 'build/ci').rglob('*')
        if p.is_file() and p.name != '.edi-native.json'
    }
    # Preserve planted bytes outside the producer-writable tree; only actual build creates them.
    (tmp_path / 'producer-bytes.json').write_text(
        json.dumps({k: v.hex() for k, v in expected.items()})
    )
    shutil.rmtree(repo / 'build/ci')
    pixi = tmp_path / 'bin/pixi'
    pixi.write_text(
        '#!'
        + sys.executable
        + '\n'
        + r"""import os,sys,json
from pathlib import Path
root=Path(os.environ['RUNNER_TEMP']);args=sys.argv[1:]
with (root/'producer-operations').open('a') as out:out.write(json.dumps(args)+'\n')
if args==['run','core-build']:
    if (os.environ.get('EDI_CORE_TARGETS')!='edi_tests'
        or os.environ.get('EDI_NATIVE_ARTIFACT','0')!='0'):sys.exit(64)
    for name,value in json.loads((root/'producer-bytes.json').read_text()).items():
        path=Path.cwd()/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(bytes.fromhex(value))
        if name.endswith(('easydiffraction','edi_tests')):path.chmod(0o755)
    sys.exit(0)
if args[:2]!=['run','python']:sys.exit(64)
os.execv("""
        + repr(sys.executable)
        + ',['
        + repr(sys.executable)
        + ',*args[2:]])\n'
    )
    pixi.chmod(0o755)
    native = platform_job(jobs(), 'native', platform)
    (build_index, build_step), (pack_index, _), (upload_index, _) = producer_boundary(native)
    pack = [
        x for x in native['steps'] if 'edi_native.py' in x.get('run', '') and 'pack' in x['run']
    ]
    assert len(pack) == 1, ' I34 producer must execute one artifact pack operation'
    step = pack[0]
    assert step.get('if', 'success()') == 'success()' and not step.get('continue-on-error'), (
        ' I34 the producer pack must execute and propagate a failure'
    )
    command = step['run']
    if defect == 'resource':
        command = command.replace('/edi-native', '/foreign-native')
    elif defect == 'operation':
        command = command.replace(' pack ', ' restore ')
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(('GIT_', 'EDI_', 'CRYSTA_', 'PIXI_', 'GITHUB_', 'HUB_', 'RELAY_'))
    }
    env.update(
        PYTHONDONTWRITEBYTECODE='1',
        PATH=str(tmp_path / 'bin') + ':' + str(Path(sys.executable).parent) + ':' + os.defpath,
        GITHUB_RUN_ID='75134',
        GITHUB_RUN_ATTEMPT='2',
        GITHUB_JOB='native',
        GITHUB_WORKSPACE=str(repo),
        RUNNER_TEMP=str(tmp_path),
        PIXI_PLATFORM=platform,
        RUNNER_OS='macOS' if platform == 'osx-arm64' else 'Linux',
        RUNNER_ARCH='ARM64' if platform == 'osx-arm64' else 'X64',
        PYTHONPATH=str(repo / 'build/ci/python'),
    )

    def resolve(value):
        value = str(value)
        for expression, observed in {
            'needs.changes.outputs.crysta_sha': 'a7' * 20,
            'steps.crysta-token.outputs.token': 'independent-token',
            'runner.temp': str(tmp_path),
            'github.workspace': str(repo),
        }.items():
            value = value.replace('${{ ' + expression + ' }}', observed)
        return value

    build_run = subprocess.run(
        ['bash', '-eu', '-c', resolve(build_step['run'])],
        cwd=workflow_cwd(native, build_step, repo, resolve),
        env=workflow_env(native, build_step, env, resolve),
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert build_run.returncode == 0, (
        ' I34 actual producer build operation must succeed before pack'
    )
    if defect == 'linked-pin':
        (repo / 'build/ci/.crysta-linked-sha').write_text('f' * 40 + '\n')
    run = subprocess.run(
        ['bash', '-eu', '-c', command],
        cwd=workflow_cwd(native, step, repo, resolve),
        env=workflow_env(native, step, env, resolve),
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    upload = native['steps'][upload_index]
    assert build_index < pack_index < upload_index, (
        ' I34 upload cannot be replayed independently of actual producer order'
    )
    assert upload.get('if', 'success()') == 'success()' and not upload.get('continue-on-error'), (
        ' I34 upload must execute after its actual successful pack'
    )
    selected = set()
    for raw_token in str(upload['with']['path']).splitlines():
        token = raw_token.replace('${{ runner.temp }}', str(tmp_path)).replace(
            '${{ github.workspace }}', str(repo)
        )
        token = token.strip()
        for path in Path('/').glob(token.lstrip('/')):
            selected.update(path.rglob('*') if path.is_dir() else [path])
    selected = {p for p in selected if p.is_file()}
    ready = tmp_path / 'edi-native'
    if defect is not None:
        assert (
            run.returncode != 0
            or not {ready / 'edi-native.tar', ready / 'edi-native.json'} <= selected
        ), ' I34 wrong producer resource or operation cannot supply the selected upload'
        return
    assert run.returncode == 0, (
        f' I34 independently planted producer bytes must pack: {run.stderr}'
    )
    assert selected == {ready / 'edi-native.tar', ready / 'edi-native.json'}, (
        ' I34 actual upload selection must carry exactly the tar and bound metadata'
    )
    with tarfile.open(ready / 'edi-native.tar') as archive:
        assert_native_archive(archive, expected)
    record = json.loads((ready / 'edi-native.json').read_text())
    assert record['source_sha'] == result[2] and record['platform'] == platform, (
        ' I34 producer metadata must bind the independent source and platform'
    )
    digest = hashlib.sha256((ready / 'edi-native.tar').read_bytes()).hexdigest()
    assert record.get('tar_sha256', record.get('sha256')) == digest, (
        ' I34 producer metadata must bind the actual selected tar bytes'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.usefixtures('private_native_workflow')
def test_native_actual_producer_upload_preserves_the_addressed_package_operation(
    tmp_path, platform
):
    for defect in (None, 'resource', 'operation'):
        folder = tmp_path / str(defect)
        folder.mkdir()
        native_producer(folder, platform, defect)


def assert_native_archive(archive, expected):
    members = [
        m for m in archive.getmembers() if m.isfile() and not m.name.endswith('.edi-native.json')
    ]
    got = {
        'build/ci/' + m.name.removeprefix('./').removeprefix('build/ci/'): archive.extractfile(
            m
        ).read()
        for m in members
    }
    assert len(got) == len(members), (
        ' I34 distinct archive members must never alias after prefix conversion'
    )
    assert got == expected, ' I34 producer archive must preserve independently planted bytes'
    executable = next(
        m
        for m in archive.getmembers()
        if m.name.removeprefix('./').removeprefix('build/ci/') == 'core/edi_tests'
    )
    assert executable.mode & 0o111, (
        ' I34 producer tar must retain executable native test permissions'
    )


@pytest.mark.parametrize('prefix', ['build/ci/', './'])
def test_native_archive_prefix_conversion_refuses_a_second_address_for_one_member(
    tmp_path, prefix
):
    expected = {'build/ci/core/edi_tests': b'independent nontrivial native test bytes\x17'}
    for defect in (None, 'resource', 'duplicate'):
        file = tmp_path / (str(defect) + '.tar')
        with tarfile.open(file, 'w') as out:
            names = [prefix + 'core/edi_tests']
            if defect == 'resource':
                names = [prefix + 'core/foreign_tests']
            elif defect == 'duplicate':
                names.append('core/edi_tests' if prefix == './' else './build/ci/core/edi_tests')
            for name in names:
                data = next(iter(expected.values()))
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o755
                out.addfile(member, io.BytesIO(data))
        with tarfile.open(file) as archive:
            if defect is None:
                assert_native_archive(archive, expected)
            else:
                with pytest.raises(AssertionError, match=' I34'):
                    assert_native_archive(archive, expected)
