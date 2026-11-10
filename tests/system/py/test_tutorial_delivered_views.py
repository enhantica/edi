"""Owner 37570e232 to 9d8a4cae6: app readouts, shared drawing and complete view toolbars."""

import json
import re

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.browser import observe_html
from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.pipeline import convert, executed_inputs, stage
from tests.fixtures.tutorial_cases.presentation import svg_documents, svg_identity
from tests.integration.py.test_tutorial_empty_project import api
from tests.system.py.test_tutorial_pattern_toolbar import app_buttons, assert_app_toolbar

REFERENCE = json.loads((ROOT / 'tests/fixtures/tutorial_cases/app_chart.json').read_text())


@pytest.fixture(scope='module')
def delivered_views(tmp_path_factory):
    folder = tmp_path_factory.mktemp('shared-delivered-views')
    project = api().Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project')
    project.analysis.calculate()
    project.report.html_offline = True
    report = project.report.as_html(offline=True, excluded=['data', 'reflections'])
    root = stage(folder / 'conversion')
    executed_inputs(root)
    notebook = json.loads((root / 'docs/user/tutorials/pd-neut-cwl_lbco-hrpt.ipynb').read_text())
    # These are real public display outputs from this exact same calculated project.
    # No fit answer is authored, and the converter must preserve the report's drawing.
    for cell, view in zip(
        notebook['cells'][1:],
        [project.display.pattern(), project.display.parameters.free()],
        strict=True,
    ):
        cell['metadata'] = {}
        cell['outputs'] = [
            {
                'output_type': 'display_data',
                'metadata': {},
                'data': {'text/html': view._repr_html_()},
            }
        ]
    (root / 'docs/user/tutorials/pd-neut-cwl_lbco-hrpt.ipynb').write_text(json.dumps(notebook))
    conversion = convert(root)
    assert conversion.returncode == 0, (
        'Gate 9: native notebook conversion preserves the actual report outputs: '
        + conversion.stdout
        + conversion.stderr
    )
    page = root / 'website/surfaces/docs/python/tutorials/cases/pd-neut-cwl_lbco-hrpt.md'
    assert page.is_file(), 'Gate 9: comparison uses a native converted notebook page'
    from bs4 import BeautifulSoup  # noqa: PLC0415 - parse the actual converted page

    frames = BeautifulSoup(page.read_text(), 'html.parser').find_all('iframe')
    assert len(frames) == 2, 'Gate 9: the native page retains both actual view documents'
    reference = {
        **REFERENCE,
        'hover_button': next(
            button['tips'][0] for button in app_buttons() if button['id'].endswith('.hover')
        ),
    }
    results = {'report': observe_html(report, folder / 'report', reference=reference)}
    for index, frame in enumerate(frames):
        source = frame.get('srcdoc')
        if source is None:
            source = (page.parent / frame['src']).resolve().read_text()
        kind = 'pattern' if index == 0 else 'parameters'
        results[kind] = observe_html(
            source, folder / ('notebook-' + str(index)), reference=reference
        )
    results['legend'] = json.loads(project.report.model().to_json())['experiments'][0]['pattern'][
        'legend'
    ]
    return results


@pytest.mark.parametrize('surface', ['report', 'pattern'])
@pytest.mark.parametrize('target', ['point', 'tick'])
def test_hover_box_matches_the_app_readout_including_miller_indices(
    surface, target, delivered_views
):
    actual = delivered_views[surface]['hovers'].get(target, {})
    assert actual.get('distance', 1) < 1e-8, (
        'Gate 9: the browser hovers the actual nontrivial app reference point or Bragg tick'
    )
    lines = [row['text'] for row in REFERENCE[target]['lines']]
    assert any(all(line in box['text'] for line in lines) for box in actual.get('boxes', [])), (
        'Gate 9: one visible hover box contains every app line, not a per-curve label: '
        + repr(lines)
    )


@pytest.mark.parametrize('surface', ['report', 'pattern'])
def test_bragg_ticks_use_the_actual_app_structure_colour(surface, delivered_views):
    ticks = [row for row in delivered_views[surface]['traces'] if row.get('yaxis') == 'y2']
    assert ticks, 'Gate 9: the real browser draws Bragg ticks from the measured case'
    expected = next(
        row['light'] for row in REFERENCE['styles'] if row['key'] == REFERENCE['tick']['style']
    )

    assert all(
        (row.get('marker') or {}).get('color', (row.get('line') or {}).get('color', '')).lower()
        == expected.lower()
        for row in ticks
    ), 'Gate 9: Bragg ticks follow the actual app structure colour without a palette offset'


