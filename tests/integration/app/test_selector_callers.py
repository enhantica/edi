"""Real SelectorField callers share refusal and popup ownership semantics."""

import json
from pathlib import Path

import pytest

from tests.integration.app import native_actor
from tests.integration.py.test_table_and_about_contract import properties, qml_objects

ROOT = Path(__file__).resolve().parents[3]
ACTORS = ROOT / 'tests/unit/app'
RECORDS = json.loads(
    (ACTORS / 'SelectorCallers.js')
    .read_text()
    .split('var callers = ', 1)[1]
    .strip()
    .removesuffix(';')
)
CASES = [
    (record['component'], level) for record in RECORDS for level in ['Off', 'Important', 'All']
]
streamed_actor = native_actor.streamed_actor

NATIVE_FILE = 'tst_selector_callers.qml'
NATIVE_PREFIX = 'SelectorCallers::test_caller_policy:'
NATIVE_SELECTORS = {
    f'test_selector_caller_policy[{component}-{level}]': NATIVE_PREFIX + component + '-' + level
    for component, level in CASES
}
DECLARED = [
    (name, token, level)
    for record in RECORDS
    for name, choice in record.get('choices', {}).items()
    for token in choice['tokens']
    for level in ['Off', 'Important', 'All']
]
DECLARED_IDS = [f'{name}-{token}-{level}' for name, token, level in DECLARED]
NATIVE_SELECTORS.update({
    f'test_declared_choice_writeback[{tag}]': 'SelectorCallers::test_declared_choice_writeback:'
    + tag
    for tag in DECLARED_IDS
})


def test_every_selector_caller_has_a_behavior_witness():
    expected = {}
    for path in (ROOT / 'app/qml').rglob('*.qml'):
        names = []
        for kind, body in qml_objects(path.read_text()):
            if kind.rsplit('.', 1)[-1] == 'SelectorField':
                raw = dict(properties(body))['objectName']
                names.append(
                    raw[1 : raw.index('${')] + '*' if raw.startswith('`') else json.loads(raw)
                )
        if names:
            expected[path.relative_to(ROOT).as_posix()] = sorted(names)
    actual = {record['path']: sorted(record['names']) for record in RECORDS}
    assert actual == expected, (
        'Every SelectorField declaration, including dynamic callers, has an actual caller witness'
    )
    assert len(actual) == len(RECORDS), (
        'Each caller component has one unambiguous behavior fixture'
    )


@pytest.mark.parametrize(('component', 'level'), CASES, ids=[f'{c}-{level}' for c, level in CASES])
def test_selector_caller_policy(component, level, streamed_actor):
    streamed_actor.run(f'SelectorCallers::test_caller_policy:{component}-{level}')


def test_declared_behavior_inventory_retains_every_imported_control():
    expected = {
        'atomSiteMoments.form': (
            'AtomSiteMomentGroup',
            'momentForm',
            ['crystal_axes', 'cartesian', 'spherical'],
        ),
        'structure.appearance.momentView': (
            'AppearanceGroup',
            'momentView',
            ['through_atom', 'from_centre', 'from_surface'],
        ),
        'minimizer.stopRule': ('MinimizerGroup', 'stopRule', ['chi_square_change', 'shift_su']),
        'minimizer.momentsNearZero': (
            'MinimizerGroup',
            'momentsNearZero',
            ['try_exact_zero', 'keep_free'],
        ),
    }
    actual = {
        name: (record['component'], choice['property'], choice['tokens'])
        for record in RECORDS
        for name, choice in record.get('choices', {}).items()
    }
    assert actual == expected, (
        'ADR-0017/0070 F2: all four imported controls retain declared token/writeback witnesses'
    )
    assert all(record.get('magnetic') for record in RECORDS if record.get('choices')), (
        'ADR-0070 F2: magnetic-only controls require actual magnetic fixture inputs'
    )


@pytest.mark.parametrize(('name', 'token', 'level'), DECLARED, ids=DECLARED_IDS)
def test_declared_choice_writeback(name, token, level, streamed_actor):
    streamed_actor.run(f'SelectorCallers::test_declared_choice_writeback:{name}-{token}-{level}')
