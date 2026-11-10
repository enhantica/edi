"""The amended tooltip delay applies through every Preferences editing path."""

import json
from pathlib import Path

import pytest

from tests.integration.app import native_actor

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / 'tests/unit/app/TooltipDelayCases.js')
    .read_text()
    .split('var cases = ', 1)[1]
    .strip()
    .removesuffix(';')
)
CASES = [
    f'{group}:{row["tag"]}'
    for group, rows in [
        ('editor_changes', DATA['edits']),
        ('existing_and_new_owners_update', DATA['owners']),
    ]
    for row in rows
]
streamed_actor = native_actor.streamed_actor
NATIVE_FILE = 'tst_tooltip_delay.qml'
NATIVE_SELECTORS = {
    f'test_changed_delay_applies_without_restart[{case}]': 'TooltipDelay::test_' + case
    for case in CASES
}


@pytest.mark.parametrize('case', CASES)
def test_changed_delay_applies_without_restart(case, streamed_actor):
    streamed_actor.run('TooltipDelay::test_' + case)


def test_delay_inventory_keeps_every_declared_owner_and_input_path():
    expected = {
        'E.Button',
        'E.GroupButton',
        'E.ToolButton',
        'E.SideBarButton',
        'E.StatusBarItem',
        'E.TabButton',
        'E.CheckBox',
        'E.ComboBox',
        'E.TextField',
        'E.Slider',
        'E.SpinBox',
        'C.ListViewLabel',
        'C.ListViewTextInput',
        'HeaderLabel',
        'NumberLabel',
        'ChartToolButton',
        'StatusBarItem',
        'ToolbarComboBox',
        'SelectorField',
        'ParameterField',
        'ParameterCell',
        'TextCell',
        'ValueField',
        'E.ToolTip',
        'WarningToolTip',
    }
    actual = {row['tag']: row['kind'] for row in DATA['owners']}
    assert actual == {
        name: 'Item' if name in {'E.ToolTip', 'WarningToolTip'} else name for name in expected
    }, 'ADR-0076: live delay covers every declared base, inherited, standalone and warning owner'
    assert [(row['tag'], row['expected']) for row in DATA['edits']] == [
        ('plus', 3100),
        ('minus', 2900),
        ('typed-enter', 2371),
    ], 'ADR-0076: both real indicator paths and committed native text input retain their witnesses'
