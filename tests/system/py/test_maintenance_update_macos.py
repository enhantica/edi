# SPDX-License-Identifier: BSD-3-Clause
"""The macOS tool's update and app recovery use the installed bundle boundary."""

import hashlib
import json
import os
import select
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.installer import package

if os.name == 'posix':
    import fcntl

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures/maintenance_update'
BUNDLE = 'MaintenanceTool.app'
EXECUTABLE = Path('Contents/MacOS/MaintenanceTool')
OLD_BYTES = b'#!/bin/sh\nprintf released-tool\\\\n\n'
NEW_BYTES = b'#!/bin/sh\nprintf updated-tool\\\\n\n'

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='The macOS swap uses POSIX tools')


def put_tool(folder, executable):
    path = folder / EXECUTABLE
    path.parent.mkdir(parents=True)
    path.write_bytes(executable)
    path.chmod(0o755)
    return path


@pytest.mark.parametrize('driver', ['2026.11.27', 'current'])
def test_success_removes_maintenance_tool_update_debris(tmp_path, driver):
    node = shutil.which('node') or ROOT / '.pixi/envs/app/bin/node'
    controller = (
        ROOT / 'tools/installer/Installer.qs'
        if driver == 'current'
        else FIXTURES / 'installer-2026.11.27.qs'
    )
    if driver != 'current':
        digest = hashlib.sha256(controller.read_bytes()).hexdigest()
        assert digest == '308d1b5dd51051da6a2720a2be6005501af55b0da96d51628fa97aeaec36086b', (
            'The legacy run must load the controller shipped in 2026.11.27'
        )
    target = tmp_path / 'install with spaces'
    staging = target / 'maintenancetool'
    installed = put_tool(target / BUNDLE, OLD_BYTES)
    put_tool(staging / BUNDLE, NEW_BYTES)
    (staging / '.DS_Store').write_bytes(b'Finder view metadata')
    meta = tmp_path / 'meta'
    meta.mkdir()
    package.write_maintenance_tool_metadata(meta, '26.18')
    for phase in ('swap', 'finish'):
        result = subprocess.run(
            [
                str(node),
                str(FIXTURES / 'ifw_update.mjs'),
                phase,
                str(target),
                str(controller),
                str(meta / 'maintenancescript.qs'),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
        assert result.returncode == 0, (
            'The update must complete through both the running controller and incoming component: '
            + result.stderr
        )
        for command in json.loads(result.stdout):
            if command[0] == '/usr/bin/xattr':
                continue
            action = subprocess.run(command, capture_output=True, timeout=5, check=False)
            assert action.returncode == 0, (
                'The shell action emitted by the update component or controller must succeed: '
                + action.stderr.decode()
            )
        if phase == 'swap':
            assert (target / f'{BUNDLE}.old' / EXECUTABLE).read_bytes() == OLD_BYTES, (
                'The original installed tool must remain recoverable until the update finishes'
            )
    assert installed.read_bytes() == NEW_BYTES, (
        'A successful update retains the newly installed tool'
    )
    debris = [target / f'{BUNDLE}.old', target / f'{BUNDLE}.old-token', staging]
    assert not any(path.exists() for path in debris), (
        'Success removes the kept tool, its mark and nonempty staging with either controller'
    )


@pytest.fixture(scope='module')
def maintenance_entry(tmp_path_factory):
    configured = os.environ.get('EDI_MAINTENANCE_QT_PREFIX')
    prefix = Path(configured) if configured else ROOT / '.pixi/envs/app'
    if not (prefix / 'lib/cmake/Qt6/Qt6Config.cmake').is_file():
        message = 'The native recovery probe needs the desktop Qt environment'
        if configured or os.environ.get('EDI_APP_TEST_RUNNER'):
            pytest.fail(message)
        pytest.skip(message)
    compiler = prefix / 'bin/c++'
    if not compiler.is_file():
        compiler = shutil.which('c++') or compiler
    build = tmp_path_factory.mktemp('maintenance-entry')
    cmake = str(prefix / 'bin/cmake')
    commands = [
        [
            cmake,
            '-S',
            str(FIXTURES),
            '-B',
            str(build),
            f'-DEDI_ROOT={ROOT}',
            f'-DCMAKE_PREFIX_PATH={prefix}',
            f'-DCMAKE_CXX_COMPILER={compiler}',
        ],
        [cmake, '--build', str(build), '--parallel', '2'],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=45)
        assert result.returncode == 0, (
            'The recovery probe must link and run the app update controller: '
            + result.stdout
            + result.stderr
        )
    return build / 'maintenance_entry'


def launch_tool(entry, installation):
    return subprocess.run(
        [str(entry), str(installation / BUNDLE / EXECUTABLE)],
        capture_output=True,
        text=True,
        check=False,
        timeout=4,
    )


def test_app_opens_the_kept_tool_after_a_stopped_swap(tmp_path, maintenance_entry):
    receipt = tmp_path / 'started'
    os.mkfifo(receipt)
    old = b'#!/bin/sh\nprintf launched > ' + shlex.quote(str(receipt)).encode() + b'\n'
    kept = put_tool(tmp_path / f'{BUNDLE}.old', old)
    pending = put_tool(tmp_path / f'{BUNDLE}.new', NEW_BYTES)
    mark = tmp_path / f'{BUNDLE}.old-token'
    mark.write_text('stopped-update\n', encoding='utf-8')
    with os.fdopen(os.open(receipt, os.O_RDONLY | os.O_NONBLOCK), 'rb') as stream:
        result = launch_tool(maintenance_entry, tmp_path)
        assert result.returncode == 0 and result.stdout.strip() == '1 1', (
            'The installed app recognizes the interrupted install and opens Maintenance normally: '
            + result.stderr
        )
        readable, _, _ = select.select([stream], [], [], 2)
        assert readable and stream.read() == b'launched', (
            'The restored executable itself runs when the user opens Maintenance'
        )
    assert (tmp_path / BUNDLE / EXECUTABLE).read_bytes() == old, (
        'The normal tool path must contain the kept release after an interruption'
    )
    assert not kept.exists() and not mark.exists() and pending.read_bytes() == NEW_BYTES, (
        'Recovery consumes the kept bundle and its mark and leaves the candidate for retry'
    )


def test_starting_app_during_live_swap_leaves_the_kept_bundle(tmp_path, maintenance_entry):
    kept = put_tool(tmp_path / f'{BUNDLE}.old', OLD_BYTES)
    pending = put_tool(tmp_path / f'{BUNDLE}.new', NEW_BYTES)
    mark = tmp_path / f'{BUNDLE}.old-token'
    driver = subprocess.run(
        ['/bin/sh', '-c', 'printf "%s " "$$"; TZ=UTC0 LC_ALL=C ps -o lstart= -p "$$"'],
        capture_output=True,
        text=True,
        check=True,
        timeout=3,
    )
    mark_text = 'interrupted-driver ' + driver.stdout
    mark.write_text(mark_text, encoding='utf-8')
    with (tmp_path / '.MaintenanceTool.lock').open('w') as swap:
        fcntl.flock(swap, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = launch_tool(maintenance_entry, tmp_path)
        assert result.returncode == 0 and result.stdout.strip() == '1 0', (
            'A live swap remains managed and the app defers its normal launch: ' + result.stderr
        )
        assert not (tmp_path / BUNDLE).exists() and kept.read_bytes() == OLD_BYTES, (
            'App startup must leave the kept bundle and empty destination to the current swap'
        )
        assert mark.read_text(encoding='utf-8') == mark_text, (
            'While the swap holds the lock, app startup must leave its ownership mark alone'
        )
        assert pending.read_bytes() == NEW_BYTES, 'The live swap keeps its pending replacement'
