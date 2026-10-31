"""Exercise the real web build script with offline compiler transports."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def build_namespace(tmp_path):
    tmp_path = tmp_path.resolve()
    root = tmp_path / 'edi'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    for name in ('wasm-build.sh', 'wasm-env.sh'):
        shutil.copy2(ROOT / 'tools/ci' / name, scripts / name)
    source = root / 'build/crysta-src'
    source.mkdir(parents=True)
    (source / 'CRYSTA_SOURCE_SHA').write_text('a' * 40)
    tools = tmp_path / 'toolchain'
    emsdk = tools / 'emsdk-4.0.7'
    bin_dir = emsdk / 'bin'
    bin_dir.mkdir(parents=True)
    (emsdk / '.edi-installed').write_text('4.0.7\n')
    (emsdk / 'emsdk_env.sh').write_text('export PATH="' + str(bin_dir) + ':$PATH"\n')
    (tools / 'eigen-3.4.0/share/eigen3/cmake').mkdir(parents=True)
    transport = """import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['BUILD_CALLS'], 'a') as stream:
    names = ['CONDA_PREFIX','CC','CXX','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS',
             'DEBUG_CFLAGS','DEBUG_CXXFLAGS','DEBUG_CPPFLAGS',
             'CMAKE_CXX_COMPILER_LAUNCHER','CMAKE_C_COMPILER_LAUNCHER']
    record = dict(name=name,args=args,cwd=os.getcwd(),
                  executable=str(pathlib.Path(sys.argv[0]).resolve()),
                  env={k:os.environ[k] for k in names if k in os.environ})
    stream.write(json.dumps(record) + '\\n')
if name == 'emcc':
    print('4.0.7')
if '-B' in args:
    out = pathlib.Path(args[args.index('-B') + 1])
    (out / 'app').mkdir(parents=True, exist_ok=True)
    (out / 'app/edi_app.wasm').write_bytes(b'\\0asm\\1\\0\\0\\0')
    cache = out / 'CMakeCache.txt'
    if os.environ.get('EDI_TEST_WASM_DROP_GRAPH') == ('app' if name == 'qt-cmake.py' else 'core'):
        cache.unlink(missing_ok=True)
    else:
        prefix = next((a.split('=',1)[1] for a in args
                       if a.startswith('-DCMAKE_INSTALL_PREFIX=')),None)
        cache.write_text(json.dumps(dict(install=prefix)))
if name == 'cmake' and args and args[0] in ['--build','--install']:
    graph = pathlib.Path(args[1])
    cache = graph / 'CMakeCache.txt'
    if not cache.is_file():
        print('transport: missing configured graph',file=sys.stderr)
        sys.exit(71)
    if args[0] == '--install':
        prefix = pathlib.Path(json.loads(cache.read_text())['install'])
        (prefix / 'lib/cmake/crysta').mkdir(parents=True,exist_ok=True)
for arg in args:
    if arg.startswith('-DCMAKE_INSTALL_PREFIX='):
        pathlib.Path(arg.split('=', 1)[1]).mkdir(parents=True, exist_ok=True)
