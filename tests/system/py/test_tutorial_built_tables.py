"""Owner 947aa4bca: table/navigation agreement on real Zensical output."""

import json
import os
import shutil
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlparse

import pytest
from bs4 import BeautifulSoup, SoupStrainer

from tests.fixtures.tutorial_cases.contract import ROOT, cases_for
from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL
from tests.fixtures.tutorial_cases.pipeline import executed_inputs, stage
from tests.fixtures.tutorial_cases.presentation import RULES

BUILD = """import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / 'website'))
import build, render_experiments
from case_records import records
pages = build.render_notebook_pages(root / 'docs/user/tutorials')
render_experiments.write_tutorial_tables(records(root), {page for _, _, page in pages})
build.TUTORIAL_PAGES[:] = pages
config = build._config_text('surfaces', (root / 'website/surfaces/mkdocs.yml').read_text(),
                           root / 'website/surfaces/docs/assets/site-components.css', None)
(root / 'website/surfaces/tables-test.yml').write_text(config)
"""


@pytest.fixture(scope='module')
def built_site(tmp_path_factory):
    root = stage(tmp_path_factory.mktemp('built-tutorial-tables') / 'source')
    shutil.copytree(ROOT / 'data', root / 'data')
    for path in (ROOT / 'docs/user/tutorials').glob('*.py'):
        shutil.copy2(path, root / 'docs/user/tutorials' / path.name)
    # Authored conversion-protocol fixtures isolate layout from expensive scientific runs.
    # They carry no fitted answers; the separate execution and final-pin gates test real runs.
    executed_inputs(root)
    # Link identity uses the committed teaching payload. The sole authored output is
    # an inert conversion control; this fixture makes no notebook-execution claim.
    example = ROOT / 'docs/user/tutorials/pd-neut-cwl_lbco-hrpt.ipynb'
    original = json.loads(
        subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', 'HEAD:' + example.relative_to(ROOT).as_posix()],
            text=True,
        )
    )
    first_code = next(cell for cell in original['cells'] if cell['cell_type'] == 'code')
    first_code['outputs'] = [
        {
            'output_type': 'stream',
            'name': 'stdout',
            'text': 'Authored conversion control; no scientific run',
        }
    ]
    first_code['execution_count'] = 1
    (root / 'docs/user/tutorials' / example.name).write_text(json.dumps(original))
    # A real public table output exercises the built page's display typography.
    from tests.integration.py.test_tutorial_empty_project import api  # noqa: PLC0415

    project = api().Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20/project')
    project.report.html_offline = True
    project.analysis.calculate()
    path = root / 'docs/user/tutorials/pd-neut-cwl_cosio-d20.ipynb'
    displayed = json.loads(path.read_text())
    displayed['cells'][0]['source'] += '\n\nInspect the measured pattern and fit parameters.'
    displayed['cells'][-1]['outputs'] = [
        {'output_type': 'display_data', 'metadata': {}, 'data': {'text/html': view._repr_html_()}}
        for view in [project.display.parameters.free(), project.display.pattern()]
    ]
    path.write_text(json.dumps(displayed))
    version = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    environment = {
        **os.environ,
        'GITHUB_SHA': version,
        'GITHUB_REF_NAME': version,
        'EDI_DOCS_REF': version,
    }
    preparation = subprocess.run(
        [sys.executable, '-c', BUILD, str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
        timeout=30,
    )
    assert preparation.returncode == 0, (
        'Gate 3: native notebook pages and overview tables must prepare before Zensical: '
        + preparation.stdout
        + preparation.stderr
    )
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'zensical',
            'build',
            '--strict',
            '-f',
            str(root / 'website/surfaces/tables-test.yml'),
        ],
        cwd=root / 'website/surfaces',
        env={**environment, 'NO_COLOR': '1'},
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    (root / 'zensical.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'Gate 3: the isolated real Zensical build must complete before checking built tables: '
        + result.stdout[-3000:]
        + result.stderr[-3000:]
    )
    return root / 'website/surfaces/site'


@pytest.fixture(scope='module')
def built_table_style(built_site, tmp_path_factory):
    from tests.fixtures.tutorial_cases.browser import observe_html  # noqa: PLC0415

    page = built_site / 'python/tutorials/cases/pd-neut-cwl_cosio-d20/index.html'
    source = page.read_text().replace(
        '<head>', '<head><base href="' + page.parent.as_uri() + '/">', 1
    )
    result = observe_html(source, tmp_path_factory.mktemp('docs-table-style') / 'browser')
    assert result['docs']['frames'], (
        'Gate 9: typography is observed on a real built-page display table'
    )
    return result['docs']


