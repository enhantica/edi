# SPDX-License-Identifier: BSD-3-Clause
"""The macOS maintenance tool swap an update runs (edi ADR-0106), in a scratch folder.

maintenance_swap.sh must leave a tool in place whatever fails, keep the installed bundle until
the update has succeeded, and run again after any interruption; maintenance_restore.sh, its undo,
puts the kept bundle back.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'tools/installer'
SWAP = FOLDER / 'maintenance_swap.sh'
RESTORE = FOLDER / 'maintenance_restore.sh'


def bundle(path: Path, text: str) -> None:
    executable = path / 'Contents/MacOS/MaintenanceTool'
    executable.parent.mkdir(parents=True)
    executable.write_text(text)


def tool(path: Path) -> str | None:
    executable = path / 'Contents/MacOS/MaintenanceTool'
    return executable.read_text() if executable.exists() else None


def run(script: Path, target: Path, env: dict | None = None) -> int:
    return subprocess.run(['/bin/sh', str(script), str(target)], env=env, check=False).returncode


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


def test_a_rerun_keeps_the_backup_an_earlier_attempt_left(tmp_path: Path) -> None:
    bundle(tmp_path / 'MaintenanceTool.app.old', 'installed')
    bundle(tmp_path / 'MaintenanceTool.app', 'half written')
    bundle(tmp_path / 'maintenancetool/MaintenanceTool.app', 'new')
    assert run(SWAP, tmp_path) == 0
    assert tool(tmp_path / 'MaintenanceTool.app') == 'new'
    assert tool(tmp_path / 'MaintenanceTool.app.old') == 'installed'


def test_a_failed_last_rename_puts_the_installed_tool_back(
    installed: Path, tmp_path_factory
) -> None:
    # An mv that refuses only the rename of the new tool into place.
    shims = tmp_path_factory.mktemp('shims')
    (shims / 'mv').write_text(
        '#!/bin/sh\ncase "$1" in *.app.new) exit 1 ;; esac\nexec /bin/mv "$@"\n'
    )
    (shims / 'mv').chmod(0o755)
    bundle(installed / 'maintenancetool/MaintenanceTool.app', 'new')
    env = {'PATH': f'{shims}:/usr/bin:/bin'}
    assert run(SWAP, installed, env) == 1
    assert tool(installed / 'MaintenanceTool.app') == 'installed', 'never left without a tool'


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
