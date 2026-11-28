# SPDX-License-Identifier: BSD-3-Clause
"""The macOS maintenance tool swap an update runs (edi ADR-0106), in a scratch folder.

maintenance_swap.sh must leave a tool in place whatever fails, keep the installed bundle until
the update has succeeded, and run again after any interruption; maintenance_restore.sh, its undo,
puts the kept bundle back, only in the run that kept it. Qt IFW saves the operation and, in the
next update, undoes it before it unpacks the component again: that undo must change nothing.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'tools/installer'
SWAP = FOLDER / 'maintenance_swap.sh'
RESTORE = FOLDER / 'maintenance_restore.sh'
OPERATION = 'this-update'  # the swap operation's own mark

# The swap is macOS's; its shell runs on any POSIX system, never on Windows.
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='a POSIX shell script')


def bundle(path: Path, text: str) -> None:
    executable = path / 'Contents/MacOS/MaintenanceTool'
    executable.parent.mkdir(parents=True)
    executable.write_text(text)


def tool(path: Path) -> str | None:
    executable = path / 'Contents/MacOS/MaintenanceTool'
    return executable.read_text() if executable.exists() else None


def run(script: Path, target: Path, env: dict | None = None, token: str = OPERATION) -> int:
    command = ['/bin/sh', str(script), str(target), token]
    return subprocess.run(command, env=env, check=False).returncode


# One maintenance tool run: a process of its own that runs its steps in turn, as the tool runs an
# operation and its undo. The scripts mark the backup with this process; another run is another.
SESSION = (
    'import json, subprocess, sys\n'
    'for command, env in json.loads(sys.argv[1]):\n'
    '    print(subprocess.run(command, env=env, check=False).returncode)\n'
)


def session(target: Path, *steps: tuple) -> list[int]:
    """Run (script, token[, env]) steps in one tool run; their exit codes."""
    commands = [
        [['/bin/sh', str(step[0]), str(target), step[1]], step[2] if len(step) > 2 else None]
        for step in steps
    ]
    result = subprocess.run(
        [sys.executable, '-c', SESSION, json.dumps(commands)],
        capture_output=True,
        text=True,
        check=True,
    )
    return [int(code) for code in result.stdout.split()]


def mv_shim(folder: Path, action: str) -> dict:
    """A PATH whose mv runs `action` instead of renaming the new tool into place."""
    (folder / 'mv').write_text(
        f'#!/bin/sh\ncase "$1" in *.app.new) {action} ;; esac\nexec /bin/mv "$@"\n'
    )
    (folder / 'mv').chmod(0o755)
    return {'PATH': f'{folder}:/usr/bin:/bin'}


# Stopped between the two renames: the swap's own shell is killed there.
STOPPED = 'kill -9 $PPID; exit 1'


@pytest.fixture
def installed(tmp_path: Path) -> Path:
    bundle(tmp_path / 'MaintenanceTool.app', 'installed')
    return tmp_path


def test_a_swap_puts_the_new_tool_in_place_and_keeps_the_installed_one(installed: Path) -> None:
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    assert run(SWAP, installed) == 0
    assert tool(installed / 'MaintenanceTool.app') == 'new'
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed', (
        'kept until the update succeeds'
    )
    assert not (installed / 'maintenancetool').exists()
    assert not (installed / 'MaintenanceTool.app.new').exists()


def test_its_undo_puts_the_installed_tool_back(installed: Path) -> None:
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    assert run(SWAP, installed) == 0
    assert run(RESTORE, installed) == 0
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert not (installed / 'MaintenanceTool.app.old').exists()


def test_a_rerun_after_the_new_tool_was_moved_aside_finishes_the_swap(installed: Path) -> None:
    bundle(installed / 'MaintenanceTool.app.new', 'new')
    assert run(SWAP, installed) == 0
    assert tool(installed / 'MaintenanceTool.app') == 'new'
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed'


def test_a_rerun_after_a_stop_between_the_renames_finishes_the_swap(
    installed: Path, tmp_path_factory
) -> None:
    stop = mv_shim(tmp_path_factory.mktemp('shims'), STOPPED)
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    codes = session(installed, (SWAP, OPERATION, stop), (SWAP, OPERATION))
    assert codes[0] != 0 and codes[1] == 0
    assert tool(installed / 'MaintenanceTool.app') == 'new'
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed', 'its own backup is kept'


def test_a_failed_last_rename_puts_the_installed_tool_back(
    installed: Path, tmp_path_factory
) -> None:
    # An mv that refuses only the rename of the new tool into place.
    env = mv_shim(tmp_path_factory.mktemp('shims'), 'exit 1')
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    assert run(SWAP, installed, env) == 1
    assert tool(installed / 'MaintenanceTool.app') == 'installed', 'never left without a tool'


def test_a_backup_an_earlier_update_left_is_dropped_not_restored(installed: Path) -> None:
    # An update run by an older control script never removed its backup.
    bundle(installed / 'MaintenanceTool.app.old', 'two updates ago')
    (installed / 'MaintenanceTool.app.old-token').write_text('earlier-update\n')
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    assert run(SWAP, installed) == 0
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed', (
        'the stale backup is replaced'
    )
    assert run(RESTORE, installed) == 0
    assert tool(installed / 'MaintenanceTool.app') == 'installed'


def test_an_undo_never_restores_a_backup_it_did_not_keep(installed: Path) -> None:
    bundle(installed / 'MaintenanceTool.app.old', 'two updates ago')
    (installed / 'MaintenanceTool.app.old-token').write_text('earlier-update\n')
    bundle(installed / 'MaintenanceTool.app.new', 'another attempt')
    assert run(RESTORE, installed) == 0
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert tool(installed / 'MaintenanceTool.app.new') == 'another attempt', 'not its own'


# Two updates in a row from an installed 2026.11.31, as Qt IFW runs them: the first update's
# operation is saved, and the next update undoes it before it unpacks the component again.


def first_update(target: Path, controller: str) -> None:
    """The first update succeeds; the released controller keeps the backup, newer ones drop it."""
    bundle(target / 'maintenancetool/MaintenanceTool.app', 'first')
    assert session(target, (SWAP, 'first-update')) == [0]
    if controller == 'newer':
        for name in ('MaintenanceTool.app.old', 'MaintenanceTool.app.old-token'):
            subprocess.run(['/bin/rm', '-rf', str(target / name)], check=True)
    assert tool(target / 'MaintenanceTool.app') == 'first'


def test_an_update_rolled_back_from_the_released_tool_puts_it_back(installed: Path) -> None:
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'first')
    assert session(installed, (SWAP, 'first-update'), (RESTORE, 'first-update')) == [0, 0]
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert not (installed / 'MaintenanceTool.app.old').exists()


@pytest.mark.parametrize('controller', ['released', 'newer'])
def test_the_next_update_undoing_the_committed_swap_changes_nothing(
    installed: Path, controller: str
) -> None:
    first_update(installed, controller)
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'second')
    assert session(installed, (RESTORE, 'first-update'), (SWAP, 'second-update')) == [0, 0]
    assert tool(installed / 'MaintenanceTool.app') == 'second'
    assert tool(installed / 'MaintenanceTool.app.old') == 'first'


@pytest.mark.parametrize('controller', ['released', 'newer'])
def test_the_next_update_rolled_back_puts_the_first_updates_tool_back(
    installed: Path, controller: str
) -> None:
    first_update(installed, controller)
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'second')
    steps = (RESTORE, 'first-update'), (SWAP, 'second-update'), (RESTORE, 'second-update')
    assert session(installed, *steps) == [0, 0, 0]
    assert tool(installed / 'MaintenanceTool.app') == 'first'


# An update stopped between the two renames leaves the backup as the only tool, and Qt IFW saves
# none of its operations. Whatever runs next, that copy stays until a new tool is in place or it is
# put back.


def stopped_update(target: Path, shims: Path) -> None:
    bundle(target / 'maintenancetool/MaintenanceTool.app', 'new')
    assert session(target, (SWAP, 'stopped-update', mv_shim(shims, STOPPED)))[0] != 0
    assert tool(target / 'MaintenanceTool.app') is None
    assert tool(target / 'MaintenanceTool.app.old') == 'installed'


def test_a_new_operation_after_a_stop_keeps_the_only_tool_as_its_backup(
    installed: Path, tmp_path_factory
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'newer')
    assert session(installed, (SWAP, 'next-update')) == [0]
    assert tool(installed / 'MaintenanceTool.app') == 'newer'
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed'


def test_a_new_operation_after_a_stop_that_fails_puts_the_only_tool_back(
    installed: Path, tmp_path_factory
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'newer')
    refuse = mv_shim(tmp_path_factory.mktemp('refuse'), 'exit 1')
    assert session(installed, (SWAP, 'next-update', refuse)) == [1]
    assert tool(installed / 'MaintenanceTool.app') == 'installed'


def test_a_new_operation_after_a_stop_with_nothing_staged_puts_the_only_tool_back(
    installed: Path, tmp_path_factory
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    subprocess.run(['/bin/rm', '-rf', str(installed / 'MaintenanceTool.app.new')], check=True)
    assert session(installed, (SWAP, 'next-update')) == [1]
    assert tool(installed / 'MaintenanceTool.app') == 'installed'


def test_a_new_operation_after_a_stop_rolled_back_puts_the_only_tool_back(
    installed: Path, tmp_path_factory
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'newer')
    steps = (SWAP, 'next-update'), (RESTORE, 'next-update')
    assert session(installed, *steps) == [0, 0]
    assert tool(installed / 'MaintenanceTool.app') == 'installed'


# After such a stop the app is the only way back: on start, and before Maintenance or Update opens
# the tool, it puts the kept bundle back (restore_kept_maintenance_tool in
# app/src/desktop_updates.cpp, tested with the app). This copies its renames so that the update the
# user retries from the app runs on the folder the app leaves.


def app_restores_the_kept_tool(target: Path) -> None:
    cur = target / 'MaintenanceTool.app'
    kept, drop = target / 'MaintenanceTool.app.old', target / 'MaintenanceTool.app.drop'
    if tool(cur) is not None or tool(kept) is None:
        return
    shutil.rmtree(drop, ignore_errors=True)
    if cur.exists() or cur.is_symlink():
        cur.rename(drop)
    kept.rename(cur)
    (target / 'MaintenanceTool.app.old-token').unlink(missing_ok=True)
    shutil.rmtree(drop, ignore_errors=True)


@pytest.mark.parametrize('staged', ['newer', None])
def test_a_retried_update_after_the_app_put_the_tool_back_finishes(
    installed: Path, tmp_path_factory, staged: str | None
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    app_restores_the_kept_tool(installed)
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert not (installed / 'MaintenanceTool.app.old').exists()
    assert not (installed / 'MaintenanceTool.app.old-token').exists()
    assert tool(installed / 'MaintenanceTool.app.new') == 'new', 'left for the retried update'
    if staged:
        bundle(installed / 'maintenancetool/MaintenanceTool.app', staged)
    assert session(installed, (SWAP, 'retried-update')) == [0]
    assert tool(installed / 'MaintenanceTool.app') == (staged or 'new')
    assert tool(installed / 'MaintenanceTool.app.old') == 'installed'


def test_a_retried_update_after_the_app_put_the_tool_back_rolls_back(
    installed: Path, tmp_path_factory
) -> None:
    stopped_update(installed, tmp_path_factory.mktemp('shims'))
    app_restores_the_kept_tool(installed)
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'newer')
    steps = (SWAP, 'retried-update'), (RESTORE, 'retried-update')
    assert session(installed, *steps) == [0, 0]
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert not (installed / 'MaintenanceTool.app.old').exists()


def test_the_app_leaves_a_tool_in_place_alone(installed: Path) -> None:
    bundle(installed / 'MaintenanceTool.app.old', 'two updates ago')
    app_restores_the_kept_tool(installed)
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert tool(installed / 'MaintenanceTool.app.old') == 'two updates ago'


def test_nothing_staged_changes_nothing(installed: Path) -> None:
    assert run(SWAP, installed) == 1
    assert tool(installed / 'MaintenanceTool.app') == 'installed'
    assert not (installed / 'MaintenanceTool.app.old').exists()


def test_each_component_script_assigns_each_function_once() -> None:
    # A second assignment silently replaces the first (the swap once ran an older copy of itself).
    for script in FOLDER.glob('*.qs'):
        names = re.findall(
            r'^\s*(Component\.prototype\.\w+|Controller\.prototype\.\w+)\s*=',
            script.read_text(),
            re.MULTILINE,
        )
        repeated = sorted({name for name in names if names.count(name) > 1})
        assert not repeated, f'{script.name} assigns {repeated} more than once'


def test_the_packaged_script_carries_both_shell_scripts() -> None:
    spec = importlib.util.spec_from_file_location('package', FOLDER / 'package.py')
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    script = package.maintenance_script()
    assert '@EDI_SWAP_SCRIPT@' not in script and '@EDI_RESTORE_SCRIPT@' not in script
    assert 'maintenance_swap.sh' in script and 'MaintenanceTool.app.old' in script
