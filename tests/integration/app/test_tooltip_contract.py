"""ADR-0076 point 6 through the public inputs of retained production owners."""

import hashlib
import io
import json
import re
from types import SimpleNamespace

import pytest

from tests.fixtures.shared_ui.generate_tooltip_matrix import render
from tests.integration.app import native_actor, native_actor_integrity
from tests.integration.app.native_actor import NativeActor
from tests.integration.app.test_shared_controls import ROOT

MATRIX_FILE = ROOT / 'tests/fixtures/shared_ui/TooltipContractCases.js'
MATRIX = json.loads(MATRIX_FILE.read_text().split('var cases = ', 1)[1].strip().removesuffix(';'))
CASES = [(group, row['tag']) for group in sorted(MATRIX) for row in MATRIX[group]]
streamed_actor = native_actor.streamed_actor

NATIVE_FILE = 'tst_tooltip_contract.qml'
NATIVE_SELECTORS = {
    f'test_retained_owner_contract[{case}-{tag}]': f'TooltipContract::test_{case}:{tag}'
    for case, tag in CASES
}


@pytest.mark.parametrize(('case', 'tag'), CASES, ids=[case + '-' + tag for case, tag in CASES])
def test_retained_owner_contract(case, tag, streamed_actor):
    streamed_actor.run(f'TooltipContract::test_{case}:{tag}')


def test_input_matrix_is_generated_once_and_has_unambiguous_native_selections():
    assert MATRIX_FILE.read_text() == render(), (
        'ADR-0076: Python and QML selection share the same generated independent input matrix'
    )
    assert len(CASES) == len(set(CASES)), (
        'ADR-0076: every ownership matrix input selects one unambiguous native data row'
    )
    actor = (ROOT / 'tests/unit/app/tst_tooltip_contract.qml').read_text()
    names = set(re.findall(r'function test_(\w+)\(', actor))
    assert {name for name in names if not name.endswith('_data')} == set(MATRIX), (
        'ADR-0076 every native ownership case has a banked Python selection'
    )
    assert {name.removesuffix('_data') for name in names if name.endswith('_data')} == set(
        MATRIX
    ), 'ADR-0076 every native ownership data function uses the same declared input matrix'
    for group in MATRIX:
        assert re.search(
            r'function test_'
            + group
            + r'_data\(\)\s*\{\s*return Matrix.cases.'
            + group
            + r';\s*\}',
            actor,
        ), 'ADR-0076: data functions select inputs without performing case setup or assertions'
    observed = {
        path.name
        for path in (ROOT / 'tests/unit/app').glob('tst_*.qml')
        if 'Turn.begin(test, Probe' in path.read_text()
    }
    assert observed == set(ACTOR_STARTUP), (
        'ADR-0076 F2: every streamed actor, including feedback, keeps lifecycle integrity coverage'
    )
    for name, (reporter, pin) in ACTOR_STARTUP.items():
        source = (ROOT / 'tests/unit/app' / name).read_text()
        assert not native_actor_integrity.problems(
            source, reporter, pin, shared_startup=name in SHARED_STARTUP
        ), (
            'ADR-0076 F2: shared startup is fixture-only; every behavior row waits and completes '
            'under its own request: ' + name
        )


def test_native_result_controls_reject_foreign_failed_skipped_or_absent_rows(tmp_path):
    selected = 'TooltipContract::test_composition:button-All-true'
    marker = '::TooltipContract::test_composition(button-All-true)'

    def actor_for(output):
        actor = NativeActor.__new__(NativeActor)
        actor.selections = [selected]
        actor.index = actor.failures = 0
        actor.permit = tmp_path / 'permit'
        actor._until = lambda *_: output
        return actor

    actor_for('PASS   : edi_app' + marker).run(selected)
    for output in [
        'FAIL!  : edi_app' + marker,
        'SKIP   : edi_app' + marker,
        'PASS   : edi_app::TooltipContract::test_other()',
        '',
    ]:
        with pytest.raises(AssertionError, match='ADR-0076'):
            actor_for(output).run(selected)
    with pytest.raises(AssertionError, match='ADR-0076'):
        actor_for('PASS   : edi_app' + marker).run(selected + '-foreign')


def test_native_lifecycle_controls_reject_wrong_ack_totals_and_crashes(tmp_path):
    actor = NativeActor.__new__(NativeActor)
    actor.reader = io.StringIO('QDEBUG : NATIVE_OWNER_READY foreign\n')
    actor.process = SimpleNamespace(poll=lambda: None)
    with pytest.raises(AssertionError, match='ADR-0076'):
        NativeActor._until(actor, 'NATIVE_OWNER_READY ', 'requested')
    actor.reader = io.StringIO('')
    actor.process = SimpleNamespace(poll=lambda: 0)
    with pytest.raises(AssertionError, match='ADR-0076'):
        NativeActor._until(actor, 'NATIVE_OWNER_DONE ', 'requested')

    def closed_actor(totals, code, failures=0):
        native = NativeActor.__new__(NativeActor)
        native.selections = ['requested']
        native.index = 1
        native.failures = failures
        native.reader = io.StringIO('')
        native.console = io.StringIO('')
        native.process = SimpleNamespace(wait=lambda **_: None, poll=lambda: code, returncode=code)
        native.log_path = tmp_path / 'native.log'
        native.log_path.write_text(totals)
        return native

    closed_actor('Totals: 3 passed, 0 failed, 0 skipped', 0).close()
    closed_actor('Totals: 2 passed, 1 failed, 0 skipped', 1, failures=1).close()
    for totals, code in [
        ('', 0),
        ('Totals: 2 passed, 0 failed, 0 skipped', 0),
        ('Totals: 3 passed, 1 failed, 0 skipped', 0),
        ('Totals: 3 passed, 0 failed, 1 skipped', 0),
        ('Totals: 3 passed, 0 failed, 0 skipped', -11),
        ('Totals: 3 passed, 0 failed, 0 skipped', 1),
    ]:
        with pytest.raises(AssertionError, match='ADR-0076'):
            closed_actor(totals, code).close()


