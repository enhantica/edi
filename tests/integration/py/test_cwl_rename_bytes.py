"""Renaming TCH profiles must retain their pre-change calculation bytes."""

import json
import platform
from pathlib import Path

import edi as crysta
import numpy as np
import pytest

from tests.fixtures.cwl_family import profiles
from tests.fixtures.cwl_family.regression_comparison import compare, compare_pin, require_reference

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('name', 'token'), [('tch', profiles.TOKENS[4]), ('fcj', profiles.TOKENS[5])]
)
def test_tch_rename_preserves_pre_change_regression_bytes(tmp_path, name, token):
    baseline = ROOT / 'tests/fixtures/cwl_family/tch-regression-Linux.json'
    assert baseline.is_file(), (
        'Every CI platform must have the retained pre-change reference input'
    )
    record = json.loads(baseline.read_text())
    require_reference(record)
    directory = profiles.write_project(tmp_path, token)
    path = directory / 'experiments/bank.edi'
    text = path.read_text().replace('_peak.broad_lorentz_x 0\n', '_peak.broad_lorentz_x .023\n')
    path.write_text(text.replace('_peak.broad_lorentz_y 0\n', '_peak.broad_lorentz_y .047\n'))
    project = crysta.Project.load(directory)
    project.analysis.calculate()
    actual = np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8').tobytes()
    compare_pin(actual, record, name, platform.system())


@pytest.mark.parametrize('native_platform', ['Darwin', 'Windows'])
def test_cross_platform_comparison_admits_only_the_declared_rounding_bound(native_platform):
    reference = np.array([-3.5, 0, 15], dtype='<f8')
    limit = np.maximum(5e-9 * np.abs(reference), 5e-10)
    compare(reference.tobytes(), reference.tobytes(), native_platform)
    inside = reference + limit * 0.5
    compare(inside.tobytes(), reference.tobytes(), native_platform)
    for index in range(len(reference)):
        outside = reference.copy()
        outside[index] += 2 * limit[index]
        with pytest.raises(AssertionError, match='Cross-platform regression'):
            compare(outside.tobytes(), reference.tobytes(), native_platform)


@pytest.mark.parametrize('damage', ['low-bit', 'nonfinite', 'missing-sample'])
def test_native_reference_and_sample_population_cannot_be_weakened(damage):
    reference = np.array([-3.5, 0, 15], dtype='<f8')
    actual = reference.copy()
    if damage == 'low-bit':
        actual[0] = np.nextafter(actual[0], np.inf)
    elif damage == 'nonfinite':
        actual[1] = np.nan
    else:
        actual = actual[:-1]
    with pytest.raises(AssertionError):
        compare(actual.tobytes(), reference.tobytes(), 'Linux')


@pytest.mark.parametrize('name', ['tch', 'fcj'])
def test_darwin_branch_uses_the_retained_pre_change_capture(tmp_path, monkeypatch, name):
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    token = profiles.TOKENS[4 if name == 'tch' else 5]
    test_tch_rename_preserves_pre_change_regression_bytes(tmp_path, name, token)
