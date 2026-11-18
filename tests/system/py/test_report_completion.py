"""Real Report tables and chart input in the native preview and saved HTML."""

import base64
import json
import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture
from tests.fixtures.report_evolution.observe_browser import observe

ROOT = Path(__file__).resolve().parents[3]


def native(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Report completion requires the actual native Qt host'
    status, output = capture(
        [
            binary,
            '-input',
            ROOT / 'tests/unit/app/tst_report_completion.qml',
            'ReportCompletion::' + case,
        ],
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert 'Could not find the following test functions' not in output, (
        'The requested Report function exists before product behavior is judged'
    )
    assert status == 0, (
        'The real Report preview and export complete their actual workflow: ' + output
    )
    function, _, tag = case.partition(':')
    expected = f'{function}({tag})' if tag else f'{function}()'
    assert expected in output and '0 failed' in output and 'SKIP' not in output, (
        'The requested Report completion function reaches its native assertions without skipping'
    )
    return output


@pytest.fixture(scope='module')
def saved_html():
    output = native('test_save_report_to_self_contained_html')
    documents = [
        json.loads(line.split('COMPLETE_REPORT_HTML ', 1)[1])
        for line in output.splitlines()
        if 'COMPLETE_REPORT_HTML ' in line
    ]
    assert documents and all(part['chunks'] == len(documents) for part in documents), (
        'The actual saved HTML is transported completely through bounded native log records'
    )
    assert [part['index'] for part in documents] == list(range(len(documents))), (
        'Every actual saved HTML byte chunk occurs exactly once in disk order'
    )
    return base64.b64decode(''.join(part['base64'] for part in documents), validate=True).decode(
        'utf-8'
    )


def test_report_full_table_reaches_its_final_input_row():
    native('test_every_declared_table_row_reaches_the_real_viewport')


@pytest.mark.parametrize('kind', ['pattern', 'structure'])
def test_report_preview_supported_buttons_perform_real_actions(kind):
    native('test_supported_preview_buttons_reach_real_chart_actions:' + kind)


BUTTONS = r"""(async () => {
  const facts = [];
  for (const figure of document.querySelectorAll('.pattern-figure,.structure-figure')) {
    const plot = figure.matches('.js-plotly-plot')
      ? figure : figure.querySelector('.js-plotly-plot');
    const controls = [...figure.querySelectorAll('button,[role="button"],a.modebar-btn')];
    const title = button => button.getAttribute('data-title')
      || button.getAttribute('aria-label') || button.title || button.textContent.trim();
    const visible = button => !button.disabled
      && getComputedStyle(button).visibility !== 'hidden'
      && getComputedStyle(button).display !== 'none'
      && button.getBoundingClientRect().width > 0;
    const result = {kind: figure.classList.contains('pattern-figure') ? 'pattern' : 'structure',
      buttons: controls.filter(visible).map(button => ({title: title(button),
        icon: button.dataset.icon, custom: button.classList.contains('viewer-button'),
        svg: button.querySelectorAll('svg').length})), actions: []};
    if (plot && result.kind === 'pattern') {
      for (const mode of ['pan','zoom']) {
        const button = controls.find(button => visible(button)
          && new RegExp('\\b' + mode + '\\b', 'i').test(title(button)));
        if (button) {
          button.click();
          await new Promise(resolve => setTimeout(resolve, 0));
          result.actions.push({requested: mode, actual: plot._fullLayout?.dragmode});
        }
      }
    }
    if (result.kind === 'structure') {
      for (const role of ['Labels', 'Bonds', 'Cell', 'Axes']) {
        const button = controls.find(button => visible(button) && title(button) === role);
        if (button) {
          const before = button.getAttribute('aria-pressed');
          button.click();
          await new Promise(resolve => setTimeout(resolve, 0));
          result.actions.push({requested: role, before,
            after: button.getAttribute('aria-pressed')});
        }
      }
      const projection = controls.find(button => visible(button)
        && /(?:orthographic|perspective)/i.test(title(button)));
      if (projection) {
        const before = title(projection);
        projection.click();
        await new Promise(resolve => setTimeout(resolve, 0));
        result.actions.push({requested: 'projection', before, after: title(projection)});
      }
    }
    facts.push(result);
  }
  return facts;
})()"""


@pytest.mark.parametrize('viewport', ['wide', 'narrow'])
def test_saved_html_full_tables_buttons_and_powder_styling(saved_html, viewport):
    expected = json.loads((ROOT / 'tests/fixtures/report_completion/reference.json').read_text())[
        'rows'
    ]
    pages = observe(
        saved_html, require_structure_rendering=True, extra_observer=BUTTONS, viewports=(viewport,)
    )
    for facts in pages.values():
        assert facts['ready'] and not facts['errors'], (
            'The actual offline HTML charts finish rendering without browser errors'
        )
        tables = [table for table in facts['tables'] if len(table['rows']) == len(expected)]
        assert len(tables) == 1, (
            'The saved HTML exposes the complete independently declared measured table'
        )
        actual = [
            [float(value.replace('\u2212', '-')) for value in row[:3]] for row in tables[0]['rows']
        ]
        assert actual == expected, (
            'Every saved HTML measured row retains the explicit independent input order and values'
        )
        figures = facts['extra']
        assert {figure['kind'] for figure in figures} == {'pattern', 'structure'}, (
            'Saved HTML draws the same supported report figure kinds as the native preview'
        )
        for figure in figures:
            names = [button['title'].lower() for button in figure['buttons']]
            assert any('save' in name or 'download' in name for name in names), (
                'Each saved HTML chart exposes its actual camera action'
            )
            assert any('reset' in name for name in names), (
                'Each saved HTML chart exposes its actual reset action'
            )
            icons = {button.get('icon'): button for button in figure['buttons']}
            assert all(
                icons.get(icon, {}).get('custom') and icons[icon]['svg'] > 0
                for icon in ('camera', 'home')
            ), 'The saved HTML uses the app-style camera and home icons in its real chart toolbar'
            if figure['kind'] == 'structure':
                assert all(
                    any('view along ' + axis in name for name in names) for axis in ('a', 'b', 'c')
                ), (
                    'The HTML structure offers the same three lattice-direction camera buttons '
                    'as the app'
                )
                toggles = [
                    action for action in figure['actions'] if action['requested'] != 'projection'
                ]
                assert {action['requested'] for action in toggles} == {
                    'Labels',
                    'Bonds',
                    'Cell',
                    'Axes',
                } and all(
                    action['before'] in {'true', 'false'} and action['after'] != action['before']
                    for action in toggles
                ), 'The real HTML structure show/hide buttons change their actual selected state'
                projection = [
                    action for action in figure['actions'] if action['requested'] == 'projection'
                ]
                assert (
                    len(projection) == 1 and projection[0]['before'] != projection[0]['after']
                ), 'The real HTML projection button switches the structure camera mode'
            if figure['kind'] == 'pattern':
                assert figure['actions'] == [
                    {'requested': 'pan', 'actual': 'pan'},
                    {'requested': 'zoom', 'actual': 'zoom'},
                ], (
                    'The real HTML Pan and Zoom buttons change the actual rendered chart '
                    'interaction modes'
                )
        patterns = facts['patterns']
        assert len(patterns) == 1 and patterns[0]['svgCount'] > 0, (
            'The actual HTML report renders its independently declared powder pattern'
        )
        colours = {
            str(trace.get('line', {}).get('color', '')).lower() for trace in patterns[0]['traces']
        }
        palette = json.loads(
            (ROOT / 'tests/fixtures/single_crystal_pattern/powder-colours.json').read_text()
        )['palettes'][0]['roles']
        assert all(
            palette[role]['light'].lower() in colours
            for role in ('total_calculation', 'difference')
        ), (
            'The HTML chart uses the independently published Main powder calculated '
            'and residual colours'
        )
