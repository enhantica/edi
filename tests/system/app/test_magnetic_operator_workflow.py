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
    'a10_refusal_ignores_renamed_and_reused_parent_name',
    'half_graph',
    'third_graph',
    'add_links_and_undo',
    'add_unlinked',
    'texture_overflow_is_atomic',
    'type_iv_letters_and_coordinate_edit',
    'unverified_letter_is_retracted',
    'k_field_refusal_is_atomic',
    'bns_field_refusal_is_atomic',
    'single_crystal_enabled_refuses',
    'single_crystal_disabled_refuses',
    'added_children_reopen',
    'find_k_disabled_parent_refuses',
    'find_k_late_choice_after_calibration_edit_refuses',
    'structure_analysis_entry_keeps_k_in_popup',
    'find_k_marks_without_kept_fit',
    'find_k_multiple_crystal_links_refuse',
    'find_k_gamma_labels_forbidden_and_allowed_marks',
    'find_k_mask_excludes_observed_peak',
    'find_k_table_analyse_add_stays_on_pattern',
    'find_k_late_choice_after_link_edit_refuses',
    'find_k_late_choice_after_mask_edit_refuses',
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
