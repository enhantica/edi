"""A separate public C++ caller cannot enter through the legacy save delegate."""

import pytest

from tests.system.py import test_save_policy_continuations as policy

tutorial_observer = policy.tutorial_observer


@pytest.mark.parametrize('choice', ['include', 'linked'])
@pytest.mark.parametrize('scope', ['whole', 'generated'])
def test_public_delegate_cannot_borrow_a_pending_save_operation(
    tutorial_observer, tmp_path, choice, scope
):
    row = policy.observe(tutorial_observer, tmp_path, f'public-save/{choice}/{scope}')
    assert not row['available'] or row['refused'], (
        'An unrelated public delegate is unavailable or explicitly refuses the active operation'
    )
    assert row['writes'] == 0 and row['unchanged'], (
        'An unowned delegate never prepares or publishes files using another save operation'
    )
    assert row['questions'] == 1, (
        'The arbitrary caller cannot replace or reuse the owned operation data decision'
    )
