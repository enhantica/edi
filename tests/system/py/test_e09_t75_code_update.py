"""Review-11 F17: normal squash and interrupted update handoffs converge."""

from __future__ import annotations

import pytest

from tests.system.py.test_e09_t75_sdk_update import update


@pytest.mark.parametrize('accident', ['squashed-pin', 'lost-dispatch'])
def test_f17_retained_squash_pin_and_partial_dispatch_remain_updatable(tmp_path, accident):
    runs, state, _, _ = update(tmp_path, defect=accident)
    assert runs[-1].returncode == 0, (
        f' F17 a valid retained pin or retried handoff must converge: {runs[-1].stderr}'
    )
    assert state['dispatched'] == ['crysta-sdk/' + state['sha'][:12]], (
        ' F17 the newest complete committed pin must get its required CI dispatch'
    )
