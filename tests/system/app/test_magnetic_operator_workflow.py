"""Drive magnetic workflows in the shared production Qt host."""

import pytest

from tests.integration.app.native_actor import streamed_actor  # noqa: F401

CASES = sorted([
    'f_cubic_presets',
    'rendered_bns_number_refusal',
    'rendered_bns_name_refusal',
    'equivalent_signed_rows_retain_derived_identity',
    'legacy_grey_fields_obey_current_cell_admission',
    'start_longitudinal_note',
    'start_uniform_dilution_has_no_note',
    'start_below_cancellation_cutoff',
    'start_above_cancellation_cutoff',
    'start_unlinked_has_no_note',
    'start_mn3o4_has_no_note',
    'start_batch_notes_are_per_candidate',
    'candidate_toggle_preserves_profile_and_free_set',
    'three_candidate_texture_failure_is_atomic',
    'type_iv_adp_cell_and_new_atom_edits_complete',
    'a_setting_presets',
    'half_graph',
    'third_graph',
    'add_links_and_undo',
    'add_unlinked',
    'texture_overflow_is_atomic',
    'calculate_does_not_enable_find_k',
    'type_iv_letters_and_coordinate_edit',
    'unverified_letter_is_retracted',
    'k_field_refusal_is_atomic',
    'bns_field_refusal_is_atomic',
    'single_crystal_enabled_refuses',
    'single_crystal_disabled_refuses',
    'added_children_reopen',
    'find_k_fixed_parent_is_eligible',
    'find_k_coordinate_edit_stales_fit',
    'find_k_calibration_edit_stales_fit',
    'find_k_mask_edit_stales_fit',
    'find_k_disabled_parent_refuses',
    'find_k_profile_edit_stales_fit',
    'find_k_data_ticks_and_choice_reach_graph',
    'find_k_unticking_changes_search_snapshot',
    'find_k_late_choice_after_calibration_edit_refuses',
])

NATIVE_FILE = 'tst_magnetic_operator_workflow.qml'
NATIVE_SELECTORS = {
    f'test_magnetic_workflow_in_the_real_qt_application[{case}]': 'MagneticOperatorWorkflow::test_'
    + case
    for case in CASES
}


@pytest.mark.parametrize('case', CASES)
def test_magnetic_workflow_in_the_real_qt_application(case, streamed_actor):  # noqa: F811
    streamed_actor.run('MagneticOperatorWorkflow::test_' + case)
