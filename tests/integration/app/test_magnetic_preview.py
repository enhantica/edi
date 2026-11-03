"""Exercise the magnetic preview through the real Qt production controls."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'sidebar_categories_follow_crysta_dictionary_order',
    'extra_groups_are_single_ordered_and_human_readable',
    'main_order_all_sites_ids_ions_and_symmetry_form',
    'symmetry_form_column_has_room_and_a_gap_after_mz',
    'magnetic_column_shows_none_and_aligns_each_choice',
    'moment_colour_preferences_offer_three_schemes',
    'magnetic_selector_and_scale_use_one_editing_surface',
    'visibility_keeps_camera_and_independent_moments',
    'analysis_contains_only_independent_magnetic_components',
    'nuclear_and_magnetic_tick_rows_cover_the_independent_reflections',
    'phase_contributions_draw_two_independent_curves_and_fills',
    'analysis_filter_counts_match_every_rendered_row',
    'analysis_filter_counts_survive_repeated_fit_publications_and_tabs',
    'fit_from_zero_moments_reaches_reference_and_logs_start',
    'k_editor_refuses_without_changing_the_saved_model',
    'catalogue_count_and_selector_operator_replacement',
    'primitive_propagation_add_refuses_without_losing_rows',
    'propagation_rows_add_remove_and_refuse_duplicates:fraction-first',
    'propagation_rows_add_remove_and_refuse_duplicates:decimal-first',
    'named_magcif_import_uses_the_app_loader:isodistort',
    'named_magcif_import_uses_the_app_loader:fullprof',
]


@pytest.mark.parametrize('case', CASES)
def test_magnetic_preview_uses_rendered_production_controls(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Magnetic app gates require the real Qt Quick Test runner'
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_magnetic_preview.qml'),
            'MagneticPreview::test_' + case,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=140
        if case.startswith(('fit_from_zero', 'analysis_filter_counts_survive'))
        else 90
        if case.startswith(('analysis_filter_counts', 'visibility_keeps_camera'))
        else 45,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The magnetic preview satisfies its rendered contract: ' + output
    )
    assert 'MagneticPreview::test_' in output and '0 failed' in output, (
        'A successful magnetic actor executes real assertions rather than an empty test selection'
    )
    assert 'SKIP' not in output, 'Every magnetic app requirement executes without skipping'
