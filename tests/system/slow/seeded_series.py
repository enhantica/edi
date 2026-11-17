"""One hundred copied NCAF points from identical starts for each explicit descent."""

import pytest

from tests.system.py.test_joint_series_seeded import check_seeded_fit


@pytest.mark.parametrize('descent', ['fast_descent', 'ladder'])
def test_slow_fullprof_seeded_points(tmp_path, descent):
    check_seeded_fit(tmp_path, 100, descent, small=False)
