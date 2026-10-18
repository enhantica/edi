"""Run the delivered report script against hand-authored presentation values, offline."""

import html
import json
from pathlib import Path

import edi
import pytest

from tests.fixtures.report_evolution.observe_browser import observe
from tests.integration.py.test_report_save_workflow import command
from tests.integration.py.test_report_storage import source

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'surface', ['python-html', 'notebook', 'python-file', 'core-file', 'cli-save', 'cli-output']
)
def test_all_html_surfaces_deliver_the_same_shared_renderer(tmp_path, surface):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = edi.Project.load(path)
    output = path / 'reports' / (project.name + '.html')
    if surface == 'python-html':
        text = project.report.as_html(offline=False)
    elif surface == 'notebook':
        text = html.unescape(project.report._repr_html_())
    else:
        if surface == 'python-file':
            project.report.save_html(output, offline=False)
        elif surface == 'core-file':
            project.report.save()
        else:
            result = command(
                path, *(['--output', str(output), '--online'] if surface == 'cli-output' else [])
            )
            assert result.returncode == 0, (
                'The actual CLI renderer surface executes: ' + result.stderr
            )
        text = output.read_text()
    assert (ROOT / 'data/report/report.js').read_text() in text, (
        'Each HTML, notebook and saved-file route embeds the shared renderer '
        'that the browser gates execute'
    )


def render_pattern(legend):
    styles = [
        {'key': key, 'light': colour, 'dark': colour, 'width_px': 1, 'mark': 'line'}
        for key, colour in [
            ('meas.0', '#13579b'),
            ('calc', '#b97531'),
            ('bragg.0', '#123456'),
            ('bragg.1', '#789abc'),
        ]
    ]
    series = [
        {
            'kind': 'measured',
            'pane': 'main',
            'label': 'meas',
            'style': 'meas.0',
            'x': [10, 20],
            'y': [2, 3],
        },
        {
            'kind': 'bragg',
            'pane': 'bragg',
            'label': 'Alpha phase',
            'style': 'bragg.0',
            'x': [12, 12],
            'y': [0.25, 0.75],
        },
        {
            'kind': 'bragg',
            'pane': 'bragg',
            'label': 'Beta phase',
            'style': 'bragg.1',
            'x': [16, 16],
            'y': [1.25, 1.75],
        },
    ]
    axis = {
        'title': 'intensity',
        'min': 0,
        'max': 4,
        'segments': [
            {'text': 'meas', 'style': 'meas.0'},
            {'text': ' - ', 'style': ''},
            {'text': 'calc', 'style': 'calc'},
        ],
    }
    pattern = {
        'legend': legend,
        'title': 'Independent fit title',
        'x': {'title': '2theta (deg)', 'min': 10, 'max': 20},
        'y_main': axis,
        'y_residual': axis,
        'series': series,
        'bragg_labels': [
            {'text': 'Alpha phase', 'style': 'bragg.0', 'centre': 0.5},
            {'text': 'Beta phase', 'style': 'bragg.1', 'centre': 1.5},
        ],
        'hover': [[], ['1 0 0', ''], ['0 1 0', '']],
        'excluded': [],
        'layout': [
            {'pane': 'main', 'fixed_px': 0, 'stretch': 0.8},
            {'pane': 'bragg', 'fixed_px': 50, 'stretch': 0},
            {'pane': 'residual', 'fixed_px': 0, 'stretch': 0.2},
        ],
    }
    model = {'pattern_styles': styles, 'experiments': [{'pattern': pattern}]}
    html = '<!doctype html><div class="pattern-figure" data-index="0" style="height:400px"></div>'
    html += (
        '<script id="edi-report-model" type="application/json">' + json.dumps(model) + '</script>'
    )
    # Observe the actual Plotly arguments without loading its library.
    html += """<script>window.Plotly = {newPlot(figure, data, layout) {
      figure.classList.add('js-plotly-plot');
      figure.data = [{line: {layout, data}}]; figure.layout = layout;
      figure.innerHTML = '<svg width="20" height="20"></svg>';
    }};</script><script>"""
    html += (ROOT / 'data/report/report.js').read_text() + '</script>'
    return observe(html)


@pytest.fixture(scope='module')
def rendered_pattern():
    return {legend: render_pattern(legend) for legend in [False, True]}


@pytest.mark.parametrize('legend', [False, True], ids=['legend-hidden', 'legend-visible'])
def test_delivered_renderer_consumes_the_models_legend_flag(rendered_pattern, legend):
    expected, pages = legend, rendered_pattern[legend]
    for page in pages.values():
        assert page['errors'] == [] and len(page['patterns']) == 1, (
            'The actual delivered script executes and reaches exactly one Plotly pattern offline'
        )
        layout = page['patterns'][0]['traces'][0]['line']['layout']
        assert layout['showlegend'] is expected, (
            'HTML honours both independently declared legend states'
        )


@pytest.mark.parametrize('legend', [False, True], ids=['legend-hidden', 'legend-visible'])
def test_delivered_renderer_draws_each_coloured_bragg_label_at_its_row(rendered_pattern, legend):
    pages = rendered_pattern[legend]
    for page in pages.values():
        layout = page['patterns'][0]['traces'][0]['line']['layout']
        annotations = layout.get('annotations', [])
        for name, colour, centre in [
            ('Alpha phase', '#123456', 0.5),
            ('Beta phase', '#789abc', 1.5),
        ]:
            found = [item for item in annotations if name in item.get('text', '')]
            assert len(found) == 1 and colour.lower() in json.dumps(found[0]).lower(), (
                'Each independently named Bragg row is visibly labelled in its '
                'declared style colour'
            )
            assert found[0].get('yref') == 'y2' and found[0].get('y') == centre, (
                'The Bragg label stays at its actual row centre in Bragg-pane coordinates'
            )


@pytest.mark.parametrize('legend', [False, True], ids=['legend-hidden', 'legend-visible'])
def test_delivered_renderer_retains_main_and_residual_title_segments(rendered_pattern, legend):
    pages = rendered_pattern[legend]
    for page in pages.values():
        layout = page['patterns'][0]['traces'][0]['line']['layout']
        for name in ['yaxis', 'yaxis3']:
            title = layout[name]['title']['text']
            assert (
                'meas' in title and 'calc' in title and '#13579b' in title and '#b97531' in title
            ), (
                'Every main and residual title retains the separately coloured '
                'operands and plain separator'
            )
