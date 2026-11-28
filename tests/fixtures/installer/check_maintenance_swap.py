# SPDX-License-Identifier: BSD-3-Clause
"""The swap of the maintenance tool's own files an update runs (edi ADR-0109), in a scratch folder.

maintenance_swap.sh puts the item an update unpacked in place of the installed one: the macOS
bundle, or the Linux tool's Qt runtime. It must leave an item in place whatever fails, keep the
installed one until the update has succeeded, and run again after any interruption;
maintenance_restore.sh, its undo, puts the kept item back, only in the run that kept it. Qt IFW
saves the operation and, in the next update, undoes it before it unpacks the component again: that
undo must change nothing. Every script, maintenance_cleanup.sh too, runs under the lock the app
takes before it puts a kept tool back, so neither ever sees the other half way.
"""

import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

# The scripts run on macOS and Linux, never on Windows, which has no fcntl.
fcntl = pytest.importorskip('fcntl', reason='POSIX shell scripts')

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'tools/installer'
SWAP = FOLDER / 'maintenance_swap.sh'
RESTORE = FOLDER / 'maintenance_restore.sh'
CLEANUP = FOLDER / 'maintenance_cleanup.sh'
OPERATION = 'this-update'  # the swap operation's own mark
# Where the tool component unpacks the new item; releases before used maintenancetool/.
STAGING = 'maintenance-update'


@dataclass(frozen=True)
class Form:
    item: str  # the folder swapped in the installation folder
    probe: str  # the file inside it that makes it usable


FORMS = [
    Form('MaintenanceTool.app', 'Contents/MacOS/MaintenanceTool'),
    Form('installer-runtime', 'dependencies.json'),
]


@dataclass(frozen=True)
class Site:
    """An installation folder holding one form of the swapped item."""

    target: Path
    form: Form

    def path(self, suffix: str = '') -> Path:
        return self.target / f'{self.form.item}{suffix}'

    @property
    def staged(self) -> Path:
        return self.target / STAGING / self.form.item

    def put(self, path: Path, text: str) -> None:
        probe = path / self.form.probe
        probe.parent.mkdir(parents=True)
        probe.write_text(text)

    def tool(self, path: Path) -> str | None:
        probe = path / self.form.probe
        return probe.read_text() if probe.exists() else None

    def command(self, script: Path, token: str = OPERATION, mode: str = '') -> list[str]:
        # As maintenancescript.qs runs it: the text given to sh -c, with the same text as its name.
        text = script.read_text(encoding='utf-8')
        arguments = [self.form.item, self.form.probe]
        if script != CLEANUP:
            arguments = [token, *arguments]
        if mode:
            arguments.append(mode)
        return ['/bin/sh', '-c', text, text, str(self.target), *arguments]


def run(site: Site, script: Path, env: dict | None = None, token: str = OPERATION) -> int:
    return subprocess.run(site.command(script, token), env=env, check=False).returncode


# One maintenance tool run: a process of its own that runs its steps in turn, as the tool runs an
# operation and its undo. The scripts mark the backup with this process; another run is another.
SESSION = (
    'import json, subprocess, sys\n'
    'for command, env in json.loads(sys.argv[1]):\n'
    '    print(subprocess.run(command, env=env, check=False).returncode, flush=True)\n'
)


def session_command(site: Site, steps: tuple) -> list[str]:
    commands = [
        [site.command(step[0], step[1], *step[3:]), step[2] if len(step) > 2 else None]
        for step in steps
    ]
    return [sys.executable, '-c', SESSION, json.dumps(commands)]


def session(site: Site, *steps: tuple) -> list[int]:
    """Run (script, token[, env[, mode]]) steps in one tool run; their exit codes."""
    result = subprocess.run(
        session_command(site, steps), capture_output=True, text=True, check=True
    )
    return [int(code) for code in result.stdout.split()]


def mv_shim(folder: Path, action: str, renamed: str = '*.new') -> dict:
    """A PATH whose mv runs `action` instead of renaming a path matching `renamed`.

    The default matches the swap's rename of the new item into place; '*.old' matches the undo's
    rename of the kept item back.
    """
    (folder / 'mv').write_text(
        f'#!/bin/sh\ncase "$1" in {renamed}) {action} ;; esac\nexec /bin/mv "$@"\n'
    )
    (folder / 'mv').chmod(0o755)
    return {'PATH': f'{folder}:/usr/bin:/bin'}


