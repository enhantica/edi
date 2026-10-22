"""Receipts from the real QML application, without provider authentication."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def app_receipts():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    binary = Path(override) if override else ROOT / 'build/app/app/edi_app_tests'
    assert binary.is_file(), 'I16: the real app-build Quick Test host is a prerequisite'
    return subprocess.run(
        [str(binary), '-input', str(Path(__file__).with_name('tst_assistant.qml')), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize(
    'case',
    [
        'test_app_lifetime_survives_project_and_page_changes',
        'test_both_themes_and_live_opposite_placement',
        'test_hiding_retains_conversation_owner_and_width',
        'test_keyboard_toggle_focus_and_multiline_composer',
        'test_narrow_panel_keeps_controls_accessible',
    ],
)
def test_assistant_behavior_in_the_real_qml_host(app_receipts, case):
    output = app_receipts.stdout + app_receipts.stderr
    assert f'PASS   : edi_app::AssistantContract::{case}(' in output, (
        'I16: each assistant behavior must execute and pass in the actual production QML host: '
        + case
        + '\n'
        + output
    )
