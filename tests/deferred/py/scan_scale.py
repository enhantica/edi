"""Deferred scale checks; restore to the system tier with the nightly runner."""

from __future__ import annotations

import hashlib
import struct

import pytest

from tests.conftest import _build_native_observer  # noqa: PLC2701
from tests.fixtures.scan_app.harness import (
    Harness,
    files,
    projection_csv,
    read_csv,
    scale_project,
)
from tests.system.py.test_scan_app_execution import (
    assert_lazy_trace,
    assert_work,
)


@pytest.fixture(scope='module')
def execution(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-scale')
    library, preload = _build_native_observer(root)
    harness = Harness(root, library, preload)
    observed = {'harness': harness, 'root': root}
    scale = scale_project(harness, root / 'scale-100000', 100000)
    observed['scale'] = harness.invoke('scale', scale, observe=True)
    small_scale = scale_project(harness, root / 'scale-1000', 1000)
    observed['virtual1000'] = harness.invoke('virtual', small_scale)
    projection_csv(scale, 100000)
    observed['virtual100000'] = harness.invoke('virtual', scale)
    observed['scaleFiles'] = files(scale)
    return observed


def test_100000_files_reach_the_actual_optimizer_without_retained_payload_growth(execution):
    actual = execution['scale']
    assert actual['entered'] and actual['completed'] == 100000, (
        'Scale: all 100000 synthetic datasets must run through the real worker optimizer'
    )
    grid = [(8.125 + 0.125 * index, 4.5 + index / 10, 1.7) for index in range(11)]
    columns = [point[column] for column in range(3) for point in grid]
    expected_hash = hashlib.sha256(struct.pack('=' + 'd' * len(columns), *columns)).hexdigest()
    assert_work(actual['work'], execution['scaleFiles'], 'scale', expected_hash)
    assert len(read_csv(actual['csv'])) == 100000, (
        'Scale: a completed synthetic fit must write one durable row per dataset'
    )
    assert actual['peak1000'] > 0 and actual['peak100000'] > 0, (
        'Scale: memory measurements must reach both specified completed-file boundaries'
    )
    assert actual['peak100000'] <= 1.1 * actual['peak1000'], (
        'Scale: peak memory after file 100000 must be within ten percent of the peak '
        'after file 1000'
    )


def test_100000_file_median_time_has_no_scan_length_factor(execution):
    actual = execution['scale']
    assert actual['earlySamples'] == actual['lateSamples'] == 1000, (
        'Scale: timing must measure the full 1001..2000 and final-1000 windows'
    )
    assert actual['medianEarly'] > 0 and actual['medianLate'] > 0, (
        'Scale: real per-file timing samples must be positive'
    )
    assert actual['medianLate'] <= 1.2 * actual['medianEarly'], (
        'Scale: the final 1000 median may grow no more than twenty percent over files '
        '1001 through 2000'
    )


def test_100000_file_reads_have_at_most_four_files_of_read_ahead(execution):
    actual = execution['scale']
    assert assert_lazy_trace(actual['trace'], execution['scaleFiles']) == 100000, (
        'Scale: lazy-read evidence must reach all 100000 fitted dataset boundaries'
    )


def test_100000_file_models_lists_and_selector_popup_are_virtualized(execution):
    small, large = execution['virtual1000'], execution['virtual100000']
    for observation, count in ((small, 1000), (large, 100000)):
        assert 'error' not in observation, (
            'Scale: the actual table and selector popup must instantiate before '
            'virtualization is judged'
        )
        assert observation['count'] == count, (
            'Scale: virtualization must use the complete synthetic dataset model'
        )
        assert observation['firstDelegates'] > 0 and observation['lastReached'], (
            'Scale: actual first and last rows must become visible'
        )
        assert observation['firstDelegates'] <= observation['tableBound'], (
            'Scale: the first viewport creates only visible and cached table delegates'
        )
        assert observation['lastDelegates'] <= observation['tableBound'], (
            'Scale: scrolling to the end retains only visible and cached table delegates'
        )
        assert observation['popupOpened'] and observation['popupDelegates'] > 0, (
            'Scale: the actual populated selector popup must open'
        )
        assert observation['popupDelegates'] <= observation['popupBound'], (
            'Scale: the selector popup instantiates only visible and cached entries'
        )
    assert large['modelObjects'] <= small['modelObjects'], (
        'Scale: growing from 1000 to 100000 files must create no per-file QObject population'
    )
