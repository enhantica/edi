"""Renaming TCH profiles must retain their pre-change calculation bytes."""

import base64
import json
import platform
from pathlib import Path

import edi as crysta
import numpy as np
import pytest

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('name', 'token'), [('tch', profiles.TOKENS[4]), ('fcj', profiles.TOKENS[5])]
)
def test_tch_rename_preserves_pre_change_regression_bytes(tmp_path, name, token):
    baseline = ROOT / 'tests/fixtures/cwl_family' / f'tch-regression-{platform.system()}.json'
    assert baseline.is_file(), 'Each native platform needs a pre-rename engine regression capture'
    record = json.loads(baseline.read_text())
    assert record['kind'] == 'regression-pin', (
        'Engine-produced values must be identified as regression pins'
    )
    directory = profiles.write_project(tmp_path, token)
    path = directory / 'experiments/bank.edi'
    text = path.read_text().replace('_peak.broad_lorentz_x 0\n', '_peak.broad_lorentz_x .023\n')
    path.write_text(text.replace('_peak.broad_lorentz_y 0\n', '_peak.broad_lorentz_y .047\n'))
    project = crysta.Project.load(directory)
    project.analysis.calculate()
    actual = np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8').tobytes()
    assert actual == base64.b64decode(record['pins'][name]), (
        'The renamed TCH or FCJ model must retain the original calculation bytes'
    )
