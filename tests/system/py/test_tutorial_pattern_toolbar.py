"""Owner 052a69b53: the delivered report toolbar follows the independent app toolbar."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.presentation import svg_documents, svg_identity
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_report_basis import html, model

PROBE = """<script>
window.addEventListener('load', () => setTimeout(() => {
  const figure = document.querySelector('.pattern-figure');
  const plot = figure && (figure.classList.contains('js-plotly-plot')
    ? figure : figure.querySelector('.js-plotly-plot'));
  const result = {
    figure: !!figure, plot: !!plot,
    modebar: plot && plot._context && plot._context.displayModeBar,
    buttons: figure ? [...figure.querySelectorAll('button')].map(button => ({
      title: button.title || button.getAttribute('aria-label'), html: button.innerHTML,
      disabled: button.disabled,
    })) : [],
  };
  const receipt = document.createElement('pre'); receipt.id = 'toolbar-witness';
  receipt.textContent = JSON.stringify(result); document.body.appendChild(receipt);
}, 1000));
</script>"""


def app_buttons():
    source = (ROOT / 'app/qml/Components/ChartToolbar.qml').read_text()
    buttons = []
    for match in re.finditer(r'ChartToolButton\s*\{(.*?)\n\s*\}', source, re.DOTALL):
        body = match[1]
        identity = re.search(r'objectName:\s*"([^"]+)"', body)
        icon = re.search(r'fontIcon:\s*"([^"]+)"', body)
        tips = re.findall(r'qsTr\("([^"]+)"\)', body)
        assert identity and icon and tips, (
            'Gate 9: every independent app toolbar button declares identity, icon and tooltips'
        )
        buttons.append({'id': identity[1], 'icon': icon[1], 'tips': tips})
    assert buttons, 'Gate 9: the app toolbar is a nonempty independent reference'
    return buttons


def chromium():
    candidates = [
        os.environ.get('BROWSER_EXECUTABLE'),
        shutil.which('chromium'),
        shutil.which('chromium-browser'),
        shutil.which('google-chrome'),
    ]
    candidates += [
        str(path)
        for path in sorted(
            (Path.home() / '.cache/ms-playwright').glob(
                'chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell'
            )
        )
    ]
    candidates += [
        str(path)
        for path in sorted(
            (Path.home() / '.cache/ms-playwright').glob('chromium-*/chrome-linux*/chrome')
        )
    ]
    selected = next((str(path) for path in candidates if path and Path(path).is_file()), None)
    assert selected is not None, 'Gate 9 prerequisite: install Chromium or set BROWSER_EXECUTABLE'
    return selected


@pytest.fixture(scope='module')
def delivered_toolbar(tmp_path_factory):
    folder = tmp_path_factory.mktemp('pattern-toolbar')
    project = api().Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project')
    project.analysis.calculate()
    report = project.report.as_html(offline=True, excluded=['data', 'reflections', 'correlations'])
    document = model(html(report))
    assert document['experiments'], 'Gate 9: the real calculated powder project supplies a pattern'
    pattern = document['experiments'][0]['pattern']
    path = folder / 'report.html'
    path.write_text(report.replace('</body>', PROBE + '</body>'))
    run = subprocess.run(
        [
            chromium(),
            '--headless',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--disable-background-networking',
            '--disable-extensions',
            '--proxy-server=direct://',
            '--proxy-bypass-list=*',
            '--host-resolver-rules=MAP * ~NOTFOUND',
            '--allow-file-access-from-files',
            '--user-data-dir=' + str(folder / 'profile'),
            '--virtual-time-budget=3000',
            '--dump-dom',
            path.as_uri(),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert run.returncode == 0, 'Gate 9: the saved offline report must open in the real browser'
    witness = BeautifulSoup(run.stdout, 'html.parser').find(id='toolbar-witness')
    assert witness is not None, (
        'Gate 9: the browser must execute the delivered report and observer'
    )
    result = json.loads(witness.get_text())
    assert result['figure'] and result['plot'], (
        'Gate 9: toolbar assertions observe a real drawn Plotly pattern'
    )
    return result, pattern


def assert_app_toolbar(actual, expected, *, legend, references=None):
    if references is None:
        document = json.loads((ROOT / 'tests/fixtures/tutorial_cases/glyphs.json').read_text())
        references = {
            name: (item['path_sha256'], item['viewBox'])
            for name, item in document['toolbar'].items()
        }
    wanted = [
        button['tips'][1] if button['id'].endswith('.legend') and not legend else button['tips'][0]
        for button in expected
    ]
    assert [button['title'] for button in actual] == wanted, (
        'Gate 9: report toolbar buttons match app order and exact state-dependent tooltips'
    )
    for button, reference in zip(actual, expected, strict=True):
        icons = svg_documents(BeautifulSoup(button['html'], 'html.parser'))
        assert len(icons) == 1, 'Gate 9: each custom chart button carries its one shared app icon'
        assert reference['icon'] in references, (
            'Gate 9: each toolbar icon exists in the shared app font'
        )
        assert svg_identity(icons[0]) == references[reference['icon']], (
            'Gate 9: the report toolbar draws exactly the glyph named by the app toolbar'
        )


def test_saved_report_toolbar_button_order_icons_and_tooltips_match_the_app(delivered_toolbar):
    result, pattern = delivered_toolbar
    assert_app_toolbar(result['buttons'], app_buttons(), legend=pattern['legend'])


def test_saved_report_hides_the_plotting_librarys_default_toolbar(delivered_toolbar):
    result, _pattern = delivered_toolbar
    assert result['modebar'] is False, (
        'Gate 9: the real Plotly context disables its default toolbar, including hover mode'
    )


@pytest.mark.parametrize('escape', ['order', 'tooltip', 'missing', 'extra', 'wrong-icon'])
def test_toolbar_observer_refuses_changed_button_lists_and_glyphs(escape):
    expected = [
        {'id': 'chart.toolbar.legend', 'icon': 'triangle', 'tips': ['Hide legend', 'Show legend']},
        {'id': 'chart.toolbar.reset', 'icon': 'square', 'tips': ['Reset axes']},
    ]
    shapes = [
        '<svg viewBox="0 0 8 8"><path d="M0 0L8 0L4 8Z"/></svg>',
        '<svg viewBox="0 0 8 8"><path d="M0 0L8 0L8 8L0 8Z"/></svg>',
    ]
    references = {
        item['icon']: svg_identity(shape) for item, shape in zip(expected, shapes, strict=True)
    }
    valid = [
        {'title': item['tips'][0], 'html': shape}
        for item, shape in zip(expected, shapes, strict=True)
    ]
    assert_app_toolbar(valid, expected, legend=True, references=references)
    broken = [dict(button) for button in valid]
    if escape == 'order':
        broken[0], broken[-1] = broken[-1], broken[0]
    elif escape == 'tooltip':
        broken[1]['title'] = 'Renamed coordinates control'
    elif escape == 'missing':
        broken.pop()
    elif escape == 'extra':
        broken.append(broken[0])
    else:
        broken[0]['html'] = broken[-1]['html']
    with pytest.raises(AssertionError, match='Gate 9:'):
        assert_app_toolbar(broken, expected, legend=True, references=references)
