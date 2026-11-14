"""Python children must find the workflow shell before an unrelated PATH decoy."""

import os
import shutil
from pathlib import Path

import pytest
import yaml

from tools.ci.native_shell import expose

ROOT = Path(__file__).resolve().parents[3]


def test_selected_workflow_shell_wins_over_an_unrelated_path_entry(tmp_path):
    selected = Path(shutil.which('bash')).resolve(strict=True)
    decoy = tmp_path / 'decoy'
    decoy.mkdir()
    fake = decoy / selected.name
    fake.write_bytes(b'unrelated shell; never executed')
    fake.chmod(0o755)
    assert Path(shutil.which('bash', path=str(decoy))) == fake, (
        'Selected workflow shell wins over an unrelated path entry.'
    )
    destination = tmp_path / 'github-path'
    destination.write_bytes(b'previous entry\n')
    assert expose(str(selected), destination) == selected, (
        'Selected workflow shell wins over an unrelated path entry.'
    )
    assert (
        destination.read_bytes() == b'previous entry\n' + str(selected.parent).encode() + b'\n'
    ), 'Selected workflow shell wins over an unrelated path entry.'
    search = str(selected.parent) + os.pathsep + str(decoy)
    assert Path(shutil.which('bash', path=search)).resolve() == selected, (
        'Selected workflow shell wins over an unrelated path entry.'
    )


@pytest.mark.parametrize('damage', ['missing', 'directory', 'wrong-name', 'newline'])
def test_selected_shell_refuses_invalid_environment_file_entries(tmp_path, damage):
    shell = tmp_path / 'bash'
    if damage == 'directory':
        shell.mkdir()
    elif damage == 'wrong-name':
        shell = tmp_path / 'other'
        shell.write_bytes(b'unrelated executable')
    elif damage == 'newline':
        shell = tmp_path / 'unexpected\nentry/bash'
    destination = tmp_path / 'github-path'
    with pytest.raises((OSError, ValueError)):
        expose(str(shell), destination)
    assert not destination.exists(), 'Selected shell refuses invalid environment file entries.'


def test_every_core_platform_exposes_its_actual_running_bash():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['core']['steps']
    selected = [step for step in steps if 'native_shell.py' in step.get('run', '')]
    assert len(selected) == 1, 'Every core platform exposes its actual running bash.'
    assert selected[0]['shell'] == 'bash', 'Every core platform exposes its actual running bash.'
    assert selected[0]['run'] == 'python tools/ci/native_shell.py "$BASH"', (
        'Every core platform exposes its actual running bash.'
    )
    assert steps.index(selected[0]) > next(
        index
        for index, step in enumerate(steps)
        if step.get('uses') == './.github/actions/setup-pixi'
    ), 'Every core platform exposes its actual running bash.'


@pytest.mark.parametrize('suffix', ['.exe', '.EXE'])
def test_selected_bash_retains_an_explicit_native_executable_suffix(tmp_path, suffix):
    selected = tmp_path / ('bash' + suffix)
    selected.write_bytes(b'actual selected shell')
    destination = tmp_path / 'github-path'
    assert expose(str(selected), destination) == selected, (
        'Selected bash retains an explicit native executable suffix.'
    )
    assert destination.read_bytes() == str(selected.parent).encode() + b'\n', (
        'Selected bash retains an explicit native executable suffix.'
    )


def test_bash_without_suffix_resolves_its_existing_exe_without_a_path_search(tmp_path):
    selected = tmp_path / 'bash.exe'
    selected.write_bytes(b'actual selected shell')
    destination = tmp_path / 'github-path'
    assert expose(str(selected.with_suffix('')), destination) == selected, (
        'Bash without suffix resolves its existing exe without a path search.'
    )
    assert destination.read_bytes() == str(selected.parent).encode() + b'\n', (
        'Bash without suffix resolves its existing exe without a path search.'
    )


def test_existing_unsuffixed_bash_wins_over_a_neighbouring_exe(tmp_path):
    selected = tmp_path / 'bash'
    selected.write_bytes(b'actual selected shell')
    selected.with_suffix('.exe').write_bytes(b'other executable')
    destination = tmp_path / 'github-path'
    assert expose(str(selected), destination) == selected, (
        'Existing unsuffixed bash wins over a neighbouring exe.'
    )
