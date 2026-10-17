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
    for tag in ['files', 'mcp-failure', 'dynamic', 'collaboration', 'web', 'plan', 'unknown']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_supported_activity_kinds_share_compact_literal_disclosure(' + tag + ')'
        ) in output, (
            'GUI92: each independently supplied activity category/disclosure executes\n' + output
        )
    for tag in ['explicit-read', 'shell-words']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_activity_categories_require_structured_evidence(' + tag + ')'
        ) in output, 'GUI92: structured action and shell-word negative controls execute\n' + output
    for tag in ['command', 'read', 'technical']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_disclosure_uses_available_caption_width(' + tag + ')'
        ) in output, 'GEO1: actual wide/narrow/restored caption geometry executes\n' + output
    assert (
        'PASS   : edi_app::AssistantInterior::'
        'test_real_selected_file_remove_pairs_with_own_label()'
    ) in output, 'GEO2: actual selected-file geometry and pointer removal execute\n' + output
    for tag in ['read-name', 'list-path', 'search-query', 'opaque-command']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_activity_description_uses_original_structured_source(' + tag + ')'
        ) in output, 'DESC1: structured-source and opaque-description controls execute\n' + output
    for tag in ['read-name', 'tool-name']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_activity_excerpt_keeps_complete_unicode_scalars(' + tag + ')'
        ) in output, 'CAP1: actual scalar-boundary excerpt controls execute\n' + output
    for tag in ['nulls', 'missing-types', 'primitives']:
        assert (
            'PASS   : edi_app::AssistantInterior::'
            'test_malformed_action_arrays_remain_opaque(' + tag + ')'
        ) in output, 'CAP2: opaque action arrays and original selection execute\n' + output
    assert result.returncode == 0, (
        'I16/INT1: actual delegate presentation completes without hidden failures\n' + output
    )