# Stopped between the two renames: the swap's own shell is killed there.
STOPPED = 'kill -9 $PPID; exit 1'


class Paused:
    """A tool run whose step stops in its mv shim, between two renames, until released.

    The shim says so on the run's output and waits on a FIFO, so nothing sleeps: reading the
    output waits for the stop, or for the end of a run that never got there.
    """

    def __init__(self, site: Site, shims: Path, renamed: str, *steps: tuple, **popen) -> None:
        self.go = shims / 'go'
        os.mkfifo(self.go)
        env = mv_shim(shims, f'echo paused; read go < "{self.go}"', renamed)
        steps = tuple(step if len(step) > 2 else (*step, env) for step in steps)
        self.tool = subprocess.Popen(
            session_command(site, steps), stdout=subprocess.PIPE, text=True, **popen
        )
        self.codes = []
        for line in self.tool.stdout:
            if line.strip() == 'paused':
                break
            self.codes.append(int(line))
        else:
            raise AssertionError(f'the run ended before it stopped: {self.codes}')

    def release(self) -> list[int]:
        """Let the stopped step go on; the exit codes of every step, once the run has ended."""
        with self.go.open('w') as go:
            go.write('\n')
        return self.finish()

    def finish(self) -> list[int]:
        # The output ends once every process of the run, the tool's own included, has gone.
        self.codes += [int(line) for line in self.tool.stdout.read().split()]
        self.tool.wait()
        return self.codes


@pytest.fixture(params=FORMS, ids=[form.item for form in FORMS])
def installed(request, tmp_path: Path) -> Site:
    site = Site(tmp_path, request.param)
    site.put(site.path(), 'installed')
    return site


@pytest.fixture
def shims(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp('shims')


def test_a_swap_puts_the_new_tool_in_place_and_keeps_the_installed_one(installed: Site) -> None:
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    assert installed.tool(installed.path()) == 'new'
    assert installed.tool(installed.path('.old')) == 'installed', 'kept until the update succeeds'
    assert not (installed.target / STAGING).exists()
    assert not installed.path('.new').exists()


def test_a_swap_removes_whatever_else_is_left_in_the_staging_folder(installed: Site) -> None:
    # Finder writes a .DS_Store into a folder it shows, so the folder is not empty once the
    # staged item has left it.
    installed.put(installed.staged, 'new')
    (installed.target / STAGING / '.DS_Store').write_text('Finder')
    assert run(installed, SWAP) == 0
    assert installed.tool(installed.path()) == 'new'
    assert not (installed.target / STAGING).exists()


def test_a_first_installation_moves_the_staged_item_in(tmp_path: Path) -> None:
    site = Site(tmp_path, FORMS[1])
    site.put(site.staged, 'new')
    assert run(site, SWAP) == 0
    assert site.tool(site.path()) == 'new'
    assert not site.path('.old').exists()
    assert not (tmp_path / STAGING).exists()


def test_its_undo_puts_the_installed_tool_back(installed: Site) -> None:
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    assert run(installed, RESTORE) == 0
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()


def test_a_rerun_after_the_new_tool_was_moved_aside_finishes_the_swap(installed: Site) -> None:
    installed.put(installed.path('.new'), 'new')
    assert run(installed, SWAP) == 0
    assert installed.tool(installed.path()) == 'new'
    assert installed.tool(installed.path('.old')) == 'installed'


def test_a_rerun_after_a_stop_between_the_renames_finishes_the_swap(
    installed: Site, shims: Path
) -> None:
    stop = mv_shim(shims, STOPPED)
    installed.put(installed.staged, 'new')
    codes = session(installed, (SWAP, OPERATION, stop), (SWAP, OPERATION))
    assert codes[0] != 0 and codes[1] == 0
    assert installed.tool(installed.path()) == 'new'
    assert installed.tool(installed.path('.old')) == 'installed', 'its own backup is kept'


def test_a_failed_last_rename_puts_the_installed_tool_back(installed: Site, shims: Path) -> None:
    # An mv that refuses only the rename of the new tool into place.
    env = mv_shim(shims, 'exit 1')
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP, env) == 1
    assert installed.tool(installed.path()) == 'installed', 'never left without a tool'
    assert not (installed.target / STAGING).exists(), 'no empty staging folder'


