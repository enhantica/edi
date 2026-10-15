"""Real production transcript presentation; no fabricated connected VM."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_actual_transcript_delegate_author_semantics():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'I16/INT1: coherent actual native Qt Quick Test runner is required'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(Path(__file__).with_name('tst_assistant_interior.qml')),
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    output = result.stdout + result.stderr
    for tag in ['human', 'assistant', 'activity-control']:
        assert (
            'PASS   : edi_app::AssistantInterior::test_literal_rows_keep_author_information('
            + tag
            + ')'
        ) in output, (
            'I16/INT1: every actual author kind and literal-body control executes\n' + output
        )
    for tag in ['running', 'completed', 'failed']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_command_activity_is_compact_and_discloses_originals(' + tag + ')'
        ) in output, 'ACT1: every actual command status/disclosure control executes\n' + output
    assert (
        'PASS   : edi_app::AssistantInterior::'
        'test_command_same_identity_updates_and_reused_row_retires_expansion()'
    ) in output, 'ACT1: same-command updates and different-command reuse execute\n' + output
    for tag in ['interrupted', 'failed']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_public_command_retirement_overrides_unfinished_original(' + tag + ')'
        ) in output, (
            'ACT1: public terminal status over unfinished command evidence executes\n' + output
        )
    assert result.returncode == 0, (
        'I16/INT1: actual delegate presentation completes without hidden failures\n' + output
    )