def test_built_display_tables_use_the_page_body_font(built_table_style):
    tables = built_table_style['frames']
    fonts = [font for table in tables for font in table['bodyText']]
    assert fonts and all(font == built_table_style['paragraph'] for font in fonts), (
        'Gate 9: table body text matches a Markdown paragraph family, weight, size and colour'
    )


def test_built_chart_text_matches_the_markdown_paragraph_typography(built_table_style):
    values = built_table_style['chartText']
    assert values and all(value == built_table_style['paragraph'] for value in values), (
        'Gate 9: chart axes and tick text match the paragraph family, weight, size and colour'
    )


def test_built_display_table_links_use_the_site_colour_without_visited_changes(built_table_style):
    links = [link for table in built_table_style['frames'] for link in table['links']]
    assert links and built_table_style['link'], (
        'Gate 9: the real table and page expose documentation links'
    )
    assert all(link['colour'] == built_table_style['link'] for link in links), (
        'Gate 9: display-table links use the built site link colour'
    )
    # Browsers conceal visited colours from getComputedStyle. Inspect the matching
    # authored :visited declarations too, resolving their colours in the same document.
    assert all(
        colour == built_table_style['link'] for link in links for colour in link['visited']
    ), 'Gate 9: no matching visited-link declaration changes the site link colour'


def test_no_built_user_document_links_to_the_developer_site(built_site):
    wrong = []
    for page in built_site.rglob('*.html'):
        for link in BeautifulSoup(
            page.read_text(), 'html.parser', parse_only=SoupStrainer('a')
        ).select('a[href]'):
            address = urlparse(urljoin('https://enhantica.github.io/edi/', link['href']))
            if address.netloc == 'enhantica.github.io' and address.path.startswith('/edi/dev/'):
                wrong.append((page.relative_to(built_site).as_posix(), link['href']))
    assert not wrong, 'Gate 3/5: user documentation never sends users into dev docs: ' + repr(
        wrong
    )


@pytest.mark.parametrize('case', cases_for('cli'))
def test_each_command_line_tutorial_is_a_local_user_page(case, built_site):
    path = built_site / 'cli/tutorials/cases' / case / 'index.html'
    assert path.is_file(), (
        'Gate 5: each case has its Command line tutorial at its user URL: ' + case
    )
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    assert soup.select_one('main h1') is not None, 'Gate 5: the user URL renders a tutorial page'
    assert not soup.select('meta[http-equiv="refresh"]'), (
        'Gate 5: a Command line tutorial is content, not a redirect to developer documentation'
    )


def teaching_payload(document):
    result = json.loads(json.dumps(document))
    for cell in result['cells']:
        cell.pop('outputs', None)
        cell.pop('execution_count', None)
    return result


def test_built_colab_address_names_the_build_version_and_matches_the_download(built_site):
    case = 'pd-neut-cwl_lbco-hrpt'
    page = built_site / 'python/tutorials/cases' / case / 'index.html'
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    links = soup.select('a[href]')
    colab = [link for link in links if 'Open in Google Colab' in link.get_text(' ', strip=True)]
    downloads = [link for link in links if 'Download Notebook' in link.get_text(' ', strip=True)]
    assert len(colab) == len(downloads) == 1, (
        'Gate 3: the built tutorial has both notebook buttons'
    )
    version = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    expected = '/github/enhantica/edi/blob/' + version + '/docs/user/tutorials/' + case + '.ipynb'
    address = urlparse(unquote(colab[0]['href']))
    assert address.netloc == 'colab.research.google.com' and address.path == expected, (
        'Gate 3: Colab names this build version, rather than hard-coded main'
    )
    target = urlparse(urljoin(page.as_uri(), downloads[0]['href']))
    assert target.scheme == 'file', 'Gate 3: Download Notebook resolves to this built site'
    from pathlib import Path  # noqa: PLC0415 - file URL from the real built link

    path = Path(unquote(target.path))
    assert path.is_relative_to(built_site) and path.is_file(), (
        'Gate 3: the notebook download link reaches an actual file in the built site'
    )
    downloaded = json.loads(path.read_text(encoding='utf-8'))
    at_version = json.loads(
        subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', version + ':docs/user/tutorials/' + case + '.ipynb'],
            text=True,
        )
    )
    assert teaching_payload(downloaded) == teaching_payload(at_version), (
        'Gate 3: Colab and Download Notebook have identical teaching cells and metadata; '
        'only execution counts and outputs may differ'
    )
    install = downloaded['cells'][0]
    source = (
        install['source'] if isinstance(install['source'], str) else ''.join(install['source'])
    )
    assert source == INSTALL_CELL and 'hide-in-docs' in install['metadata']['tags'], (
        'Gate 3: the notebook opened in Colab and downloaded retains the hidden install cell'
    )