def test_a_backup_an_earlier_update_left_is_dropped_not_restored(installed: Site) -> None:
    # An update run by an older control script never removed its backup.
    installed.put(installed.path('.old'), 'two updates ago')
    installed.path('.old-token').write_text('earlier-update\n')
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    assert installed.tool(installed.path('.old')) == 'installed', 'the stale backup is replaced'
    assert run(installed, RESTORE) == 0
    assert installed.tool(installed.path()) == 'installed'


def test_an_undo_never_restores_a_backup_it_did_not_keep(installed: Site) -> None:
    installed.put(installed.path('.old'), 'two updates ago')
    installed.path('.old-token').write_text('earlier-update\n')
    installed.put(installed.path('.new'), 'another attempt')
    assert run(installed, RESTORE) == 0
    assert installed.tool(installed.path()) == 'installed'
    assert installed.tool(installed.path('.new')) == 'another attempt', 'not its own'


def test_the_swap_and_its_undo_match_in_any_time_zone(installed: Site) -> None:
    # The tool's start time goes into the mark; read in local time it would differ between them.
    path = os.environ.get('PATH', '/usr/bin:/bin')
    installed.put(installed.staged, 'new')
    steps = (
        (SWAP, OPERATION, {'PATH': path, 'TZ': 'JST-9'}),
        (RESTORE, OPERATION, {'PATH': path, 'TZ': 'EST5'}),
    )
    assert session(installed, *steps) == [0, 0]
    assert installed.tool(installed.path()) == 'installed'


# Two updates in a row from an installed 2026.11.31, as Qt IFW runs them: the first update's
# operation is saved, and the next update undoes it before it unpacks the component again.


def first_update(site: Site, controller: str) -> None:
    """The first update succeeds; the released controller keeps the backup, newer ones drop it."""
    site.put(site.staged, 'first')
    assert session(site, (SWAP, 'first-update')) == [0]
    if controller == 'newer':
        for suffix in ('.old', '.old-token'):
            subprocess.run(['/bin/rm', '-rf', str(site.path(suffix))], check=True)
    assert site.tool(site.path()) == 'first'


def test_an_update_rolled_back_from_the_released_tool_puts_it_back(installed: Site) -> None:
    installed.put(installed.staged, 'first')
    assert session(installed, (SWAP, 'first-update'), (RESTORE, 'first-update')) == [0, 0]
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()


@pytest.mark.parametrize('controller', ['released', 'newer'])
def test_the_next_update_undoing_the_committed_swap_changes_nothing(
    installed: Site, controller: str
) -> None:
    first_update(installed, controller)
    installed.put(installed.staged, 'second')
    assert session(installed, (RESTORE, 'first-update'), (SWAP, 'second-update')) == [0, 0]
    assert installed.tool(installed.path()) == 'second'
    assert installed.tool(installed.path('.old')) == 'first'


@pytest.mark.parametrize('controller', ['released', 'newer'])
def test_the_next_update_rolled_back_puts_the_first_updates_tool_back(
    installed: Site, controller: str
) -> None:
    first_update(installed, controller)
    installed.put(installed.staged, 'second')
    steps = (RESTORE, 'first-update'), (SWAP, 'second-update'), (RESTORE, 'second-update')
    assert session(installed, *steps) == [0, 0, 0]
    assert installed.tool(installed.path()) == 'first'


# An update stopped between the two renames leaves the backup as the only tool, and Qt IFW saves
# none of its operations. Whatever runs next, that copy stays until a new tool is in place or it is
# put back.


def stopped_update(site: Site, shims: Path) -> None:
    site.put(site.staged, 'new')
    assert session(site, (SWAP, 'stopped-update', mv_shim(shims, STOPPED)))[0] != 0
    assert site.tool(site.path()) is None
    assert site.tool(site.path('.old')) == 'installed'


def test_a_new_operation_after_a_stop_keeps_the_only_tool_as_its_backup(
    installed: Site, shims: Path
) -> None:
    stopped_update(installed, shims)
    installed.put(installed.staged, 'newer')
    assert session(installed, (SWAP, 'next-update')) == [0]
    assert installed.tool(installed.path()) == 'newer'
    assert installed.tool(installed.path('.old')) == 'installed'


def test_a_new_operation_after_a_stop_that_fails_puts_the_only_tool_back(
    installed: Site, shims: Path, tmp_path_factory
) -> None:
    stopped_update(installed, shims)
    installed.put(installed.staged, 'newer')
    refuse = mv_shim(tmp_path_factory.mktemp('refuse'), 'exit 1')
    assert session(installed, (SWAP, 'next-update', refuse)) == [1]
    assert installed.tool(installed.path()) == 'installed'


