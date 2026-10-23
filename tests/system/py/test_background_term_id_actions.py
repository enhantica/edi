"""Required term ids and singular naming buttons are exercised through real app input."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def actor(file, case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Background id acceptance requires the production Qt host'
    result = subprocess.run(
        [str(runner), '-input', str(ROOT / 'tests/unit/app' / file), case, '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'The real app must meet the stable background id action or required-id refusal contract: '
        + output
    )
    if 'test_missing_' not in case:
        assert (
            'BACKGROUND_NAMING_PRIOR_ACTION recorded=setParametersFree restored=true' in output
        ), 'Naming Undo must restore a recorded preceding free/fixed batch'
    return output


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_order_button_renames_ids_follows_references_undoes_and_reloads(kind):
    output = actor('tst_background_term_ids.qml', 'BackgroundTermIds::test_order_action_' + kind)
    receipts = re.findall(r'BACKGROUND_TERM_IDS (\{[^\n]+\})', output)
    assert len(receipts) == 1, 'Each series type must complete one actual id renaming action'
    assert json.loads(receipts[0]) == {
        'type': kind,
        'ids': ['5', '0', '3'],
        'action': 'background.nameTerms',
    }, 'Id from order must save decimal powers without renumbering or reordering the sparse terms'


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_app_refuses_a_missing_required_term_id_with_a_clear_message(kind):
    output = actor('tst_background_term_ids.qml', 'BackgroundTermIds::test_missing_' + kind)
    assert 'BACKGROUND_TERM_IDS_REFUSED ' + kind in output, (
        'The app must refuse the actual missing-id input and name its required background id field'
    )


def test_position_button_retains_reference_rewriting_and_undo_with_singular_label():
    actor(
        'tst_background_position_names.qml',
        'BackgroundPositionNames::test_rounding_references_and_one_undo',
    )
