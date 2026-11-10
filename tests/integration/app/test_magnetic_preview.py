"""Exercise the magnetic preview through the real Qt production controls."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'converted_forbidden_direction_refuses:polar',
    'converted_forbidden_direction_refuses:cartesian',
    'converted_forbidden_direction_refuses:negative-modulus',
    'converted_forbidden_direction_refuses:polar-range',
    'sidebar_categories_follow_crysta_dictionary_order',
    'extra_groups_are_single_ordered_and_human_readable',
    'main_order_all_sites_ids_ions_and_symmetry_form',
    'monoclinic_moment_form_selector_edits_and_saves_crystal_axes',
    'derived_moment_uncertainties_use_the_applicable_covariance:fitted',
    'derived_moment_uncertainties_use_the_applicable_covariance:fallback',
    # Historical node name retained; the retired M-squared bound now means undefined s.u.
    'zero_moment_modulus_uses_the_fitted_bound',
    'relation_graph_uncertainty_states:cell-chain',
    'relation_graph_uncertainty_states:cell-chain-undefined',
    'relation_graph_uncertainty_states:fixed',
    'relation_graph_uncertainty_states:undefined',
    'relation_graph_uncertainty_states:missing-pair',
    'relation_graph_uncertainty_states:correlated',
    'relation_graph_uncertainty_states:unrelated-undefined',
    'relation_graph_uncertainty_states:tied',
    'relation_graph_uncertainty_states:undefined-tied',
    'relation_graph_uncertainty_states:chain',
    'relation_graph_uncertainty_states:cross-undefined',
    'relation_graph_uncertainty_states:constant',
    'relation_graph_uncertainty_states:symmetry-tied',
    'undetermined_moment_angles_have_no_uncertainty:zero',
    'undetermined_moment_angles_have_no_uncertainty:pole',
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


@pytest.fixture
def native_case_observation(case, request):
    if case == 'fit_from_zero_moments_reaches_reference_and_logs_start':
        return request.getfixturevalue('magnetic_fit_starts')
    return None


@pytest.mark.parametrize('case', CASES)
def test_magnetic_preview_uses_rendered_production_controls(case, native_case_observation):
    if native_case_observation is not None:
        return
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
        timeout=240
        if case == 'visibility_keeps_camera_and_independent_moments'
        else 140
        if case.startswith(('fit_from_zero', 'analysis_filter_counts_survive'))
        else 90
        if case.startswith('analysis_filter_counts')
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


@pytest.fixture(scope='module')
def magnetic_fit_starts():
    """One real pair of fits shared by independent UI, minimum and notice checks."""
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Magnetic fit starts require the real app test host'
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_magnetic_preview.qml'),
            'MagneticPreview::test_fit_from_zero_moments_reaches_reference_and_logs_start',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=140,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '0 failed' in output and 'SKIP' not in output, (
        'The actual app completes both distinct magnetic starts without a skipped actor: ' + output
    )
    prefix = 'MAGNETIC_FIT_STARTS '
    rows = [line.split(prefix, 1)[1] for line in output.splitlines() if prefix in line]
    assert len(rows) == 1, 'The completed native actor returns exactly one full two-start receipt'
    return json.loads(rows[0])


@pytest.mark.parametrize('start', ['baseline', 'fromZero'])
def test_both_magnetic_starts_reach_the_independent_fullprof_interval(start, magnetic_fit_starts):
    expected = json.loads(
        (ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/expected.json').read_text()
    )['variants']['form-factor-j0']['quantities']
    result = magnetic_fit_starts[start]
    assert abs(result['rwp'] - expected['rwp']['value']) <= (
        expected['rwp']['value'] * expected['rwp']['tol_rel']
    ), 'Each magnetic start reaches the unchanged independent FullProf Rwp interval'
    components = {row['name']: row['value'] for row in result['components']}
    for name, reference in expected.items():
        if name.startswith('param.'):
            assert name in components, 'Each independently referenced moment is present in the fit'
            assert abs(abs(components[name]) - abs(reference['value'])) <= reference['tol_abs'], (
                'Each fitted moment magnitude retains its independent FullProf absolute tolerance'
            )


def test_zero_magnetic_start_notice_and_minimum_agree(magnetic_fit_starts):
    before, zero = magnetic_fit_starts['baseline'], magnetic_fit_starts['fromZero']
    assert before['notices'] == 0 and zero['notices'] > 0, (
        'Info names the one-magneton adjustment only for the all-zero user start'
    )
    reference = json.loads(
        (ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/expected.json').read_text()
    )['variants']['form-factor-j0']['quantities']['rwp']
    assert abs(before['rwp'] - zero['rwp']) <= reference['value'] * reference['tol_rel'], (
        'The zero and nonzero user starts reach the same minimum within the reference tolerance'
    )
