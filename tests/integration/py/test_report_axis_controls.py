"""Actual axis buttons consume authored views using the vendored Three math."""

import json
import subprocess
from pathlib import Path

import edi
import pytest

from tests.unit.py.test_report_collection_domain import model

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('instances', ['spheres', 'shared', 'both'])
def test_all_delivered_axis_buttons_consume_the_complete_collection(tmp_path, instances):
    document = model()
    structure = document['structures'][0]
    structure['scene']['current'] = True
    if instances == 'spheres':
        structure['drawing']['shared'] = []
    elif instances == 'shared':
        structure['drawing']['spheres'] = []
    structure['scene']['frame']['target'] = [1.25, 2.5, 3.75]
    directions = [[1, 0, 0], [0, -1, 0], [0, 0, 1]]
    ups = [[0, 0, 1], [0, 0, 1], [0, 1, 0]]
    for index in range(3):
        structure['along'][index].update(
            direction=directions[index], up=ups[index], magnification=2
        )
    restored = edi.ReportModel.from_json(json.dumps(document))
    data = tmp_path / 'model.json'
    data.write_text(restored.to_json())
    result = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/report_units/observe_renderer.js'),
            str(ROOT / 'data/report/report.js'),
            str(data),
            '--click-axes',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'The delivered report script executes against the actual vendored Three math: '
        + result.stderr
    )
    clicks = json.loads(result.stdout)['axisClicks']
    assert [click['title'] for click in clicks] == [
        'View along a',
        'View along b',
        'View along c',
    ], 'All three real axis controls are present and actually clicked'
    centre = structure['scene']['frame']['target']
    for index, click in enumerate(clicks):
        assert 'error' not in click, (
            'Every axis control addresses an existing view without a JavaScript exception'
        )
        assert click['up'] == ups[index], (
            'Each axis button consumes its independently authored up vector'
        )
        delta = [click['position'][i] - centre[i] for i in range(3)]
        length = sum(value * value for value in delta) ** 0.5
        assert [value / length for value in delta] == pytest.approx(
            directions[index], abs=1e-12
        ), 'Each axis button looks along its independently authored non-home direction'
        assert click['top'] == pytest.approx(structure['drawing']['fitted_half_height'] / 2), (
            'Axis views consume the nonidentity magnification rather than the home view'
        )