def label(item):
    node = item.find(['label', 'a'], recursive=False)
    if node is None:
        container = item.find('div', class_='md-nav__container', recursive=False)
        node = container.find('a', recursive=False) if container is not None else None
    if node is None:
        return ''
    text = node.select_one('.md-ellipsis')
    return (text if text is not None else node).get_text(' ', strip=True)


def children(item):
    navigation = item.find('nav', recursive=False)
    listing = navigation.find('ul', recursive=False) if navigation is not None else None
    return listing.find_all('li', recursive=False) if listing is not None else []


def assert_built_order(page, interface):
    soup = BeautifulSoup(page, 'html.parser')
    tables = soup.select('[data-example-catalogue] table')
    assert len(tables) == 1, 'Gate 3: the built overview contains one real tutorial table'
    table_sections = [
        item['data-tutorial-section'] for item in tables[0].select('[data-tutorial-section]')
    ]
    nav = soup.select_one('.md-nav--primary')
    assert nav is not None, 'Gate 3: the built page contains native site navigation'
    interfaces = [item for item in nav.find_all('li') if label(item) == interface]
    assert len(interfaces) == 1, 'Gate 3: the built navigation names the selected interface once'
    tutorials = [item for item in children(interfaces[0]) if label(item) == 'Tutorials']
    assert len(tutorials) == 1, 'Gate 3: the built interface contains one Tutorials section'
    nav_sections = [label(item) for item in children(tutorials[0]) if children(item)]
    assert table_sections == nav_sections == [name for name, _ in RULES['sections']], (
        'Gate 3: the actual built table and navigation share the five sections in the same order'
    )


def assert_no_interface_column(page):
    soup = BeautifulSoup(page, 'html.parser')
    tables = soup.select('[data-example-catalogue] table')
    assert len(tables) == 1, 'Gate 3: each built interface overview contains one tutorial table'
    headers = [cell.get_text(' ', strip=True) for cell in tables[0].select('thead th')]
    assert not headers, (
        'Gate 3: an interface overview begins at its section heading, with no column header row'
    )
    for row in tables[0].select('[data-example-row]'):
        cells = row.find_all('td', recursive=False)
        assert len(cells) == 1 and cells[0].select_one('.ed-example-name a[href]') is not None, (
            'Gate 3: the built title is the link; no duplicate own-interface cell remains'
        )


@pytest.mark.parametrize(
    ('interface', 'folder'), [tuple(item[:2]) for item in RULES['interfaces']]
)
def test_built_tutorial_table_section_order_matches_its_navigation(interface, folder, built_site):
    assert_built_order((built_site / folder / 'tutorials/index.html').read_text(), interface)


@pytest.mark.parametrize('folder', ['application', 'python', 'cli'])
def test_built_interface_overview_has_no_interface_column(folder, built_site):
    assert_no_interface_column((built_site / folder / 'tutorials/index.html').read_text())


def control_page():
    sections = [name for name, _ in RULES['sections']]
    groups = ''.join(
        '<li><label>' + name + '</label><nav><ul><li><a>Case</a></li></ul></nav></li>'
        for name in sections
    )
    nav = (
        '<nav class="md-nav--primary"><ul><li><label>Python</label><nav><ul><li>'
        '<label>Tutorials</label><nav><ul>'
        + groups
        + '</ul></nav></li></ul></nav></li></ul></nav>'
    )
    rows = ''.join(
        '<tr data-tutorial-section="' + name + '"><th>' + name + '</th></tr>' for name in sections
    )
    return nav + '<div data-example-catalogue><table>' + rows + '</table></div>'


@pytest.mark.parametrize('escape', ['table-order', 'nav-order', 'interface-column'])
def test_built_html_observers_refuse_order_drift_and_duplicate_interface_columns(escape):
    good = control_page()
    assert_built_order(good, 'Python')
    assert_no_interface_column(good)
    soup = BeautifulSoup(good, 'html.parser')
    if escape == 'table-order':
        rows = soup.select('[data-tutorial-section]')
        rows[0].insert_before(rows[-1])
    elif escape == 'nav-order':
        labels = [
            node for node in soup.select('label') if node.get_text() in dict(RULES['sections'])
        ]
        labels[0].string, labels[-1].string = labels[-1].get_text(), labels[0].get_text()
    else:
        soup.select_one('table').insert(
            0, BeautifulSoup('<thead><tr><th>Python</th></tr></thead>', 'html.parser').thead
        )
    check = (
        (lambda: assert_no_interface_column(str(soup)))
        if escape == 'interface-column'
        else (lambda: assert_built_order(str(soup), 'Python'))
    )
    with pytest.raises(AssertionError, match='Gate 3:'):
        check()
