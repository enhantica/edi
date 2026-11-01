"""Exercise the actual local launcher using offline command transports."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
POISON = ('CONDA_PREFIX', 'PYTHONPATH', 'CC', 'CXX', 'CFLAGS', 'LDFLAGS', 'SDKROOT')


def executable(path, body):
    path.write_text('#!' + sys.executable + '\n' + body)
    path.chmod(0o755)


def namespace(tmp_path, installed):
    root = tmp_path / 'edi'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    dev = root / 'tools/dev'
    dev.mkdir()
    shutil.copy2(ROOT / 'tools/dev/app-with-crysta.sh', dev)
    native = tmp_path / 'native checkout'
    (native / 'include/crysta').mkdir(parents=True)
    (native / 'pixi.toml').write_text('[workspace]\nname="crysta"\n')
    (native / 'include/crysta/model.hpp').write_text('// admission witness\n')
    if installed:
        old = native / '.pixi/envs/cpp-ci/lib/python3.14/site-packages/crysta-1.dist-info'
        old.mkdir(parents=True)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    log = tmp_path / 'calls.jsonl'
    recorder = (
        'import json,os,pathlib,subprocess,sys\n'
        'name=pathlib.Path(sys.argv[0]).name\n'
        'args=sys.argv[1:]\n'
        f'with open({str(log)!r}, "a") as stream:\n'
        ' stream.write(json.dumps(dict(name=name,args=args,env=dict(os.environ)))+"\\n")\n'
    )
    executable(bin_dir / 'uname', 'print("Linux")\n')
    executable(bin_dir / 'git', 'print("transport-source")\n')
    executable(bin_dir / 'cmake', recorder)
    executable(
        bin_dir / 'pixi',
        recorder + 'if args[0]=="run":\n'
        ' env=dict(os.environ,MACOSX_DEPLOYMENT_TARGET="13.4")\n'
        ' command=args[args.index("bash"):]\n'
        ' sys.exit(subprocess.run(command,env=env,check=False).returncode)\n',
    )
    for name in ('app-build', 'app-run'):
        executable(scripts / (name + '.py'), recorder)
        (scripts / (name + '.sh')).write_text(
            'exec "' + sys.executable + '" "' + str(scripts / (name + '.py')) + '" "$@"\n'
        )
    env = {**os.environ, 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'], 'CI': ''}
    env.update(dict.fromkeys(POISON, 'must-not-cross-native-boundary'))
    env['CCACHE_DIR'] = str(tmp_path / 'cache')
    return root, native, log, env


def launch(namespace, *arguments):
    root, native, log, env = namespace
    result = subprocess.run(
        ['bash', str(root / 'tools/dev/app-with-crysta.sh'), str(native), *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result, calls


@pytest.mark.parametrize('installed', [False, True])
def test_local_launcher_uses_the_build_only_environment_through_sdk_and_app(tmp_path, installed):
    space = namespace(tmp_path, installed)
    result, calls = launch(space, '--project', 'path with spaces.edi')
    assert result.returncode == 0, 'The real launcher reaches the SDK/app chain: ' + result.stderr
    assert [call['name'] for call in calls] == [
        'pixi',
        'pixi',
        'cmake',
        'cmake',
        'cmake',
        'app-build.py',
        'app-run.py',
    ], 'Native install/configure/build/install finish before the normal app build and launch'
    _root, native, _log, env = space
    pixi = [call for call in calls if call['name'] == 'pixi']
    assert len(pixi) == 2, 'There is exactly one frozen install and one native run'
    assert [call['args'][0] for call in pixi] == ['install', 'run'], (
        'The frozen installation precedes the native execution entrypoint'
    )
    for call in pixi:
        args = call['args']
        assert args[args.index('-e') + 1] == 'cpp-toolchain', (
            'Both install and run select the build-only environment'
        )
        assert args[args.index('--manifest-path') + 1] == str(native / 'pixi.toml'), (
            'Both operations belong to the supplied native checkout'
        )
        assert not any(arg.startswith('--skip') for arg in args), (
            'Old editable-package presence cannot change installation'
        )
        assert not set(POISON) & call['env'].keys(), (
            'The native process receives a clean environment'
        )
        assert call['env']['CCACHE_DIR'] == env['CCACHE_DIR'], (
            'The declared cache survives cleaning'
        )
    assert '--frozen' in pixi[0]['args'], 'Installation uses the committed lock'
    assert '--as-is' in pixi[1]['args'], 'The native run does not perform a second installation'
    cmake = [call for call in calls if call['name'] == 'cmake']
    assert len(cmake) == 3, 'Configure/build/install are all exercised, without running tests'
    configure, build, install = [call['args'] for call in cmake]
    assert configure[configure.index('-B') + 1] == str(native / 'build/edi-local'), (
        'Configure owns the local native graph'
    )
    assert build[:2] == ['--build', configure[configure.index('-B') + 1]], (
        'Build uses the same configured native graph'
    )
    assert install[:2] == ['--install', configure[configure.index('-B') + 1]], (
        'Install uses the same built native graph'
    )
    assert configure[configure.index('-G') + 1] == 'Ninja', 'The native generator remains Ninja'
    assert '-DCMAKE_BUILD_TYPE=Release' in configure, 'The local SDK remains a Release build'
    assert '-DCRYSTA_LTO=OFF' in configure, 'The original local SDK LTO policy is retained'
    assert configure[configure.index('-S') + 1] == str(native), 'Configure uses the actual source'
    assert '-DCRYSTA_CXX_PACKAGE=ON' in configure, 'The native SDK package remains enabled'
    assert '-DCMAKE_OSX_DEPLOYMENT_TARGET=13.4' in configure, (
        'The native activation owns its floor'
    )
    assert build[build.index('--target') + 1 :] == ['crysta_core', 'crysta_cli'], (
        'Only the genuine core and CLI targets are selected'
    )
    prefix = native / 'build/edi-local/prefix'
    assert install[install.index('--prefix') + 1] == str(prefix), 'Install retains the local SDK'
    app = [call for call in calls if call['name'].startswith('app-')]
    assert [call['name'] for call in app] == ['app-build.py', 'app-run.py'], (
        'The SDK build is followed by the normal app build and launch'
    )
    assert app[0]['env']['EDI_CRYSTA_PREFIX'] == str(prefix), (
        'The app links the SDK just installed'
    )
    assert app[0]['env']['EDI_APP_TARGETS'] == 'edi_app', 'The normal app target stays selected'
    assert app[1]['args'] == ['--project', 'path with spaces.edi'], (
        'App arguments retain boundaries'
    )


def test_local_launcher_refuses_ci_before_installing(tmp_path):
    space = namespace(tmp_path, False)
    space[3]['CI'] = 'true'
    result, calls = launch(space)
    assert result.returncode != 0, 'CI cannot substitute a local checkout for the pinned SDK'
    assert not calls, 'CI refusal precedes every install, configure, build and app launch'
