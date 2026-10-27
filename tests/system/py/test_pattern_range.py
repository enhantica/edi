"""Keep the live Pattern range stable inside its current envelope."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture


@pytest.fixture(scope='module')
def pattern_capture():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    return capture(
        [
            binary,
            '-input',
            ROOT / 'tests/system/app/PatternRange.qml',
            '-o',
            '-,txt',
            'PatternRange::test_drag_holds_and_commits_refit',
        ],
        timeout=90,
    )


def test_parameter_range_holds_during_drag_and_refits_on_commit(pattern_capture):
    status, output = pattern_capture
    assert status == 0, 'The actual drag-and-commit y-range contract must pass: ' + output
    assert 'PASS   : edi_app::PatternRange::test_drag_holds_and_commits_refit()' in output, (
        'The live y-range scenario must execute every required boundary and reset assertion'
    )
    assert '::PatternRange::cleanupTestCase()' in output, (
        'The y-range actor must finish cleanup after real parameter calculations'
    )
