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
    assert Path(shutil.which('bash', path=str(decoy))) == fake
    destination = tmp_path / 'github-path'
    destination.write_bytes(b'previous entry\n')
    assert expose(str(selected), destination) == selected
    assert destination.read_bytes() == b'previous entry\n' + str(selected.parent).encode() + b'\n'
    search = str(selected.parent) + os.pathsep + str(decoy)
    assert Path(shutil.which('bash', path=search)).resolve() == selected


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
    assert not destination.exists()


def test_every_core_platform_exposes_its_actual_running_bash():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['core']['steps']
    selected = [step for step in steps if 'native_shell.py' in step.get('run', '')]
    assert len(selected) == 1
    assert selected[0]['shell'] == 'bash'
    assert selected[0]['run'] == 'python tools/ci/native_shell.py "$BASH"'
    assert steps.index(selected[0]) > next(
        index
        for index, step in enumerate(steps)
        if step.get('uses') == './.github/actions/setup-pixi'
    )
