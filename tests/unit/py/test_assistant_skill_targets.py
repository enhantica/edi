# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'skill_targets', ROOT / 'tools/checks/assistant_skill_targets.py'
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_bundled_targets_exist():
    assert MODULE.check_targets(ROOT / 'data/assistant/skills', ROOT / 'app/qml') == [], (
        'All bundled skill targets must exist in the current app.',
        'Bundled targets exist.',
    )


def test_skill_naming_a_missing_element_is_rejected(tmp_path):
    skills = tmp_path / 'skills'
    shutil.copytree(ROOT / 'data/assistant/skills', skills)
    guide = skills / 'project-assistance/SKILL.md'
    with guide.open('a') as stream:
        stream.write('\nClick `ui:missing.assistant.control`.\n')
    errors = MODULE.check_targets(skills, ROOT / 'app/qml')
    assert any('missing.assistant.control' in error for error in errors), (
        'Skill naming a missing element is rejected.'
    )


def test_removing_a_real_control_is_rejected(tmp_path):
    qml = tmp_path / 'qml'
    shutil.copytree(ROOT / 'app/qml', qml)
    original = qml / 'Pages/Experiment/ExperimentsGroup.qml'
    text = original.read_text()
    assert 'objectName: "experiments.load.dataFile"' in text, (
        'Removing a real control is rejected.'
    )
    original.write_text(
        text.replace('objectName: "experiments.load.dataFile"', 'objectName: "renamed.dataFile"')
    )
    errors = MODULE.check_targets(ROOT / 'data/assistant/skills', qml)
    assert any('experiments.load.dataFile' in error for error in errors), (
        'Removing a real control is rejected.'
    )


def test_file_cell_route_is_rejected(tmp_path):
    guide = tmp_path / 'guide/SKILL.md'
    guide.parent.mkdir()
    guide.write_text('Click experiments.file.0 to load data.')
    assert any('retired' in error for error in MODULE.check_targets(tmp_path, ROOT / 'app/qml')), (
        'File cell route is rejected.'
    )
