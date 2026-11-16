"""Every product consumes one qualified SDK and packages its full runtime closure."""

import hashlib
import importlib
import importlib.util
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tests.fixtures.windows_native_sdk import make as make_windows
from tests.fixtures.windows_native_sdk import write_manifest as write_windows_manifest

ROOT = Path(__file__).resolve().parents[3]


def document(path):
    return yaml.safe_load((ROOT / path).read_text())


def test_all_installers_consume_their_platform_sdk_from_the_shared_producer():
    workflow = document('.github/workflows/installers.yml')['jobs']
    assert workflow['crysta-sdk']['uses'] == './.github/workflows/crysta-sdk.yml', (
        'Native product packaging delegates SDK production to the same qualified platform producer'
    )
    candidates = [job for job in workflow.values() if isinstance(job, dict) and 'steps' in job]
    consumers = [
        step
        for job in candidates
        for step in job['steps']
        if step.get('uses') == './.github/actions/crysta-sdk'
    ]
    assert len(consumers) == 1, 'The installer matrix has exactly one SDK acquisition boundary'
    platform = consumers[0]['with']['platform']
    for token in ('Windows', 'win-64', 'macOS', 'osx-arm64', 'linux-64'):
        assert token in platform, (
            'Every installer host selects its corresponding qualified SDK artifact'
        )


