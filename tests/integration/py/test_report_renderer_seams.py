"""Actual report JavaScript library calls at independent convention seams."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/report_units'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())


def observe(tmp_path):
    source = ROOT / 'data/report/report.js'
    assert source.is_file(), 'The planned report renderer must exist as the actual browser program'
    q = REFERENCE['drawing_seam']['quaternion_wxyz']
    instance = {
        'position': {'x': 1.25, 'y': 2.5, 'z': 3.75},
        'scale': {'x': 0.2, 'y': 1.5, 'z': 0.2},
        'rotation': q,
        'color': {'r': 12, 'g': 34, 'b': 56},
    }
    pattern = {
        'current': True,
        'x': {'title': 'd (Å)', 'min': 1, 'max': 3},
        'y_main': {'title': 'Intensity', 'min': 0, 'max': 120},
        'y_residual': {'title': 'Residual', 'min': -3, 'max': 3},
        'excluded': [],
        'layout': [
            {'pane': 'Main', 'stretch': 0.7, 'fixed_px': 0},
            {'pane': 'Bragg', 'stretch': 0, 'fixed_px': 36},
            {'pane': 'Residual', 'stretch': 0.3, 'fixed_px': 0},
        ],
        'series': [
            {
                'kind': 'Measured',
                'pane': 'Main',
                'id': 'meas',
                'style': 'meas',
                'label': 'Measured',
                'points': [{'x': 1, 'y': 100}, {'x': None, 'y': None}, {'x': 3, 'y': 110}],
                'rows': [0, None, 2],
                'bar_low': [90, None, 100],
                'bar_high': [112, None, 122],
            },
            {
                'kind': 'BraggTicks',
                'pane': 'Bragg',
                'id': 'bragg/phase_b',
                'style': 'bragg.1',
                'label': 'phase_b',
                'points': [{'x': 1.75, 'y': 1}],
                'rows': [0],
                'bar_low': [],
                'bar_high': [],
            },
            {
                'kind': 'Residual',
                'pane': 'Residual',
                'id': 'resid',
                'style': 'resid',
                'label': 'Residual',
                'points': [{'x': 1, 'y': -2}, {'x': 3, 'y': 2}],
                'rows': [0, 2],
                'bar_low': [],
                'bar_high': [],
            },
        ],
    }
    drawing = {
        'fitted_half_height': 4.25,
        'spheres': [instance, dict(instance, position={'x': -1.25, 'y': 2.5, 'z': 3.75})],
        'cylinders': [instance],
        'shared': [],
        'triad': [],
    }
    view = {
        'direction': {'x': 0, 'y': 0, 'z': 1},
        'up': {'x': 0, 'y': 1, 'z': 0},
        'magnification': 1,
        'pan_x': 0,
        'pan_y': 0,
        'projection': 'Orthographic',
    }
    model = {
        'schema_version': 1,
        'generated': '2026-10-13 16:00 UTC',
        'software': {},
        'project': {'name': 'seams', 'title': 'Seams', 'authors': '', 'description': ''},
        'analysis': {'parameters': [], 'correlations': None, 'evolution': []},
        'experiments': [
            {
                'id': 'hand_pattern',
                'pattern': pattern,
                'styles': [
                    {
                        'key': 'meas',
                        'light': '#000000',
                        'dark': '#FFFFFF',
                        'mark': 'circle',
                        'width_px': 1,
                        'opacity': 1,
                        'marker_px': 3,
                    },
                    {
                        'key': 'bragg.1',
                        'light': '#123456',
                        'dark': '#ABCDEF',
                        'mark': 'line-ns-open',
                        'width_px': 1,
                        'opacity': 1,
                        'marker_px': 4,
                    },
                    {
                        'key': 'resid',
                        'light': '#777777',
                        'dark': '#888888',
                        'mark': 'line',
                        'width_px': 1,
                        'opacity': 1,
                        'marker_px': 0,
                    },
                ],
            }
        ],
        'structures': [
            {
                'id': 'hand_structure',
                'scene': {'frame': {'target': {'x': 0, 'y': 0, 'z': 0}}},
                'view': view,
                'drawing': drawing,
            }
        ],
    }
    path = tmp_path / 'model.json'
    path.write_text(json.dumps(model, ensure_ascii=False, allow_nan=False))
    result = subprocess.run(
        ['node', str(FIXTURE / 'observe_renderer.js'), str(source), str(path)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 0, (
        'The actual renderer must execute at its browser library seam: ' + result.stderr
    )
    return json.loads(result.stdout)


def test_pattern_traces_preserve_gaps_asymmetric_errors_and_pane_shares(tmp_path):
    result = observe(tmp_path)
    assert result['plots'], 'The actual report renderer must send the presented pattern to Plotly'
    traces = [trace for call in result['plots'] for trace in call[1]]
    measured = next((trace for trace in traces if trace.get('y') == [100, None, 110]), None)
    assert measured is not None, (
        'Presented measured points must reach Plotly with their null gap intact'
    )
    assert measured.get('connectgaps', False) is False, (
        'Plotly must never connect a presented excluded-region gap'
    )
    error = measured['error_y']
    assert error.get('symmetric') is False, 'Unequal presented bar ends must remain asymmetric'
    assert error['arrayminus'][0] == 10 and error['array'][0] == 12, (
        'Presented bar ends 90 and 112 around 100 must become minus 10 and plus 12'
    )
    layout = next(call[2] for call in result['plots'] if measured in call[1])
    shares = sorted(
        axis['domain'][1] - axis['domain'][0]
        for name, axis in layout.items()
        if name.startswith('yaxis') and 'domain' in axis
    )
    assert shares == pytest.approx(sorted([0.658, 0.06, 0.282])), (
        'At height 600 the two fixed Bragg rows take 0.06 and stretch panes take 0.658 and 0.282'
    )
    assert any(trace.get('marker', {}).get('color') == '#123456' for trace in traces), (
        'The second phase must resolve its light colour from the bragg.1 core style row'
    )


def test_drawing_quaternion_order_unit_geometry_and_camera_frame(tmp_path):
    result = observe(tmp_path)
    expected = REFERENCE['drawing_seam']['quaternion_xyzw']
    assert any(q == pytest.approx(expected) for q in result['quaternions']), (
        'The nonidentity core wxyz rotation must become three.js xyzw without changing its sign'
    )
    cylinders = [g for g in result['geometries'] if g['name'] == 'CylinderGeometry']
    assert cylinders and cylinders[0]['args'][:3] == [1, 1, 1], (
        'The renderer must use the core instance contract: unit radius and length along +y'
    )
    assert result['matrices'], (
        'Core drawing instances must be placed through real composed mesh transforms'
    )
    assert any(
        m['position'] == {'x': 1.25, 'y': 2.5, 'z': 3.75}
        and m['scale'] == {'x': 0.2, 'y': 1.5, 'z': 0.2}
        for m in result['matrices']
    ), 'Instance positions and scales must reach the renderer unchanged'
    assert result['cameras'], 'The report structure must use an orthographic camera'
    camera = result['cameras'][0]
    assert camera['frustum'][2:4] == [4.25, -4.25], (
        'The camera must retain the core fitted half-height'
    )
    assert camera['position']['z'] > 0 and camera['up'] == {'x': 0, 'y': 1, 'z': 0}, (
        'A core +z view direction must place the camera above the target with +y up'
    )
