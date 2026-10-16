"""Real Main popup checks under owner 99d50f71f; no provider fixture."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def popup171_owned_environment(captures):
    # Every possible full-actor invocation is deliberately guarded against a
    # bundled/default vendor runtime, including the original popup fixture.
    owned = captures / 'owned-peer'
    owned.mkdir(exist_ok=True)
    executable = owned / 'codex'
    executable.write_text(
        f'#!{sys.executable}\n'
        + (ROOT / 'tests/integration/py/assistant_vm_probe/codex_stdio_peer.py').read_text()
    )
    executable.chmod(0o700)
    config = owned / 'peer-input.json'
    config.write_text(
        json.dumps({
            'scenario': 'fileauth',
            'report_page_reply': True,
            'trace': str(owned / 'original-client-lines.jsonl'),
        })
    )
    environment = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_CODEX_DEVELOPMENT_EXECUTABLE': str(executable.resolve()),
        'EDI_TEST_CODEX_PEER_INPUT': str(config.resolve()),
    }
    for key, leaf in [
        ('TMPDIR', 'tmp'),
        ('XDG_CONFIG_HOME', 'config'),
        ('XDG_DATA_HOME', 'data'),
        ('XDG_CACHE_HOME', 'cache'),
    ]:
        directory = owned / leaf
        directory.mkdir(exist_ok=True)
        environment[key] = str(directory.resolve())
    return environment


@pytest.fixture(scope='module')
def popup_receipt(tmp_path_factory):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'I16/popup: coherent real native Quick Test runner is required'
    captures = Path(
        os.environ.get('EDI_ASSISTANT_POPUP_CAPTURE_DIR', tmp_path_factory.mktemp('popup'))
    )
    captures.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run(
            [
                str(runner),
                '-input',
                str(Path(__file__).with_name('tst_assistant_popup.qml')),
                '-o',
                '-,txt',
            ],
            cwd=captures,
            env=popup171_owned_environment(captures),
            capture_output=True,
            text=True,
            timeout=90,  # Prior whole-actor operational allowance; Qt assertions stay bounded.
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        # subprocess may retain bytes even with text=True. Keep raw evidence and
        # expose it in the unchanged timeout failure; never turn timeout into pass.
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            destination = captures / ('popup-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(
                str(destination) + '\n' + raw.decode('utf-8', errors='backslashreplace')
            )
        raise


@pytest.mark.parametrize(
    'case',
    [
        'test_home_appbar_only_and_no_auto_dismiss',
        'test_workflow_same_sidebar_and_live_state',
        'test_keyboard_can_return_to_appbar',
        'test_focus_restore_uses_current_scope',
        'test_navigation_keeps_visible_popup_fixed',
    ],
)
def test_actual_popup_owner_contract(popup_receipt, case):
    output = popup_receipt.stdout + popup_receipt.stderr
    assert f'PASS   : edi_app::AssistantPopup::{case}(' in output, (
        'I16/popup: genuine Main executes the owner appbar-only sidebar contract: '
        + case
        + '\n'
        + output
    )
    assert 'FAIL!' not in output and popup_receipt.returncode == 0, (
        'I16/popup: all actual popup rows and capture callbacks '
        'complete without a hidden failure\n' + output
    )


def test_report171_real_retained_anchor_navigates_current_main_report(tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'REPORT171 SETUP: coherent actual Main Qt runner required'
    environment = popup171_owned_environment(tmp_path)
    # Declared supported test hover policy, not production/Mac default proof.
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    try:
        result = subprocess.run(
            [
                str(runner),
                '-input',
                str(Path(__file__).with_name('tst_assistant_popup.qml')),
                'AssistantPopup::test_report171_chat_anchor_uses_existing_current_report_page',
                '-o',
                '-,txt',
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode()
            destination = tmp_path / ('report171-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    output = result.stdout + result.stderr
    for case in ['current', 'replacement', 'missing', 'disabled', 'protected-other']:
        assert (
            'PASS   : edi_app::AssistantPopup::'
            'test_report171_chat_anchor_uses_existing_current_report_page(' + case + ')'
        ) in output, (
            'REPORT171: real retained anchor executes current-page/guard case '
            + case
            + '\n'
            + output
        )
    assert result.returncode == 0 and 'FAIL!' not in output, (
        'REPORT171: all actual pointer/navigation cases settle within original actor bound\n'
        + output
    )
