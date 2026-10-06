"""Renaming TCH profiles must retain their pre-change calculation bytes."""

import base64
import hashlib
import json
import platform
import shutil
from pathlib import Path

import edi as crysta
import numpy as np
import pytest

from tests.fixtures.cwl_family import profiles
from tests.fixtures.cwl_family.regression_comparison import (
    compare,
    compare_pin,
    read_reference,
    rename_project,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('name', 'token'), [('tch', profiles.TOKENS[4]), ('fcj', profiles.TOKENS[5])]
)
def test_tch_rename_preserves_pre_change_regression_bytes(tmp_path, name, token):
    record = read_reference(ROOT / 'tests/fixtures/cwl_family', platform.system())
    directory = rename_project(ROOT / 'tests/fixtures/cwl_family', tmp_path, name, token, record)
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
def test_darwin_branch_uses_the_retained_pre_change_capture(tmp_path, name):
    # A synthetic selector control, never a numerical expectation for the engine.
    linux = json.loads((ROOT / 'tests/fixtures/cwl_family/tch-regression-Linux.json').read_text())
    (tmp_path / 'tch-regression-Linux.json').write_text(json.dumps(linux))
    with pytest.raises(AssertionError, match='own pre-change platform reference'):
        read_reference(tmp_path, 'Darwin')
    darwin = dict(linux, platform='Darwin', pins=dict(linux['pins']))
    native = np.frombuffer(base64.b64decode(linux['pins'][name]), dtype='<f8').copy()
    native[0] = np.nextafter(native[0], np.inf)
    darwin['pins'][name] = base64.b64encode(native.tobytes()).decode()
    (tmp_path / 'tch-regression-Darwin.json').write_text(json.dumps(darwin))
    selected = read_reference(tmp_path, 'Darwin')
    assert selected['pins'][name] == darwin['pins'][name], (
        'Darwin selects its native byte reference instead of substituting Linux samples'
    )
    compare_pin(native.tobytes(), selected, name, 'Darwin')
    with pytest.raises(AssertionError, match='bytes exactly'):
        compare_pin(base64.b64decode(linux['pins'][name]), selected, name, 'Darwin')


@pytest.mark.parametrize('damage', ['sample', 'width'])
def test_native_capture_inputs_cannot_change_under_the_same_reference(tmp_path, damage):
    # Independently sealed input bytes, a selector control rather than an engine output oracle.
    inputs = tmp_path / 'references'
    shutil.copytree(ROOT / 'tests/fixtures/cwl_family/rename_inputs', inputs / 'rename_inputs')
    hashes = {
        p.relative_to(inputs / 'rename_inputs').as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted((inputs / 'rename_inputs').rglob('*.edi'))
    }
    record = {'platform': 'Darwin', 'input_sha256': hashes}
    rename_project(inputs, tmp_path / 'valid', 'tch', profiles.TOKENS[4], record)
    path = inputs / 'rename_inputs/tch/experiments/bank.edi'
    text = path.read_text()
    text = (
        text.replace('_peak.broad_gauss_w 0.085', '_peak.broad_gauss_w 0.086')
        if damage == 'width'
        else text.replace(' 0 1\n', ' 0 2\n', 1)
    )
    assert text != path.read_text(), (
        'Every input-seal escape must actually change its independent vehicle'
    )
    path.write_text(text)
    with pytest.raises(AssertionError, match='identical serialized'):
        rename_project(inputs, tmp_path / 'damaged', 'tch', profiles.TOKENS[4], record)