@pytest.fixture
def packaging(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools/installer'))
    runtime = importlib.import_module('native_runtime')
    cli = importlib.import_module('standalone_cli')
    wheel = importlib.import_module('python_wheel')
    spec = importlib.util.spec_from_file_location(
        'edi_packaging_builder', ROOT / 'tools/installer/build.py'
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return SimpleNamespace(runtime=runtime, cli=cli, wheel=wheel, builder=builder)


def runtime_world(tmp_path, packaging, monkeypatch):
    (prefix, _repo, manifest) = make_windows(tmp_path / 'sdk-input')
    binary = tmp_path / 'product/edi.exe'
    binary.parent.mkdir()
    binary.write_bytes(b'independent executable protocol, not scientific qualification')
    graph = {
        'edi.exe': ['VCOMP140.dll', 'KERNEL32.dll'],
        'vcomp140.dll': ['MSVCP140.dll'],
        'msvcp140.dll': ['ucrtbase.dll'],
    }
    monkeypatch.setattr(packaging.runtime, 'SYSTEM', 'windows')
    monkeypatch.setattr(packaging.runtime, 'dependencies', lambda image: graph[image.name.lower()])
    return (binary, prefix, manifest, graph)


def test_runtime_bundle_copies_only_the_transitive_manifest_qualified_closure(
    packaging, tmp_path, monkeypatch
):
    (binary, prefix, manifest, _graph) = runtime_world(tmp_path, packaging, monkeypatch)
    spare = prefix / 'bin/Unused.DLL'
    spare.write_bytes(b'independent unused qualified runtime')
    manifest['tested']['sha256']['bin/Unused.DLL'] = hashlib.sha256(spare.read_bytes()).hexdigest()
    write_windows_manifest(prefix, manifest)
    libraries = packaging.runtime.bundle_runtime(binary, prefix)
    assert {path.name for path in libraries} == {'VCOMP140.DLL', 'MSVCP140.dll'}, (
        'Bundling follows the entire required closure without copying unrelated qualified DLLs'
    )
    for path in libraries:
        assert path.read_bytes() == (prefix / 'bin' / path.name).read_bytes(), (
            'Every copied DLL retains its independently qualified SDK bytes'
        )
    assert not (binary.parent / 'Unused.DLL').exists(), (
        'The installed product carries only dependencies reached from its actual images'
    )


@pytest.mark.parametrize(
    'defect',
    [
        'changed-bytes',
        'unrecorded-runtime',
        'unsafe-manifest-path',
        'ambiguous-case',
        'unknown-dependency',
        'missing-transitive',
    ],
)
def test_runtime_bundle_refuses_unqualified_bytes_paths_and_dependency_escape(
    packaging, tmp_path, monkeypatch, defect
):
    (binary, prefix, manifest, graph) = runtime_world(tmp_path, packaging, monkeypatch)
    if defect == 'changed-bytes':
        (prefix / 'bin/VCOMP140.DLL').write_bytes(b'unqualified DLL')
    elif defect == 'unrecorded-runtime':
        (prefix / 'bin/Hidden.DLL').write_bytes(b'unrecorded DLL')
        graph['edi.exe'] = ['Hidden.DLL']
    elif defect == 'unsafe-manifest-path':
        manifest['tested']['sha256']['bin/../outside.dll'] = '0' * 64
    elif defect == 'ambiguous-case':
        manifest['tested']['sha256']['bin/vcomp140.dll'] = manifest['tested']['sha256'][
            'bin/VCOMP140.DLL'
        ]
    elif defect == 'unknown-dependency':
        graph['edi.exe'] = ['vendor-helper.dll']
    else:
        graph['vcomp140.dll'] = ['missing-transitive.dll']
    write_windows_manifest(prefix, manifest)
    with pytest.raises((RuntimeError, OSError)):
        packaging.runtime.bundle_runtime(binary, prefix)


@pytest.mark.parametrize(
    'name', ['C:\\producer\\VCOMP140.DLL', '../VCOMP140.DLL', '/producer/VCOMP140.DLL']
)
def test_extracted_windows_runtime_cannot_resolve_a_path_by_basename(
    packaging, tmp_path, monkeypatch, name
):
    (binary, prefix, _manifest, graph) = runtime_world(tmp_path, packaging, monkeypatch)
    for leaf in ('VCOMP140.DLL', 'MSVCP140.dll'):
        shutil.copy2(prefix / 'bin' / leaf, binary.parent / leaf)
    graph['edi.exe'] = [name]
    with pytest.raises(RuntimeError):
        packaging.runtime.verify_dependencies(binary)


def test_cli_and_wheel_use_the_supplied_sdk_without_engine_source_build(
    packaging, tmp_path, monkeypatch
):
    (prefix, _repo, _manifest) = make_windows(tmp_path / 'sdk-input')
    work = tmp_path / 'work'
    source = work / 'cli-build/cli'
    source.mkdir(parents=True)
    (source / 'easydiffraction.exe').write_bytes(b'independent CLI transport')
    (source / 'LICENSE').write_text('independent notice')
    (source / 'licenses').mkdir()
    (source / 'licenses/NOTICE').write_text('runtime notices')
    commands = []
    bundles = []
    wheels = []
    qualified = []
    monkeypatch.setattr(packaging.cli, 'SYSTEM', 'windows')
    runtime_package(tmp_path / 'notice-input', packaging, monkeypatch)
    monkeypatch.setattr(
        packaging.cli, 'run', lambda args, **_kw: commands.append([str(a) for a in args])
    )

    def bundle(binary, sdk):
        bundles.append((binary, sdk))
        shutil.copy2(prefix / 'bin/VCOMP140.DLL', binary.parent / 'VCOMP140.DLL')
        return [binary.parent / 'VCOMP140.DLL']

    monkeypatch.setattr(packaging.cli, 'bundle_runtime', bundle)
    monkeypatch.setattr(packaging.cli, 'qualify_cli', lambda *args: qualified.append(args))
    monkeypatch.setattr(packaging.cli, 'build_wheel', lambda *args: wheels.append(args))
    packaging.cli.build_cli(prefix, work, ['-G', 'Ninja'], '2026.1.1', 'a7' * 20, 'win-64')
    configurations = [row for row in commands if '-S' in row]
    assert len(configurations) == 1 and configurations[0][
        configurations[0].index('-S') + 1
    ] == str(ROOT), 'CLI packaging configures only the Edi host and never configures Crysta source'
    assert '-DCMAKE_PREFIX_PATH=' + prefix.as_posix() in configurations[0], (
        'The CLI links the exact supplied SDK prefix used by the desktop product'
    )
    assert all('crysta_core' not in row and 'crysta_cli' not in row for row in commands), (
        'No CLI or wheel boundary may trigger an engine compilation target'
    )
    assert bundles[0][1] == wheels[0][-1] == prefix, (
        'Runtime bundling and Python-wheel compilation receive that identical qualified SDK'
    )
    assert len(qualified) == 1, (
        'The shipped CLI archive still crosses its actual qualification boundary'
    )
    archive = work / 'EasyDiffraction-2026.1.1-win-64-cli.zip'
    with zipfile.ZipFile(archive) as packed:
        assert {'edi.exe', 'VCOMP140.DLL', 'LICENSE', 'licenses/NOTICE'} <= set(
            packed.namelist()
        ), 'The standalone archive carries its executable, required runtime and existing notices'


def test_desktop_and_cli_configure_the_same_sdk_without_recompiling_crysta(
    packaging, tmp_path, monkeypatch
):
    source = tmp_path / 'crysta-source'
    (source / 'include/crysta').mkdir(parents=True)
    (source / 'include/crysta/model.hpp').write_text('independent source identity transport')
    work = tmp_path / 'work'
    work.mkdir()
    prefix = tmp_path / 'qualified-sdk'
    prefix.mkdir()
    qt = tmp_path / 'qt'
    qt.mkdir()
    commands = []
    cli_prefixes = []
    monkeypatch.setattr(packaging.builder, 'resolve_qt_prefix', lambda _qt: qt)
    monkeypatch.setattr(packaging.builder, 'acquire_sdk', lambda _source: prefix)
    monkeypatch.setattr(
        packaging.builder,
        'release_identity',
        lambda *_args: {'version': '2026.1.1', 'plan': None, 'commit': 'a7' * 20},
    )
    monkeypatch.setattr(
        packaging.builder, 'write_preview_history', lambda *_args: work / 'history.json'
    )
    monkeypatch.setattr(packaging.cli, 'build_cli', lambda sdk, *_args: cli_prefixes.append(sdk))

    class HostCompiledError(Exception):
        pass

    def run(args, **_kwargs):
        row = [str(a) for a in args]
        commands.append(row)
        if '--build' in row:
            raise HostCompiledError

    monkeypatch.setattr(packaging.builder, 'run', run)
    with pytest.raises(HostCompiledError):
        packaging.builder.build(source, work, qt, None, '2026.1.1')
    configure = next(row for row in commands if '-S' in row)
    assert configure[configure.index('-S') + 1] == str(ROOT), (
        'Desktop packaging configures the Edi host rather than another engine tree'
    )
    assert f'-DCMAKE_PREFIX_PATH={prefix.as_posix()};{qt.as_posix()}' in configure, (
        'Desktop links the same actual SDK package before its separate Qt host dependency'
    )
    assert cli_prefixes == [prefix], 'The desktop coordinator gives the CLI that same SDK instance'
    assert all(str(source) not in row and 'crysta_core' not in row for row in commands), (
        'No desktop coordinator command can configure or compile Crysta a second time'
    )


def runtime_package(tmp_path, packaging, monkeypatch, system='windows'):
    prefix = tmp_path / 'locked-environment'
    records = prefix / 'conda-meta'
    records.mkdir(parents=True)
    cached = tmp_path / 'actual-package-cache'
    licenses = cached / 'info/licenses'
    licenses.mkdir(parents=True)
    (licenses / 'LICENSE').write_bytes(b'independent actual package notice\n')
    name = {'windows': 'VCOMP140.DLL', 'linux': 'libgomp.so.1', 'macos': 'libomp.dylib'}[system]
    relative = ('Library/bin/' if system == 'windows' else 'lib/') + name
    record = {'name': 'runtime-owner', 'files': [relative], 'link': {'source': str(cached)}}
    import json  # noqa: PLC0415 - opaque package ownership protocol

    (records / 'runtime-owner.json').write_text(json.dumps(record), encoding='utf-8')
    monkeypatch.setenv('CONDA_PREFIX', str(prefix))
    monkeypatch.setattr(packaging.runtime, 'SYSTEM', system)
    return prefix, record, tmp_path / name


@pytest.mark.parametrize('system', ['windows', 'linux', 'macos'])
def test_each_packaged_runtime_carries_its_actual_owned_package_notices(
    packaging, tmp_path, monkeypatch, system
):
    _prefix, _record, library = runtime_package(tmp_path, packaging, monkeypatch, system)
    notices = tmp_path / 'notices'
    assert packaging.runtime.runtime_notices([library], notices) == notices, (
        'All native products collect notices through the first shared package-ownership algorithm'
    )
    assert (
        notices / 'runtime-owner/LICENSE'
    ).read_bytes() == b'independent actual package notice\n', (
        'The collected notice is the actual deployed runtime package license, byte for byte'
    )
    import package  # noqa: PLC0415 - first-owner compatibility contract

    assert packaging.builder.deployed_package_names is package.deployed_package_names, (
        'The original desktop package ownership API delegates to the shared first implementation'
    )


@pytest.mark.parametrize('damage', ['unowned', 'ambiguous', 'empty-license', 'missing-records'])
def test_runtime_notices_refuse_unowned_ambiguous_or_unlicensed_bundled_bytes(
    packaging, tmp_path, monkeypatch, damage
):
    prefix, record, library = runtime_package(tmp_path, packaging, monkeypatch)
    import json  # noqa: PLC0415

    records = prefix / 'conda-meta'
    if damage == 'unowned':
        record['files'] = ['Library/bin/other.dll']
        (records / 'runtime-owner.json').write_text(json.dumps(record), encoding='utf-8')
    elif damage == 'ambiguous':
        record['name'] = 'second-owner'
        (records / 'second-owner.json').write_text(json.dumps(record), encoding='utf-8')
    elif damage == 'empty-license':
        (Path(record['link']['source']) / 'info/licenses/LICENSE').unlink()
    else:
        shutil.rmtree(records)
    with pytest.raises(RuntimeError, match=r'ownership|licence|records'):
        packaging.runtime.runtime_notices([library], tmp_path / 'notices')


def test_wheel_carries_nested_runtime_notices_and_hashes_every_one_in_record(
    packaging, tmp_path, monkeypatch
):
    import base64  # noqa: PLC0415
    import csv  # noqa: PLC0415
    import io  # noqa: PLC0415

    monkeypatch.setattr(packaging.wheel, 'SYSTEM', 'windows')
    monkeypatch.setattr(packaging.runtime, 'SYSTEM', 'windows')
    extension = tmp_path / 'module/_edi.pyd'
    extension.parent.mkdir()
    extension.write_bytes(b'independent module transport, not scientific qualification')
    (extension.parent / 'VCOMP140.DLL').write_bytes(b'independent qualified runtime bytes')
    notices = tmp_path / 'notices/runtime-owner/nested'
    notices.mkdir(parents=True)
    expected = b'independent runtime attribution\n'
    (notices / 'LICENSE').write_bytes(expected)
    asset = tmp_path / 'independent.whl'
    packaging.wheel.write_wheel(
        asset, extension, '2026.1.1', 'cp312-abi3-win_amd64', tmp_path / 'notices'
    )
    root = 'easydiffraction-2026.1.1.dist-info'
    member = root + '/licenses/native/runtime-owner/nested/LICENSE'
    with zipfile.ZipFile(asset) as archive:
        assert archive.read(member) == expected, (
            'Wheel notices retain their full nested paths and actual bytes'
        )
        record = {
            row[0]: row[1:]
            for row in csv.reader(io.StringIO(archive.read(root + '/RECORD').decode()))
        }
        for name in [member, 'edi/VCOMP140.DLL', 'edi/_edi.pyd']:
            data = archive.read(name)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
            assert record[name] == ['sha256=' + digest, str(len(data))], (
                'Every installed native binary and runtime notice is covered by the wheel RECORD'
            )


@pytest.mark.parametrize('system', ['linux', 'macos', 'windows'])
def test_shared_process_qualification_uses_outer_locked_python_and_exact_installed_wheel(
    packaging, tmp_path, monkeypatch, system
):
    import sys  # noqa: PLC0415

    monkeypatch.setattr(packaging.wheel, 'SYSTEM', system)
    python = tmp_path / 'isolated-venv/python'
    installed = tmp_path / 'isolated-venv/site-packages'
    project = tmp_path / 'scientific-project'
    calls = []

    def purelib(command, **kwargs):
        assert command[0] == python, (
            'Only the isolated venv interpreter answers its installed purelib path'
        )
        assert kwargs['env'] == {'LOCKED': 'environment'}, (
            'Purelib discovery uses the exact qualifier environment'
        )
        return str(installed) + '\n'

    monkeypatch.setattr(packaging.wheel.subprocess, 'check_output', purelib)
    monkeypatch.setattr(
        packaging.wheel, 'run', lambda command, **kwargs: calls.append((command, kwargs))
    )
    packaging.wheel.qualify_shared_process(
        python, project, 'a7' * 20, {'LOCKED': 'environment'}, tmp_path
    )
    orders = ['zmq', 'edi'] if system == 'windows' else ['system', 'zmq', 'edi']
    assert [command[-1] for command, _ in calls] == orders, (
        'Qualification exercises both PyZMQ load orders and the applicable system runtime preload'
    )
    for command, kwargs in calls:
        assert command[:3] == [sys.executable, '-I', '-c'], (
            'The locked outer interpreter supplies PyZMQ while user path injection stays disabled'
        )
        assert command[4:] == [str(installed), project, 'a7' * 20, command[-1]], (
            'Only the installed wheel path and exact project/source identity reach the child'
        )
        assert kwargs['env'] == {'LOCKED': 'environment'} and kwargs['cwd'] == tmp_path, (
            'Every load order uses the same clean qualifier process environment'
        )
        assert_shared_process_program(command[3])


def assert_shared_process_program(program):
    import ast  # noqa: PLC0415 - inspect executable child syntax rather than comments

    tree = ast.parse(program)
    calls = {ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assertions = {
        ast.unparse(node.test) for node in ast.walk(tree) if isinstance(node, ast.Assert)
    }
    for call in [
        'p.calculate()',
        'zmq.Context()',
        'ctypes.CDLL(runtime, mode=ctypes.RTLD_GLOBAL)',
    ]:
        assert call in calls, 'Each real child executes its calculation and loaded native runtime'
    assert 'edi.__build_commit__ == sys.argv[3]' in assertions, (
        'Each real child proves exact wheel source identity'
    )
    assert (
        'Path(edi.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())' in assertions
    ), 'The imported package must originate in the freshly installed wheel directory'
    assert 'len(p.experiments[0].data.intensity_calc) > 0' in assertions, (
        'Each real load-order child calculates a nonempty scientific result'
    )


@pytest.mark.parametrize('kind', ['dynamic-runtime', 'strong-runtime-symbol', 'weak-templates'])
def test_linux_module_keeps_its_cxx_runtime_private(packaging, tmp_path, monkeypatch, kind):
    extension = tmp_path / '_edi.abi3.so'
    extension.write_bytes(b'independent inspector dispatch only')
    monkeypatch.setattr(
        packaging.wheel,
        'dependencies',
        lambda _image: ['libstdc++.so.6'] if kind == 'dynamic-runtime' else ['libc.so.6'],
    )
    monkeypatch.setattr(
        packaging.wheel.subprocess,
        'check_output',
        lambda *_args, **_kwargs: (
            '0000 T _ZNSt6runtime\n'
            if kind == 'strong-runtime-symbol'
            else '0000 W _ZNSt8template\n'
        ),
    )
    if kind == 'weak-templates':
        packaging.wheel.private_runtime(extension)
    else:
        with pytest.raises(RuntimeError, match='runtime'):
            packaging.wheel.private_runtime(extension)
