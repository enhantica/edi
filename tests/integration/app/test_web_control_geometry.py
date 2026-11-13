"""Real Qt observations of the production browser control-extent getter."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.build_native import geometry_provider, require_native

ROOT = Path(
    os.environ.get('EDI_WEB_GEOMETRY_SOURCE_ROOT', Path(__file__).resolve().parents[3])
).resolve()
EXTENT_CASES = (
    'empty',
    'populated',
    'empty-again',
    'unclipped',
    'partly-clipped',
    'disabled-ancestor',
    'focus-read',
    'hidden-duplicate',
)


@pytest.fixture(scope='module')
def observations():
    directory = Path(
        os.environ.get('EDI_WEB_GEOMETRY_PROBE_DIR', ROOT / 'build/onboarding-native')
    )
    binary = require_native(ROOT, directory, 'geometry_probe')
    result = subprocess.run(
        [str(binary)],
        cwd=ROOT,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, (
        'The actual Qt geometry carrier must complete every observation: ' + result.stderr
    )
    payload = json.loads(result.stdout)
    assert payload['provider'] == hashlib.sha256(geometry_provider(ROOT).encode()).hexdigest(), (
        'The running geometry artifact must identify the exact current production getter'
    )
    rows = payload['observations']
    assert len({row['case'] for row in rows}) == len(rows), (
        'Every actual Qt observation must have one unambiguous case identity'
    )
    return {row['case']: row for row in rows}


@pytest.mark.parametrize('case', EXTENT_CASES)
def test_transformed_control_extent_is_independent_of_ink_and_clip(case, observations):
    row = observations[case]
    value = row['value']
    assert 'error' not in value, 'One visible real TextInput must expose its declared scene extent'
    expected = {'x': 295, 'y': 130, 'width': 60, 'height': 300}
    for field, number in expected.items():
        assert abs(value[field] - number) < 1e-6, (
            'Declared 200x40 input at20,30 maps through scale1.5/rotation90/translation400,100'
        )
    assert value['visible'] is True, (
        'A real visible input retains effective Qt visibility through projection'
    )
    assert value['enabled'] is (case != 'disabled-ancestor'), (
        'The getter must retain inherited Qt enabled state'
    )
    assert (row['declaredWidth'], row['declaredHeight']) == (200, 40), (
        'The fixture must keep its independent declared input extent'
    )


def test_empty_and_populated_text_have_the_same_target_without_changing_focus(observations):
    assert observations['empty']['inkWidth'] >= 0, (
        'The real empty text/cursor content must have a nonnegative native extent'
    )
    assert observations['empty']['inkWidth'] < observations['empty']['declaredWidth'], (
        'Empty-input ink/cursor extent must differ from its declared control extent'
    )
    assert observations['populated']['inkWidth'] > 0, (
        'The populated control must exercise nonempty real text geometry'
    )
    assert observations['populated']['value']['text'] == 'Fe3+ specimen', (
        'The getter must retain the real populated text'
    )
    for case in ('empty', 'empty-again'):
        text = observations[case]['value']['text']
        assert isinstance(text, str), 'A real control must serialize text as a string'
        assert not text, 'The cleared control must remain actually empty'
    for row in observations.values():
        assert row['editorFocusBefore'] == row['editorFocusAfter'], (
            'Reading geometry must never request editor focus'
        )
        assert row['otherFocusBefore'] == row['otherFocusAfter'], (
            'Reading one control cannot steal focus from another control'
        )
    focus = observations['focus-read']
    assert focus['value']['activeFocus'] == focus['editorFocusBefore'], (
        'Focus must be actual observed Qt activeFocus'
    )


@pytest.mark.parametrize(
    ('case', 'reason'),
    [
        ('hidden-ancestor', 'no visible item'),
        ('duplicate', '2 visible items'),
        ('absent', 'no item'),
    ],
)
def test_geometry_refuses_hidden_duplicate_and_absent_controls(case, reason, observations):
    assert reason in observations[case]['value'].get('error', ''), (
        'A hidden, ambiguous or nonexistent control must not produce a trusted input target'
    )
    expected_name = 'not-a-control' if case == 'absent' else 'editor'
    assert expected_name in observations[case]['value']['error'], (
        'Geometry refusal must identify its actual control and visibility/count reason'
    )


def test_visual_children_remain_discoverable_without_qobject_parentage(observations):
    value = observations['visual-only']['value']
    assert 'error' not in value, (
        'The real visual-only child must remain discoverable through the window scene'
    )
    assert tuple(value[field] for field in ('x', 'y', 'width', 'height')) == (15, 25, 70, 30), (
        'Visual-only delegates must expose their independently declared scene extent'
    )