def test_a_new_operation_after_a_stop_with_nothing_staged_puts_the_only_tool_back(
    installed: Site, shims: Path
) -> None:
    stopped_update(installed, shims)
    subprocess.run(['/bin/rm', '-rf', str(installed.path('.new'))], check=True)
    assert session(installed, (SWAP, 'next-update')) == [1]
    assert installed.tool(installed.path()) == 'installed'


def test_a_new_operation_after_a_stop_rolled_back_puts_the_only_tool_back(
    installed: Site, shims: Path
) -> None:
    stopped_update(installed, shims)
    installed.put(installed.staged, 'newer')
    steps = (SWAP, 'next-update'), (RESTORE, 'next-update')
    assert session(installed, *steps) == [0, 0]
    assert installed.tool(installed.path()) == 'installed'


# After such a stop the app is the only way back: on start, and before Maintenance or Update opens
# the tool, it puts the kept item back (restore_kept_maintenance_tool in
# app/src/desktop_updates.cpp, tested with the app). This copies it, the lock included, so that the
# update the user retries from the app runs on the folder the app leaves, and a recovery racing an
# update or another recovery is seen to give way.


def app_recovers(site: Site, between: Callable[[], None] | None = None) -> bool:
    """Put the kept item back when none is usable; False when another holds the lock.

    `between` runs between the two renames, where a recovery without the lock could be overtaken.
    """
    lock = os.open(site.target / '.MaintenanceTool.lock', os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        cur, kept, drop = site.path(), site.path('.old'), site.path('.drop')
        if site.tool(cur) is not None or site.tool(kept) is None:
            return True
        shutil.rmtree(drop, ignore_errors=True)
        if cur.exists() or cur.is_symlink():
            cur.rename(drop)
        if between:
            between()
        kept.rename(cur)
        site.path('.old-token').unlink(missing_ok=True)
        shutil.rmtree(drop, ignore_errors=True)
        return True
    finally:
        os.close(lock)


@pytest.mark.parametrize('staged', ['newer', None])
def test_a_retried_update_after_the_app_put_the_tool_back_finishes(
    installed: Site, shims: Path, staged: str | None
) -> None:
    stopped_update(installed, shims)
    assert app_recovers(installed)
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()
    assert not installed.path('.old-token').exists()
    assert installed.tool(installed.path('.new')) == 'new', 'left for the retried update'
    if staged:
        installed.put(installed.staged, staged)
    assert session(installed, (SWAP, 'retried-update')) == [0]
    assert installed.tool(installed.path()) == (staged or 'new')
    assert installed.tool(installed.path('.old')) == 'installed'


def test_a_retried_update_after_the_app_put_the_tool_back_rolls_back(
    installed: Site, shims: Path
) -> None:
    stopped_update(installed, shims)
    assert app_recovers(installed)
    installed.put(installed.staged, 'newer')
    steps = (SWAP, 'retried-update'), (RESTORE, 'retried-update')
    assert session(installed, *steps) == [0, 0]
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()


def test_the_app_leaves_a_tool_in_place_alone(installed: Site) -> None:
    installed.put(installed.path('.old'), 'two updates ago')
    assert app_recovers(installed)
    assert installed.tool(installed.path()) == 'installed'
    assert installed.tool(installed.path('.old')) == 'two updates ago'


def claimed_by_a_running_tool(mark: Path) -> bool:
    """Whether the tool a claim or a backup's mark names, "<token> <pid> <start>", still runs."""
    try:
        fields = mark.read_text(encoding='utf-8').split()
    except FileNotFoundError:
        return False
    env = {'TZ': 'UTC0', 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}
    ps = subprocess.run(
        ['ps', '-o', 'lstart=', '-p', fields[1]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return ps.returncode == 0 and ' '.join(ps.stdout.split()) == ' '.join(fields[2:])


def app_cleans(site: Site) -> bool:
    """The app's cleanup at start (remove_maintenance_tool_leftovers): whether it removed anything.

    The staging folder stays while the tool its claim names runs, whatever the folder holds yet.
    """
    lock = os.open(site.target / '.MaintenanceTool.lock', os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        if site.tool(site.path()) is None:
            return False
        staging = site.target / STAGING
        leftovers = [site.path('.old'), site.path('.old-token'), staging]
        if claimed_by_a_running_tool(staging / '.claim'):
            leftovers.remove(staging)
        if claimed_by_a_running_tool(site.path('.old-token')):
            leftovers = leftovers[2:]
        present = [path for path in leftovers if path.exists()]
        for path in present:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        return bool(present)
    finally:
        os.close(lock)


class Unpacking:
    """A tool run that has claimed the staging folder and is unpacking into it until released."""

    def __init__(self, site: Site, shims: Path) -> None:
        self.go = shims / 'go'
        os.mkfifo(self.go)
        commands = [
            [site.command(SWAP, 'claim', 'claim'), None],
            [['/bin/sh', '-c', f'echo paused; read go < "{self.go}"'], None],
        ]
        command = [sys.executable, '-c', SESSION, json.dumps(commands)]
        self.tool = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
        codes = []
        for line in self.tool.stdout:
            if line.strip() == 'paused':
                break
            codes.append(int(line))
        assert codes == [0], f'the claim failed: {codes}'

    def release(self) -> list[int]:
        with self.go.open('w') as go:
            go.write('\n')
        codes = [int(line) for line in self.tool.stdout.read().split()]
        self.tool.wait()
        return codes


def test_the_app_keeps_a_staging_folder_its_update_is_unpacking_into(
    installed: Site, shims: Path
) -> None:
    unpacking = Unpacking(installed, shims)
    try:
        # Unpacked so far: the item's folder, without the file that makes it usable.
        (installed.staged / 'part').mkdir(parents=True)
        assert not app_cleans(installed)
        assert (installed.staged / 'part').is_dir(), 'left to the update unpacking into it'
    finally:
        assert unpacking.release() == [0]
    # That tool has exited: whatever it left is left over.
    assert app_cleans(installed)
    assert not (installed.target / STAGING).exists()


def test_the_app_removes_a_staging_folder_nobody_claims(installed: Site) -> None:
    installed.put(installed.staged, 'new')
    assert app_cleans(installed)
    assert not (installed.target / STAGING).exists()


def test_a_claim_names_this_run_and_its_release_drops_it(installed: Site) -> None:
    claim, release = (SWAP, 'claim', None, 'claim'), (CLEANUP, '', None, 'release')
    assert session(installed, claim) == [0]
    text = (installed.target / STAGING / '.claim').read_text().split()
    assert text[0] == 'claim', text
    assert session(installed, release) == [0]
    assert (installed.target / STAGING / '.claim').exists(), 'another run does not release it'
    assert session(installed, claim, release) == [0, 0]
    assert not (installed.target / STAGING).exists(), 'the claiming run releases it'


def test_nothing_is_claimed_or_marked_without_the_tools_start_time(
    installed: Site, shims: Path
) -> None:
    # A claim or mark without it reads as a later process with the same number, whose tool has
    # exited.
    (shims / 'ps').write_text('#!/bin/sh\nexit 1\n')
    (shims / 'ps').chmod(0o755)
    env = {'PATH': f'{shims}:/usr/bin:/bin'}
    installed.put(installed.staged, 'new')
    assert session(installed, (SWAP, 'claim', env, 'claim'), (SWAP, OPERATION, env)) == [1, 1]
    assert not (installed.target / STAGING / '.claim').exists()
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()
    assert not installed.path('.old-token').exists()


def test_a_release_keeps_whatever_else_the_rollback_left(installed: Site) -> None:
    claim, release = (SWAP, 'claim', None, 'claim'), (CLEANUP, '', None, 'release')
    installed.put(installed.staged, 'part')
    assert session(installed, claim, release) == [0, 0]
    assert not (installed.target / STAGING / '.claim').exists()
    assert installed.tool(installed.staged) == 'part', 'the app removes it once this run has ended'


def single_item(site: Site, text: str) -> None:
    """One item in place, holding `text`, with nothing moved inside it."""
    assert site.tool(site.path()) == text
    assert not (site.path() / site.path('.new').name).exists(), 'moved into the item'
    assert not (site.path() / site.form.item).exists(), 'moved into the item'


def test_the_app_gives_way_to_a_swap_between_its_renames(installed: Site, shims: Path) -> None:
    installed.put(installed.staged, 'new')
    paused = Paused(installed, shims, '*.new', (SWAP, OPERATION))
    assert installed.tool(installed.path()) is None, 'stopped with no tool in place'
    assert not app_recovers(installed)
    assert installed.tool(installed.path('.old')) == 'installed', 'left alone'
    assert paused.release() == [0]
    single_item(installed, 'new')
    assert not installed.path('.new').exists()
    assert installed.tool(installed.path('.old')) == 'installed'


def test_the_app_gives_way_to_an_undo_between_its_renames(installed: Site, shims: Path) -> None:
    installed.put(installed.staged, 'new')
    path = {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
    paused = Paused(installed, shims, '*.old', (SWAP, OPERATION, path), (RESTORE, OPERATION))
    assert paused.codes == [0]
    assert installed.tool(installed.path()) is None, 'stopped with no tool in place'
    assert not app_recovers(installed)
    assert paused.release() == [0, 0]
    single_item(installed, 'installed')
    assert not installed.path('.old').exists()


def test_a_swap_whose_tool_was_force_quit_still_finishes_alone(
    installed: Site, shims: Path
) -> None:
    # The tool goes, the swap's shell goes on: until it ends, the lock is still held.
    installed.put(installed.staged, 'new')
    paused = Paused(installed, shims, '*.new', (SWAP, OPERATION))
    paused.tool.kill()
    paused.tool.wait()
    assert not app_recovers(installed)
    paused.release()
    single_item(installed, 'new')
    assert not installed.path('.new').exists()
    assert installed.tool(installed.path('.old')) == 'installed'
    assert app_recovers(installed), 'the lock goes with the swap'


def test_a_swap_stopped_with_its_whole_tree_lets_the_app_recover(
    installed: Site, shims: Path
) -> None:
    # A power cut or a forced shutdown: nothing of the update runs on, and its lock is gone.
    installed.put(installed.staged, 'new')
    paused = Paused(installed, shims, '*.new', (SWAP, OPERATION), start_new_session=True)
    os.killpg(paused.tool.pid, signal.SIGKILL)
    paused.finish()
    assert app_recovers(installed)
    single_item(installed, 'installed')
    assert not installed.path('.old').exists()
    assert installed.tool(installed.path('.new')) == 'new', 'left for the retried update'


def test_two_recoveries_together_leave_one_usable_tool(installed: Site, shims: Path) -> None:
    stopped_update(installed, shims)
    second = []
    assert app_recovers(installed, between=lambda: second.append(app_recovers(installed)))
    assert second == [False], 'the second gives way'
    single_item(installed, 'installed')
    assert not installed.path('.old').exists()
    assert not installed.path('.drop').exists()


def test_nothing_staged_changes_nothing(installed: Site) -> None:
    assert run(installed, SWAP) == 1
    assert installed.tool(installed.path()) == 'installed'
    assert not installed.path('.old').exists()


# After a successful update the tool component's script runs maintenance_cleanup.sh.


def test_the_cleanup_removes_the_backup_and_the_staging_folder(installed: Site) -> None:
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    (installed.target / STAGING).mkdir()
    (installed.target / STAGING / '.DS_Store').write_text('Finder')
    assert run(installed, CLEANUP) == 0
    assert installed.tool(installed.path()) == 'new'
    for leftover in ('.old', '.old-token'):
        assert not installed.path(leftover).exists(), leftover
    assert not (installed.target / STAGING).exists()


def test_the_cleanup_removes_the_folder_older_releases_staged_into(installed: Site) -> None:
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    (installed.target / 'maintenancetool').mkdir()
    (installed.target / 'maintenancetool/.DS_Store').write_text('Finder')
    assert run(installed, CLEANUP) == 0
    assert not (installed.target / 'maintenancetool').exists()


def test_the_cleanup_keeps_a_file_by_the_older_staging_name(installed: Site) -> None:
    # On a case-insensitive disk the Linux tool, MaintenanceTool, answers to that name.
    installed.put(installed.staged, 'new')
    assert run(installed, SWAP) == 0
    (installed.target / 'maintenancetool').write_text('the tool')
    assert run(installed, CLEANUP) == 0
    assert (installed.target / 'maintenancetool').read_text() == 'the tool'


def test_the_cleanup_keeps_the_only_tool(installed: Site, shims: Path) -> None:
    stopped_update(installed, shims)
    (installed.target / STAGING).mkdir(exist_ok=True)
    (installed.target / STAGING / '.DS_Store').write_text('Finder')
    assert run(installed, CLEANUP) == 0
    assert installed.tool(installed.path('.old')) == 'installed'
    assert installed.path('.old-token').exists()
    assert (installed.target / STAGING / '.DS_Store').exists()


# The first Linux update off a release whose app component carried the runtime: the Framework
# undoes that component, deleting the runtime's files, before any operation of the update runs.
# The app component's script keeps a copy first (swap with copy) and settles it at the end and in
# its operation's undo (restore with copy).
KEEP = (SWAP, 'transition', None, 'copy')
SETTLE = (RESTORE, 'transition', None, 'copy')
OLD_UNDO = (
    'import os, sys\n'
    'for folder, _, files in os.walk(sys.argv[1]):\n'
    '    for name in files:\n'
    '        os.remove(os.path.join(folder, name))\n'
)


def undoes_the_old_app(site: Site) -> tuple:
    # Deletes the files as the Framework's undo of an unpack does, leaving the folders.
    return ([sys.executable, '-c', OLD_UNDO, str(site.path())], None)


def transition(site: Site, *steps) -> list[int]:
    commands = [
        step if isinstance(step[0], list) else [site.command(step[0], step[1], step[3]), step[2]]
        for step in steps
    ]
    command = [sys.executable, '-c', SESSION, json.dumps([list(step) for step in commands])]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return [int(code) for code in result.stdout.split()]


def test_a_failed_first_update_puts_the_kept_runtime_back(installed: Site) -> None:
    codes = transition(installed, KEEP, undoes_the_old_app(installed), SETTLE)
    assert codes == [0, 0, 0]
    assert installed.tool(installed.path()) == 'installed', 'the copy survived the undo'
    for suffix in ('.old', '.old-token', '.copy'):
        assert not installed.path(suffix).exists(), suffix


def test_the_kept_copy_goes_when_the_runtime_is_still_usable(installed: Site) -> None:
    assert transition(installed, KEEP, SETTLE, SETTLE) == [0, 0, 0]
    assert installed.tool(installed.path()) == 'installed'
    for suffix in ('.old', '.old-token', '.copy'):
        assert not installed.path(suffix).exists(), suffix


def test_a_later_run_never_settles_the_copy(installed: Site) -> None:
    assert session(installed, KEEP) == [0]
    assert session(installed, SETTLE) == [0]
    assert installed.path('.old').exists(), 'kept by another run'


@pytest.mark.parametrize('rolled_back', [False, True], ids=['succeeded', 'rolled-back'])
def test_a_swap_after_the_undo_takes_the_copy_as_its_backup(
    installed: Site, *, rolled_back: bool
) -> None:
    # A tool component that swaps a new runtime in after the undo finds no usable one in place,
    # so it keeps the copy as its own backup; its undo puts the original back.
    installed.put(installed.staged, 'new')
    swap, undo = (SWAP, OPERATION, None, ''), (RESTORE, OPERATION, None, '')
    steps = (KEEP, undoes_the_old_app(installed), swap, *([undo] if rolled_back else []), SETTLE)
    assert transition(installed, *steps) == [0] * len(steps)
    assert installed.tool(installed.path()) == ('installed' if rolled_back else 'new')
    kept = None if rolled_back else 'installed'
    assert installed.tool(installed.path('.old')) == kept, 'the swap backup, for the cleanup'


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


def test_the_tool_runs_each_script_with_its_text_as_its_name() -> None:
    # The scripts run themselves again under the lock from that name.
    script = (FOLDER / 'maintenancescript.qs').read_text()
    for name in ('SWAP_SCRIPT', 'RESTORE_SCRIPT', 'CLEANUP_SCRIPT'):
        assert f'"-c", {name}, {name},' in script, name


def test_no_script_holds_an_at_sign() -> None:
    # IFW expands a variable named between two at signs in an operation's arguments.
    for script in (SWAP, RESTORE, CLEANUP):
        assert '@' not in script.read_text(), script.name


def test_the_packaged_script_carries_the_shell_scripts() -> None:
    spec = importlib.util.spec_from_file_location('package', FOLDER / 'package.py')
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    script = package.maintenance_script()
    for marker in ('EDI_SWAP_SCRIPT', 'EDI_RESTORE_SCRIPT', 'EDI_CLEANUP_SCRIPT'):
        assert f'@{marker}@' not in script, marker
    for name in ('maintenance_swap.sh', 'maintenance_restore.sh', 'maintenance_cleanup.sh'):
        assert name in script, name