@pytest.mark.parametrize('surface', ['report', 'pattern'])
@pytest.mark.parametrize('target', ['point', 'tick'])
def test_hover_lines_and_segments_have_the_apps_semantic_colours(surface, target, delivered_views):
    lines = REFERENCE[target]['lines']
    boxes = delivered_views[surface]['hovers'][target].get('boxes', [])
    boxes = [box for box in boxes if all(line['text'] in box['text'] for line in lines)]
    assert boxes, 'Gate 9: hover colour checks observe one complete app readout'
    colours = {row['key']: row['light'] for row in REFERENCE['styles']}
    for line in lines:
        segments = line['segments'] or [{'text': line['text'], 'style': line['style']}]
        for segment in segments:
            if not segment['style']:
                continue
            colour = colours[segment['style']].lstrip('#')
            rgb = 'rgb(' + ', '.join(str(int(colour[i : i + 2], 16)) for i in (0, 2, 4)) + ')'
            assert any(
                span['text'] == segment['text'] and rgb in {span['colour'], span['fill']}
                for box in boxes
                for span in box['spans']
            ), 'Gate 9: each hover line or rich-text segment has its exact app semantic colour'


@pytest.mark.parametrize('surface', ['report', 'pattern'])
def test_bragg_structure_labels_have_the_app_structure_icon_and_colour(surface, delivered_views):
    labels = delivered_views[surface]['structureLabels']
    assert labels, 'Gate 9: the Bragg row names its structure with the app structure icon'
    references = json.loads((ROOT / 'tests/fixtures/tutorial_cases/glyphs.json').read_text())[
        'toolbar'
    ]
    reference = references['layer-group']
    expected_icon = (reference['path_sha256'], reference['viewBox'])
    colour = next(
        row['light'] for row in REFERENCE['styles'] if row['key'] == REFERENCE['tick']['style']
    )
    rgb = 'rgb(' + ', '.join(str(int(colour[i : i + 2], 16)) for i in (1, 3, 5)) + ')'
    assert any(
        label['colour'] == rgb
        and expected_icon
        in [
            svg_identity(icon)
            for icon in svg_documents(BeautifulSoup(label['html'], 'html.parser'))
        ]
        for label in labels
    ), 'Gate 9: Bragg labels use the same app per-structure colour and glyph'


