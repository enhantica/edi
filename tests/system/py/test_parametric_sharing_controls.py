"""Shared-group edits exercise the production Qt parameter and undo paths."""

import pytest

from tests.integration.app import native_actor

CASES = (
    'bulk_shared_is_one_undo',
    'column_follows_fitting_mode',
    'group_edits_and_undo',
    'unshareable_rows_explain_why',
)
NATIVE_FILE = 'tst_parametric_sharing.qml'
NATIVE_SELECTORS = {
    f'test_sharing_controls[{case}]': f'ParametricSharing::test_{case}' for case in CASES
}
streamed_actor = native_actor.streamed_actor


@pytest.mark.parametrize('case', CASES)
def test_sharing_controls(case, streamed_actor):
    streamed_actor.run(f'ParametricSharing::test_{case}')
