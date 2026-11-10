"""Owner 25826cf2e: report/notebook Plotly specs retain the app's three framed panes.

Reference: app/qml/Components/PatternChart.qml, PaneGrid's closed Rectangle border,
mainView / braggView / residualView and paneGap = em (ADR-0021).
The authored browser input tests layout only; it supplies no diffraction truth.
The existing report-basis gate proves notebook/report drawing-code identity.
"""

import copy
import json
import subprocess

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT


def assert_app_panel_structure(plot):
    layout = plot['layout']
    domains = [layout.get(key, {}).get('domain') for key in ['yaxis', 'yaxis2', 'yaxis3']]
    assert all(isinstance(value, list) and len(value) == 2 for value in domains), (
        'Gate 9: the measured powder chart has three separate pattern, Bragg and residual domains'
    )
    for low, high in domains:
        assert 0 <= low < high <= 1, (
            'Gate 9: every framed panel has positive height inside the chart'
        )
    assert domains[0][0] > domains[1][1] and domains[1][0] > domains[2][1], (
        'Gate 9: positive gaps separate the three panels as in the app chart'
    )
    for index, y in enumerate(['y', 'y2', 'y3']):
        x = ['x', 'x2', 'x3'][index]
        for key in [y.replace('y', 'yaxis'), x.replace('x', 'xaxis')]:
            axis = layout.get(key, {})
            assert axis.get('showline') is True and axis.get('mirror') in {
                True,
                'all',
                'ticks',
                'allticks',
            }, (
                'Gate 9: every panel has a full frame, its top line and a line above Bragg ticks: '
                + key
            )
            assert axis.get('linecolor') not in {None, '', 'transparent', 'rgba(0,0,0,0)'}, (
                'Gate 9: panel frames use a visible axis colour rather than transparent lines'
            )
        assert layout[x.replace('x', 'xaxis')].get('anchor') == y, (
            'Gate 9: each x frame belongs to its own panel rather than joining the three'
        )
    for trace in plot['traces']:
        y = trace.get('yaxis', 'y')
        assert trace.get('xaxis', 'x') == y.replace('y', 'x'), (
            'Gate 9: pattern, tick and residual traces use their own framed panel'
        )


def authored_pattern(rows):
    return {
        'legend': True,
        'x': {'title': '2θ (°)', 'min': 12.5, 'max': 137.25},
        'layout': [
            {'pane': 'main', 'stretch': 0.7, 'fixed_px': 0},
            {'pane': 'bragg', 'stretch': 0, 'fixed_px': 8 + 24 * rows},
            {'pane': 'residual', 'stretch': 0.3, 'fixed_px': 0},
        ],
        'series': [{'kind': 'measured'}],
        'browser': {
            'fixed_height': 8 + 24 * rows,
            'bottom_axis': 'y3',
            'main_title': 'Intensity',
            'residual_title': 'meas - calc',
            'bragg_rows': rows,
            'annotations': [],
            'shapes': [],
            'traces': [
                {'name': name, 'yaxis': y, 'x': [12.5, 137.25], 'y': [1.25, 2.5]}
                for name, y in [
                    ('meas', 'y'),
                    ('calc', 'y'),
                    ('background', 'y'),
                    ('Bragg', 'y2'),
                    ('meas - calc', 'y3'),
                ]
            ],
        },
    }


@pytest.mark.parametrize(('height', 'em', 'rows'), [(360, 13, 1), (780, 19, 3)])
def test_delivered_report_spec_matches_the_apps_three_framed_panels(tmp_path, height, em, rows):
    data = tmp_path / 'authored.json'
    data.write_text(json.dumps({'height': height, 'em': em, 'pattern': authored_pattern(rows)}))
    result = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/tutorial_cases/observe_pattern.cjs'),
            str(ROOT / 'data/report/report.js'),
            str(data),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (
        'Gate 9: the delivered drawing program executes its actual Plotly call: ' + result.stderr
    )
    calls = json.loads(result.stdout)
    assert len(calls) == 1, 'Gate 9: each measured pattern creates one chart specification'
    assert_app_panel_structure(calls[0])


@pytest.mark.parametrize(
    'escape',
    [
        'top-frame',
        'bragg-frame',
        'residual-frame',
        'first-gap',
        'second-gap',
        'trace-panel',
        'transparent-frame',
    ],
)
def test_panel_observer_rejects_missing_frames_joined_domains_and_shared_trace_axes(escape):
    layout = {
        'yaxis': {'domain': [0.5, 1]},
        'yaxis2': {'domain': [0.3, 0.4]},
        'yaxis3': {'domain': [0, 0.2]},
    }
    for x, y in [('x', 'y'), ('x2', 'y2'), ('x3', 'y3')]:
        layout[x.replace('x', 'xaxis')] = {'anchor': y}
    for axis in layout.values():
        axis.update(showline=True, mirror=True, linecolor='#888')
    valid = {'layout': layout, 'traces': [{'yaxis': 'y2', 'xaxis': 'x2'}]}
    assert_app_panel_structure(valid)
    broken = copy.deepcopy(valid)
    if escape == 'transparent-frame':
        broken['layout']['xaxis2']['linecolor'] = 'transparent'
    elif escape.endswith('frame'):
        key = {'top-frame': 'xaxis', 'bragg-frame': 'xaxis2', 'residual-frame': 'xaxis3'}[escape]
        broken['layout'][key]['mirror'] = False
    elif escape == 'first-gap':
        broken['layout']['yaxis2']['domain'][1] = 0.5
    elif escape == 'second-gap':
        broken['layout']['yaxis3']['domain'][1] = 0.3
    else:
        broken['traces'][0]['xaxis'] = 'x'
    with pytest.raises(AssertionError, match='Gate 9:'):
        assert_app_panel_structure(broken)
