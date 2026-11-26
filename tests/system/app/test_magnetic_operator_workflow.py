"""Drive magnetic workflows in the shared production Qt host."""

import pytest

from tests.integration.app.native_actor import streamed_actor  # noqa: F401

CASES = sorted([
    'f_cubic_presets',
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