# Regression pins of reviewed fixture-only startup and eager declarations. These
# admit factory/window/input preparation and fixture-readiness guards, never cases.
# Any new startup statement or component initializer must be reviewed explicitly.
SHARED_STARTUP = {
    'tst_selector_callers.qml',
    'tst_feedback_completion.qml',
    'tst_tooltip_delay.qml',
}
ACTOR_STARTUP = {
    'tst_tooltip_contract.qml': (
        'default',
        'cedea5e30f863a39407b23a392b18fa8f8124e7902476c2e3ca050e0034a012c',
    ),
    'tst_shared_tooltips.qml': (
        'default',
        '8a8d9083d17e4abae82f34fd5c6feacad9341adb86383feee9e81d8fe86095aa',
    ),
    'tst_selector_callers.qml': (
        'default',
        'fe896901bc8e825d47affbfe8205cc7d24221c0eaf0f05bc285e3b6b7647d7b7',
    ),
    'tst_feedback_completion.qml': (
        'direct',
        'd44a90f06df033e0c34b71aab0e9afe44a03e7cda847a027450e81eefad9bea6',
    ),
    'tst_tooltip_delay.qml': (
        'default',
        'e02466cec71caa3864d6d15b5191d69eab5da6b0615c8c3ba4d670362e52449c',
    ),
}


@pytest.mark.parametrize('name', list(ACTOR_STARTUP))
@pytest.mark.parametrize(
    'escape',
    [
        'late-begin',
        'foreign-begin',
        'early-end',
        'startup-case',
        'startup-assertion',
        'eager-case',
        'eager-assertion',
        'indirect-startup',
    ],
)
def test_streamed_actor_integrity_rejects_startup_and_request_escapes(name, escape):
    source = (ROOT / 'tests/unit/app' / name).read_text()
    reporter, pin = ACTOR_STARTUP[name]
    assert not native_actor_integrity.problems(
        source, reporter, pin, shared_startup=name in SHARED_STARTUP
    ), 'ADR-0076 F2: each escape starts from an admitted actual actor'
    if escape == 'late-begin':
        source = source.replace(
            'gateTurnSelector = Turn.begin',
            'verify(true, "Behavior before permit"); gateTurnSelector = Turn.begin',
            1,
        )
    elif escape == 'foreign-begin':
        source = source.replace('Turn.begin(test, Probe', 'Turn.begin(test, OtherProbe', 1)
    elif escape == 'early-end':
        source = source.replace(
            'function cleanup() {', 'function cleanup() { Turn.end(gateTurnSelector);', 1
        )
    elif escape in {'startup-case', 'startup-assertion', 'indirect-startup'}:
        body = {
            'startup-case': 'test_unrequested();',
            'startup-assertion': 'compare(2+2, 4, "Unrequested correctness");',
            'indirect-startup': 'runUnrequested();',
        }[escape]
        if 'function initTestCase() {' in source:
            source = source.replace(
                'function initTestCase() {', 'function initTestCase() {' + body, 1
            )
        else:
            source = source.replace(
                'function init() {', 'function initTestCase() {' + body + '} function init() {', 1
            )
        if escape == 'indirect-startup':
            source += '\nfunction runUnrequested() { test_unrequested(); }\n'
    elif escape == 'eager-assertion':
        source = source.replace(
            'TestCase {',
            'TestCase { Component.onCompleted: compare(2+2, 4, "Unrequested correctness");',
            1,
        )
    else:
        source = source.replace(
            'TestCase {', 'TestCase { Component.onCompleted: test_unrequested();', 1
        )
    assert native_actor_integrity.problems(
        source, reporter, pin, shared_startup=name in SHARED_STARTUP
    ), (
        'ADR-0076 F2: startup cannot pre-execute correctness, and no row bypasses its request: '
        + name
        + ' '
        + escape
    )


# Regression pins of the reviewed request/result protocol. Runtime controls above
# independently reject foreign acknowledgements, absent/skipped/failed rows and crashes.
NATIVE_PROTOCOL_REGRESSION = {
    'tests/unit/app/NativeTurn.js': (
        '460292a88882d539759a26c1e1254dd3166247eb0ec0013879f9897e67eac248'
    ),
    'tests/integration/app/native_actor.py': (
        'a23f130e37f19925b7f9928c81dc6c9873063a5e6b1eb7e23cd67449f2311605'
    ),
}


def test_measured_startup_keeps_the_reviewed_request_and_result_protocol():
    for relative, expected in NATIVE_PROTOCOL_REGRESSION.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, (
            'ADR-0076 F2: measured startup cannot alter the reviewed per-row barrier, reporter '
            'or request/result accounting without an explicit integrity adaptation: ' + relative
        )
