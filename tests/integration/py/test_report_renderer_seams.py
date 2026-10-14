"""Actual report JavaScript library calls at independent convention seams."""

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/report_units'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())


def observe(tmp_path, *, structure=True):
    source = ROOT / 'data/report/report.js'
    assert source.is_file(), 'The planned report renderer must exist as the actual browser program'
    q = REFERENCE['drawing_seam']['quaternion_wxyz']
    instance = {
        'atom': 0,
        'position': [1.25, 2.5, 3.75],
        'scale': [0.2, 1.5, 0.2],
        'rotation': q,
        'color': '#0c2238',
    }
    pattern = {
        'current': True,
        'x': {'title': 'd (Å)', 'min': 1, 'max': 3},
        'y_main': {'title': 'Intensity', 'min': 0, 'max': 120},
        'y_residual': {'title': 'Residual', 'min': -3, 'max': 3},
        'excluded': [],
        'layout': [
            {'pane': 'main', 'stretch': 0.7, 'fixed_px': 0},
            {'pane': 'bragg', 'stretch': 0, 'fixed_px': 36},
            {'pane': 'residual', 'stretch': 0.3, 'fixed_px': 0},
        ],
        'series': [
            {
                'kind': 'measured',
                'pane': 'main',
                'id': 'meas',
                'style': 'meas',
                'label': 'Measured',
                'x': [1, None, 3],
                'y': [100, None, 110],
                'rows': [0, None, 2],
                'bar_low': [90, None, 100],
                'bar_high': [112, None, 122],
            },
            {
                'kind': 'bragg',
                'pane': 'bragg',
                'id': 'bragg/phase_b',
                'style': 'bragg.1',
                'label': 'phase_b',
                'x': [1.75],
                'y': [1],
                'rows': [0],
                'bar_low': [],
                'bar_high': [],
            },
            {
                'kind': 'residual',
                'pane': 'residual',
                'id': 'resid',
                'style': 'resid',
                'label': 'Residual',
                'x': [1, 3],
                'y': [-2, 2],
                'rows': [0, 2],
                'bar_low': [],
                'bar_high': [],
            },
        ],
        'hover': [[], ['(1 2 3)'], []],
    }
    drawing = {
        'fitted_half_height': 4.25,
        'spheres': [instance, dict(instance, atom=1, position=[-1.25, 2.5, 3.75])],
        'cylinders': [instance],
        'shared': [],
        'triad': [],
    }
    view = {
        'direction': [0, 0, 1],
        'up': [0, 1, 0],
        'magnification': 0.9,
        'pan_x': 0,
        'pan_y': 0,
        'projection': 'Orthographic',
    }
    model = {
        'schema_version': 1,
        'generated': '2026-10-13 16:00 UTC',
        'name': 'seams',
        'title': 'Seams',
        'authors': '',
        'description': '',
        'analysis_categories': [],
        'correlations': None,
        'evolution': [],
        'experiments': [
            {
                'id': 'hand_pattern',
                'pattern': pattern,
                'styles': [
                    {
                        'key': 'meas',
                        'light': REFERENCE['pattern_seam']['measured_colour'],
                        'dark': '#FFFFFF',
                        'mark': 'line+markers+bars',
                        'width_px': 1,
                        'opacity': 1,
                        'marker_px': 3,
                    },
                    {
                        'key': 'bragg.1',
                        'light': '#123456',
                        'dark': '#ABCDEF',
                        'mark': 'markers',
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
                'scene': {
                    'current': True,
                    'has_copies': False,
                    'atoms': [{'asymmetric': True}, {'asymmetric': True}],
                    'bonds': [],
                    'legend': [],
                    'frame': {
                        'target': [0, 0, 0],
                        'view_direction': [0, 0, 1],
                        'view_up': [0, 1, 0],
                        'half_width': 4,
                        'pad': 0.2,
                    },
                },
                'view': view,
                'drawing': drawing,
                'labels': [],
                'along': [view, view, view],
            }
        ],
    }
    model['pattern_styles'] = model['experiments'][0].pop('styles')
    if not structure:
        model['structures'] = []
    model['structure_styles'] = [
        {'key': 'background', 'light': '#ffffff'},
        {'key': 'material.specular', 'value': 0.2},
        {'key': 'material.shininess', 'value': 90},
        {'key': 'light.ambient', 'value': 0.68},
    ]
    for light, strength, right, up, toward in [
        ('key', 1.25, 0.3, 0.45, 0.85),
        ('fill', 0.34, -0.4, -0.2, -0.45),
    ]:
        for suffix, value in [('', strength), ('.right', right), ('.up', up), ('.toward', toward)]:
            model['structure_styles'].append({'key': 'light.' + light + suffix, 'value': value})
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


class ColouredLabel(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.words = []
        self.colours = []
        self.colour = None
        self.stack = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.stack.append((tag, self.colour))
        if tag == 'span':
            for declaration in dict(attrs).get('style', '').split(';'):
                key, _, value = declaration.partition(':')
                if key.strip().lower() == 'color':
                    self.colour = ''.join(value.lower().split())

    def handle_endtag(self, tag):
        while self.stack:
            opened, inherited = self.stack.pop()
            self.colour = inherited
            if opened == tag:
                break

    def handle_data(self, data):
        self.words.append(data)
        if data.strip():
            self.colours.append(self.colour)


def test_pattern_traces_preserve_gaps_asymmetric_errors_and_pane_shares(tmp_path):
    result = observe(tmp_path, structure=False)
    assert result['plots'], 'The actual report renderer must send the presented pattern to Plotly'
    traces = [trace for call in result['plots'] for trace in call[1]]
    measured = next((trace for trace in traces if trace.get('y') == [100, None, 110]), None)
    assert measured is not None, (
        'Presented measured y=[100,null,110] reaches Plotly with its gap; '
        f'actual trace labels and y={[(row.get("name"), row.get("y")) for row in traces]!r}'
    )
    label = ColouredLabel(measured.get('name', ''))
    expected_colour = {'#0c2238', 'rgb(12,34,56)', 'rgba(12,34,56,1)'}
    assert (
        ''.join(label.words) == 'Measured'
        and label.colours
        and all(colour in expected_colour for colour in label.colours)
    ), (
        'The measured legend span retains its label and independent series colour; '
        f'actual name={measured.get("name")!r}'
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
    height = layout['height'] - layout['margin']['t'] - layout['margin']['b']
    seam = REFERENCE['pattern_seam']
    fixed = seam['fixed_bragg_px']
    assert layout['height'] == seam['height'] and height > fixed, (
        'The 600 pixel viewport leaves a positive plot body after its toolbar margins'
    )
    assert shares == pytest.approx(
        sorted([
            seam['stretch']['main'] * (height - fixed) / height,
            fixed / height,
            seam['stretch']['residual'] * (height - fixed) / height,
        ])
    ), (
        'The fixed Bragg pane takes 36 plot-body pixels and stretch panes split the rest 7:3; '
        f'plot height={height!r}, actual domains={shares!r}'
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
        and [m['rotation'][key] for key in ('x', 'y', 'z', 'w')] == pytest.approx(expected)
        for m in result['matrices']
    ), 'The same composed instance keeps its independent position, scale and quaternion'
    assert any(
        instance['geometry'] == 'CylinderGeometry'
        and instance['elements'] == pytest.approx(REFERENCE['drawing_seam']['world_matrix'])
        for instance in result['rendered']
    ), (
        'A visible rod reaches the final render with Rz(-90) scale (.2,1.5,.2) and '
        f'translation (1.25,2.5,3.75); actual instances={result["rendered"]!r}'
    )
    assert result['cameras'], 'The report structure must use an orthographic camera'
    camera = result['cameras'][0]
    assert camera['frustum'][2:4] == pytest.approx([4.25 / 0.9, -4.25 / 0.9]), (
        'The camera divides the explicit core fitted half-height 4.25 by home magnification 0.9; '
        f'actual frustum={camera["frustum"]!r}'
    )
    assert camera['position']['z'] > 0 and camera['up'] == {'x': 0, 'y': 1, 'z': 0}, (
        'A core +z view direction must place the camera above the target with +y up'
    )