def drawing_without_document_typography(value):
    if isinstance(value, list):
        return [drawing_without_document_typography(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key.endswith('font') and isinstance(item, dict):
            result[key] = {
                name: '<document typography>'
                if name in {'family', 'size', 'color', 'weight'}
                else drawing_without_document_typography(field)
                for name, field in item.items()
            }
        else:
            result[key] = drawing_without_document_typography(item)
    return result


def test_report_and_native_notebook_page_share_the_chart_spec_apart_from_document_typography(
    delivered_views,
):
    report = delivered_views['report']['requests']
    notebook = delivered_views['pattern']['requests']
    assert report and notebook, 'Gate 9: compare actual Plotly calls from both delivered views'
    # c8208962d explicitly keeps print typography in reports and page typography in docs.
    # The built-page typography gates and app colour witnesses test those permitted differences.
    assert drawing_without_document_typography(report[0]) == drawing_without_document_typography(
        notebook[0]
    ), 'Gate 9: both views share the complete chart spec apart from declared document typography'


def test_report_and_native_notebook_parameter_tables_share_stripes_and_padding(delivered_views):
    notebook = delivered_views['parameters']['tables']
    assert notebook, 'Gate 9: the native notebook page draws its actual parameter table'
    for table in notebook:
        matches = [
            row
            for row in delivered_views['report']['tables']
            if row['headers'] == table['headers']
        ]
        assert matches, 'Gate 9: the HTML report contains the same parameter table vocabulary'
        assert any(
            row['cells'] == table['cells'] and row['stripes'] == table['stripes']
            for row in matches
        ), 'Gate 9: report and notebook tables have identical computed padding and row stripes'


@pytest.mark.parametrize('surface', ['report', 'pattern'])
def test_all_eight_pattern_buttons_are_present_on_report_and_notebook(surface, delivered_views):
    figures = [
        figure
        for figure in delivered_views[surface]['figures']
        if 'pattern-figure' in figure['kind']
    ]
    assert len(figures) == 1, 'Gate 9: each comparison surface contains its one actual pattern'
    wanted = [
        button for button in app_buttons() if not button['id'].endswith(('.save', '.saveImage'))
    ]
    assert len(wanted) >= 8, 'Gate 9: the app reference retains all eight pattern controls'
    actual = [button for button in figures[0]['controls'] if button['title'] != 'Save image']
    assert_app_toolbar(actual, wanted, legend=delivered_views['legend'])


def test_notebook_layer_adds_no_chart_or_parameter_table_overrides():
    paths = list((ROOT / 'website/surfaces/docs/assets').glob('*.css'))
    forbidden = []
    for path in paths:
        source = re.sub(r'/\*.*?\*/', '', path.read_text(), flags=re.DOTALL)
        for selector, body in re.findall(r'([^{}]+)\{([^{}]*)\}', source):
            if (
                re.search(r'notebook', selector, re.IGNORECASE)
                and re.search(
                    r'\b(table|thead|tbody|tr|td|th)\b|plotly|pattern-figure|structure-figure',
                    selector,
                )
                and re.search(r'padding|background|border|stroke|fill', body)
            ):
                forbidden.append(path.name + ': ' + selector.strip())
    assert not forbidden, (
        'Gate 9: the notebook docs layer adds no chart or table drawing overrides: '
        + repr(forbidden)
    )


@pytest.mark.parametrize('surface', ['report', 'pattern'])
def test_every_delivered_view_places_save_image_rightmost_in_its_own_group(
    surface, delivered_views
):
    figures = delivered_views[surface]['figures']
    assert figures, 'Gate 9: Save image is checked on actually rendered views'
    for figure in figures:
        controls = figure['controls']
        assert controls and controls[-1]['title'] == 'Save image', (
            'Gate 9: Save image is the final toolbar control for every report and notebook view'
        )
        save = controls[-1]
        assert all(save['rect']['left'] >= other['rect']['right'] for other in controls[:-1]), (
            'Gate 9: Save image is geometrically rightmost, after the other controls'
        )
        gaps = [
            right['rect']['left'] - left['rect']['right']
            for left, right in zip(controls[:-2], controls[1:-1], strict=True)
            if right['rect']['left'] >= left['rect']['right']
        ]
        gap = save['rect']['left'] - controls[-2]['rect']['right'] if len(controls) > 1 else 0
        assert gap > min(gaps, default=0) + 0.5, (
            'Gate 9: Save image is separated from reset by a group gap wider than ordinary spacing'
        )
        reference = json.loads((ROOT / 'tests/fixtures/tutorial_cases/glyphs.json').read_text())[
            'toolbar'
        ]['camera']
        icons = svg_documents(BeautifulSoup(save['html'], 'html.parser'))
        assert len(icons) == 1 and svg_identity(icons[0]) == (
            reference['path_sha256'],
            reference['viewBox'],
        ), 'Gate 9: Save image uses the shared app camera glyph'
        assert not figure['snapshots'], (
            'Gate 9: no notebook or report view retains a bottom-right camera button'
        )


@pytest.mark.parametrize('surface', ['report', 'pattern'])
def test_each_delivered_pattern_hides_the_default_plotting_toolbar(surface, delivered_views):
    assert delivered_views[surface]['modebar'] is False, (
        'Gate 9: report and notebook patterns both disable the plotting library default toolbar'
    )


@pytest.mark.parametrize('damage', ['panel-domain', 'measured-intensity', 'tick-colour'])
def test_document_typography_exception_preserves_all_chart_geometry_and_data(damage):
    original = {
        'traces': [{'y': [13.25, 18.5], 'marker': {'color': '#c58a03'}}],
        'layout': {'yaxis': {'domain': [0.3, 1]}, 'font': {'family': 'Print', 'size': 12}},
    }
    changed = json.loads(json.dumps(original))
    changed['layout']['font'] = {'family': 'Site', 'size': 16}
    assert drawing_without_document_typography(changed) == drawing_without_document_typography(
        original
    ), 'Gate 9: only the declared document typography varies between shared drawings'
    if damage == 'panel-domain':
        changed['layout']['yaxis']['domain'][0] = 0.5
    elif damage == 'measured-intensity':
        changed['traces'][0]['y'][0] += 2.25
    else:
        changed['traces'][0]['marker']['color'] = '#8b9762'
    assert drawing_without_document_typography(changed) != drawing_without_document_typography(
        original
    ), 'Gate 9: geometry, intensity and per-structure colours cannot hide as typography changes'