"""
    for name in ('emcc', 'emcmake', 'cmake'):
        executable = bin_dir / name
        executable.write_text('#!' + sys.executable + '\n' + transport)
        executable.chmod(0o755)
    for mode in ('singlethread', 'multithread'):
        kit = tools / 'qt/6.11.2' / ('wasm_' + mode)
        (kit / 'lib/cmake/Qt6').mkdir(parents=True)
        (kit / 'lib/cmake/Qt6/QtPublicWasmToolchainHelpers.cmake').write_text(
            'set(QT_EMCC_RECOMMENDED_VERSION "4.0.7")\n'
        )
        (kit / 'bin').mkdir()
        stub = kit / 'bin/qt-cmake.py'
        stub.write_text(transport)
        (kit / 'bin/qt-cmake').write_text(
            'exec "' + sys.executable + '" "' + str(stub) + '" "$@"\n'
        )
    pack = scripts / 'wasm-pack.py'
    pack.write_text(
        'import json,os\n'
        "with open(os.environ['BUILD_CALLS'],'a') as f:\n"
        " f.write(json.dumps({'name':'pack','args':[],'cwd':os.getcwd()})+'\\n')\n"
    )
    (scripts / 'wasm-pack.sh').write_text('exec "' + sys.executable + '" "' + str(pack) + '"\n')
    calls = tmp_path / 'calls.jsonl'
    env = {
        **os.environ,
        'EDI_WASM_TOOLCHAIN': str(tools),
        'CONDA_PREFIX': str(tmp_path / 'host'),
        'BUILD_CALLS': str(calls),
        'EDI_WASM_CRYSTA_SRC': '',
    }
    env.pop('EDI_TEST_WASM_DROP_GRAPH', None)
    return root, scripts, env, calls


def run_build(namespace, modes):
    root, scripts, env, calls = namespace
    calls.unlink(missing_ok=True)
    result = subprocess.run(
        ['bash', str(scripts / 'wasm-build.sh'), *modes],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    captured = (
        [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    )
    return result, captured


@pytest.fixture(scope='module')
def build_calls(tmp_path_factory):
    namespace = build_namespace(tmp_path_factory.mktemp('web-build-transports'))
    result, calls = run_build(namespace, ['multithread', 'singlethread'])
    assert result.returncode == 0, (
        'Both web kits must reach their actual build commands with offline compiler transports: '
        + result.stderr
    )
    return calls


def test_each_kit_selects_its_own_engine_backend_and_simd(build_calls):
    core = [call['args'] for call in build_calls if call['name'] == 'emcmake']
    assert len(core) == 2, 'The web build must independently configure both engine kits'
    for flags in core:
        threaded = any('/multithread/' in flag for flag in flags)
        assert '-DCRYSTA_OPENMP=OFF' in flags, 'Both web kits must keep native OpenMP disabled'
        assert '-DCRYSTA_SLEEF=ON' in flags, 'Every shipped web kit must select vector maths'
        assert '-DCRYSTA_WASM_THREADS=' + ('ON' if threaded else 'OFF') in flags, (
            'Only the multithread kit may require pthreads and shared memory'
        )
        assert '-DCRYSTA_WASM_SIMD=ON' in flags, 'Every shipped web kit must enable wasm SIMD'
        assert '-DCRYSTA_REQUIRE_SIMD=ON' in flags, (
            'Both shipped web kits must refuse configuration without their required SIMD backend'
        )


def test_app_pthread_pool_is_preallocated_and_sized_for_the_engine(build_calls):
    apps = [call['args'] for call in build_calls if call['name'] == 'qt-cmake.py']
    assert len(apps) == 2, 'Both Qt kits must configure through their actual kit launcher'
    threaded = next(flags for flags in apps if any('/multithread/' in flag for flag in flags))
    serial = next(flags for flags in apps if any('/singlethread/' in flag for flag in flags))
    text = ' '.join(threaded)
    assert 'PTHREAD_POOL_SIZE' in text, (
        'Multithread kit must preallocate enough pthread workers for its engine'
    )
    assert 'hardwareConcurrency' in text, (
        'Browser worker allocation must follow the device core count'
    )
    assert 'PTHREAD_POOL_SIZE' not in ' '.join(serial), (
        'The serial kit must remain runnable without browser shared memory or a pthread pool'
    )


def require_physical_build_calls(
    calls, namespace, physical, *, cached, modes=('multithread', 'singlethread')
):
    root, _scripts, env, _log = namespace
    build_events = [c for c in calls if c['name'] in {'emcmake', 'qt-cmake.py', 'cmake'}]
    expected = []
    for mode in modes:
        out = physical / mode
        if not cached:
            expected += [
                ('emcmake', '-B', out / 'crysta'),
                ('cmake', '--build', out / 'crysta'),
                ('cmake', '--install', out / 'crysta'),
            ]
        expected += [('qt-cmake.py', '-B', out / 'app'), ('cmake', '--build', out / 'app')]
    assert len(build_events) == len(expected), (
        'No configured/build/installed graph step is omitted or duplicated'
    )
    for call, (name, operation, graph) in zip(build_events, expected, strict=True):
        assert call['name'] == name, (
            'Both kits retain configure/build/install order and actual launchers'
        )
        args = call['args']
        graph_arg = args[args.index(operation) + 1]
        assert graph_arg == str(graph), (
            'Every CMake graph argument uses its actual physical per-kit directory'
        )
        assert str(Path(graph_arg).resolve()) == graph_arg, (
            'A logical alias is not a physical graph argument'
        )
        assert graph.is_dir() and (graph / 'CMakeCache.txt').is_file(), (
            'Each build/install uses an actually configured graph'
        )
        assert call['cwd'] == str(root.resolve()), (
            'The actual source working directory is preserved'
        )
        assert call['env'] == {}, (
            'Host compiler/launcher/Conda flags cannot leak into target configuration'
        )
        mode = graph.parent.name
        prefix = graph.parent / 'crysta-prefix'
        if name == 'emcmake':
            assert args[0] == 'cmake', 'The native engine still configures through emcmake/cmake'
            assert '-DCMAKE_INSTALL_PREFIX=' + str(prefix) in args, (
                'The install destination is the same physical kit prefix'
            )
            assert '-S' in args and args[args.index('-S') + 1] == str(root / 'build/crysta-src')
            required = {
                '-DCMAKE_BUILD_TYPE=Release',
                '-DCRYSTA_CXX_PACKAGE=ON',
                '-DCRYSTA_EIGEN_FETCH=ON',
                '-DCMAKE_DISABLE_FIND_PACKAGE_doctest=ON',
                '-DCRYSTA_OPENMP=OFF',
                '-DCRYSTA_SLEEF=ON',
                '-DCRYSTA_WASM_SIMD=ON',
                '-DCRYSTA_REQUIRE_SIMD=ON',
                '-DCRYSTA_WASM_THREADS=' + ('ON' if mode == 'multithread' else 'OFF'),
            }
            assert required <= set(args), (
                'Physical routing preserves native package/backend/ABI flags'
            )
        elif name == 'qt-cmake.py':
            assert {
                '-DCMAKE_BUILD_TYPE=Release',
                '-DEDI_BUILD_APP=ON',
                '-DEDI_BUILD_BINDINGS=OFF',
            } <= set(args), 'Target app mode stays unchanged'
            tools = Path(env['EDI_WASM_TOOLCHAIN'])
            assert call['executable'] == str(
                tools / 'qt/6.11.2' / ('wasm_' + mode) / 'bin/qt-cmake.py'
            ), 'Each app graph uses its own actual Qt kit launcher'
            assert '-Dcrysta_DIR=' + str(prefix / 'lib/cmake/crysta') in args, (
                'The app links its physical native prefix'
            )
            assert '-DQT_HOST_PATH=' + env['CONDA_PREFIX'] in args, (
                'The exact host prefix survives as a CMake argument'
            )
            assert '-DQT_HOST_PATH_CMAKE_DIR=' + env['CONDA_PREFIX'] + '/lib/cmake' in args
            assert '-DEigen3_DIR=' + str(tools / 'eigen-3.4.0/share/eigen3/cmake') in args
            if env.get('EDI_GUI_COMPONENTS_SRC'):
                assert (
                    '-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + env['EDI_GUI_COMPONENTS_SRC']
                    in args
                )
            assert (
                '-DEDI_WORKER_OWNER_THREAD=' + ('OFF' if mode == 'multithread' else 'ON') in args
            )
        else:
            assert args[0] == operation, (
                'A build/install graph cannot be routed through another operation'
            )
            if operation == '--build' and graph.name == 'app':
                assert args[2:] == ['--target', 'edi_app'], 'The actual target app is built'


@pytest.fixture(scope='module', params=['direct', 'symlink-parent'])
def physical_build_runs(request, tmp_path_factory):
    namespace = build_namespace(tmp_path_factory.mktemp('physical-web-' + request.param))
    root, _scripts, env, _log = namespace
    host = root.parent / 'host prefix'
    gui = root.parent / 'gui source'
    host.mkdir()
    gui.mkdir()
    env.update(CONDA_PREFIX=str(host), EDI_GUI_COMPONENTS_SRC=str(gui))
    physical = root / 'build/wasm' if request.param == 'direct' else root.parent / 'physical wasm'
    physical.mkdir()
    if request.param == 'symlink-parent':
        (root / 'build/wasm').symlink_to(physical, target_is_directory=True)
        assert (root / 'build/wasm').is_symlink(), (
            'The real alias escape is armed, not a copied directory'
        )
    assert not (physical / 'multithread').exists() and not (physical / 'singlethread').exists(), (
        'The first invocation really starts with cold per-kit graphs'
    )
    for name in [
        'CC',
        'CXX',
        'CFLAGS',
        'CXXFLAGS',
        'CPPFLAGS',
        'LDFLAGS',
        'DEBUG_CFLAGS',
        'DEBUG_CXXFLAGS',
        'DEBUG_CPPFLAGS',
        'CMAKE_CXX_COMPILER_LAUNCHER',
        'CMAKE_C_COMPILER_LAUNCHER',
    ]:
        env[name] = 'transport-host-only'
    first, cold = run_build(namespace, ['multithread', 'singlethread'])
    assert first.returncode == 0, 'Both cold kits must complete offline transport: ' + first.stderr
    keys = {
        mode: (physical / mode / 'crysta-prefix/.edi-wasm-key').read_bytes()
        for mode in ['multithread', 'singlethread']
    }
    second, warm = run_build(namespace, [])
    assert second.returncode == 0, (
        'The ordinary no-argument cached build reaches packaging: ' + second.stderr
    )
    return namespace, physical.resolve(), cold, warm, keys


@pytest.mark.parametrize('cached', [False, True])
def test_normal_wasm_graph_arguments_are_physical_for_both_kits(physical_build_runs, cached):
    namespace, physical, cold, warm, keys = physical_build_runs
    calls = warm if cached else cold
    require_physical_build_calls(calls, namespace, physical, cached=cached)
    pack = [i for i, call in enumerate(calls) if call['name'] == 'pack']
    assert pack == ([len(calls) - 1] if cached else []), (
        'Default both-kit invocation packs once after completion; explicit kits do not pack'
    )
    for mode, key in keys.items():
        path = physical / mode
        assert (path / 'crysta-prefix/.edi-wasm-key').read_bytes() == key, (
            'Cached graphs retain their exact engine key'
        )
        expected = (
            'crysta ' + 'a' * 40 + ' kit 6.11.2/' + mode + ' emsdk 4.0.7 eigen '
            '8586084f71f9bde545ee7fa6d00288b264a2b7ac3607b974e54d13e7162c1c72'
            ' fetched threads '
            + ('ON' if mode == 'multithread' else 'OFF')
            + ' simd ON sleef ON require-simd ON\n'
        )
        assert key == expected.encode(), (
            'Physical addressing does not change source/kit/Emscripten/Eigen/backend identity'
        )
        assert (path / 'app/app/CRYSTA_SOURCE_SHA').read_text() == 'a' * 40 + '\n'


@pytest.mark.parametrize(
    'seam',
    [
        'core-configure',
        'app-configure',
        'core-build',
        'core-install',
        'app-build',
        'install-prefix',
        'package-prefix',
    ],
)
def test_physical_graph_gate_refuses_each_logical_argument_escape(physical_build_runs, seam):
    namespace, physical, cold, _warm, _keys = physical_build_runs
    require_physical_build_calls(cold, namespace, physical, cached=False)
    changed = copy.deepcopy(cold)
    root = namespace[0]
    for call in changed:
        args = call['args']
        operation = (
            'emcmake'
            if seam in {'core-configure', 'install-prefix'}
            else 'qt-cmake.py'
            if seam in {'app-configure', 'package-prefix'}
            else 'cmake'
        )
        if call['name'] != operation:
            continue
        if operation == 'cmake' and (
            not args or args[0] != ('--install' if seam == 'core-install' else '--build')
        ):
            continue
        if seam == 'app-build' and Path(args[1]).name != 'app':
            continue
        if seam == 'core-build' and Path(args[1]).name != 'crysta':
            continue
        physical_mode = str(physical / 'multithread')
        logical_mode = str(root / 'build/wasm/multithread')
        if not (root / 'build/wasm').is_symlink():
            logical_mode = str(root / 'build/wasm/..' / 'wasm/multithread')
        # Even the direct layout gets a noncanonical lexical parent escape;
        # linked layout additionally crosses the real symlink boundary.
        if any(physical_mode in arg for arg in args):
            if seam == 'install-prefix':
                indexes = [
                    i for i, a in enumerate(args) if a.startswith('-DCMAKE_INSTALL_PREFIX=')
                ]
            elif seam == 'package-prefix':
                indexes = [i for i, a in enumerate(args) if a.startswith('-Dcrysta_DIR=')]
            else:
                indexes = [args.index('-B') + 1] if '-B' in args else [1]
            for index in indexes:
                args[index] = args[index].replace(physical_mode, logical_mode, 1)
            break
    assert changed != cold, 'Each argument counterfeit really reaches its actual command slot'
    with pytest.raises(AssertionError):
        require_physical_build_calls(changed, namespace, physical, cached=False)


@pytest.mark.parametrize('drop', ['core', 'app'])
def test_missing_actual_configuration_cannot_publish_an_app_or_pack(tmp_path, drop):
    namespace = build_namespace(tmp_path)
    namespace[2]['EDI_TEST_WASM_DROP_GRAPH'] = drop
    result, calls = run_build(namespace, [])
    assert result.returncode == 71, (
        'The actual attempted build refuses the missing graph at its transport boundary'
    )
    assert 'transport: missing configured graph' in result.stderr, (
        'The failure is the intended missing graph, not setup'
    )
    assert any(c['name'] == 'cmake' and c['args'][0] == '--build' for c in calls), (
        'The refusing build was actually attempted'
    )
    assert not any(c['name'] == 'pack' for c in calls), (
        'A missing graph never reaches normal publication'
    )
    assert not (namespace[0] / 'build/wasm/multithread/app/app/CRYSTA_SOURCE_SHA').exists(), (
        'An unsuccessful app build cannot receive the normal source-identity marker'
    )


def test_unknown_kit_refuses_before_any_configuration(tmp_path):
    namespace = build_namespace(tmp_path)
    result, calls = run_build(namespace, ['not-a-kit'])
    assert result.returncode != 0 and 'unknown build' in result.stderr, (
        'The original kit refusal stays visible'
    )
    assert [c['name'] for c in calls] == ['emcc'], (
        'The intended mode refusal happens before any CMake/kit/pack execution'
    )


@pytest.mark.parametrize('mode', ['multithread', 'singlethread'])
def test_explicit_individual_kit_keeps_its_own_physical_graph_and_no_pack(tmp_path, mode):
    namespace = build_namespace(tmp_path)
    root = namespace[0]
    physical = root.parent / 'physical wasm'
    physical.mkdir()
    (root / 'build/wasm').symlink_to(physical, target_is_directory=True)
    result, calls = run_build(namespace, [mode])
    assert result.returncode == 0, 'The individual public kit mode completes: ' + result.stderr
    require_physical_build_calls(calls, namespace, physical.resolve(), cached=False, modes=[mode])
    assert not any(c['name'] == 'pack' for c in calls), (
        'An explicit single kit does not publish the combined site'
    )
    other = 'singlethread' if mode == 'multithread' else 'multithread'
    assert not (physical / other).exists(), (
        'An explicit kit never configures or writes its sibling graph'
    )
