"""Packaged assistant UI names must exist in the current GUI declarations."""

import re

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT


def check_targets(skills, qml):
    declared = set(re.findall(r'objectName\s*:\s*["\']([^"\']+)["\']', qml))
    targets = set(re.findall(r'`ui:([^`]+)`', skills))
    prose = re.sub(r'`ui:[^`]+`', '', skills)
    targets.update(token.rstrip('.') for token in re.findall(r'ui:([A-Za-z0-9_.-]+)', prose))
    assert targets, 'Gate 4: packaged assistant guidance actually exercises named GUI elements'
    assert targets <= declared, (
        'Gate 4: assistant guidance names only elements declared by the current GUI: '
        + repr(sorted(targets - declared))
    )


def test_packaged_assistant_skills_name_only_current_gui_elements():
    skills = list((ROOT / 'data/assistant/skills').glob('*/SKILL.md'))
    assert skills, 'Gate 4: the packaged assistant ships its skill documents'
    check_targets(
        '\n'.join(path.read_text() for path in skills),
        '\n'.join(path.read_text() for path in (ROOT / 'app/qml').rglob('*.qml')),
    )


@pytest.mark.parametrize(
    'target',
    [
        'ui:structures.oldLoad',
        'ui:onlineLoad.renamed',
        'ui:missing.button',
        'ui:structures..load',
        '`ui:onlineLoad.`',
    ],
)
def test_assistant_target_observer_refuses_missing_and_renamed_gui_names(target):
    qml = 'Button { objectName: "structures.load" }\nPopup { objectName: "onlineLoad" }'
    check_targets('Use ui:structures.load and ui:onlineLoad.', qml)
    with pytest.raises(AssertionError, match='Gate 4:'):
        check_targets('Use ' + target, qml)
