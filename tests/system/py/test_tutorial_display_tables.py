"""Owner 60fd686d5: real public display tables and notebook/CLI progress parity."""

import json
import os
import re
import subprocess
import sys
from urllib.parse import unquote

import nbformat
import pytest
from bs4 import BeautifulSoup
from nbclient import NotebookClient

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.notebook_fit import environment
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_report_basis import Scripts
from tests.system.py.test_tutorial_cli_stream_parity import assert_human_stream, without_time

REFERENCE = json.loads((ROOT / 'tests/fixtures/tutorial_outline/tables.json').read_text())


def document(view):
    source = view if isinstance(view, str) else view._repr_html_()
    parsed = Scripts(source)
    return BeautifulSoup(parsed.frames[0] if parsed.frames else source, 'html.parser')


@pytest.fixture(scope='module')
def fitted_display_case():
    from conftest import corpus_case_dir  # noqa: PLC0415 - real pinned corpus admission

    source = corpus_case_dir('cosio-d20-s1') / 'project'
    project = api().Project.load(source)
    project.analysis.fit()
    return source, project


def named_table(soup, headers):
    actual = []
    for table in soup.find_all('table'):
        titles = [cell.get_text(' ', strip=True).casefold() for cell in table.select('thead th')]
        actual.append(titles)
        if titles == headers:
            return table
    raise AssertionError(
        'Gate 8/9: the public display must contain the primary column set: '
        + repr(headers)
        + '; actual='
        + repr(actual)
    )


@pytest.mark.parametrize('route', ['free', 'all', 'fittable'])
def test_parameter_displays_use_the_published_free_columns_with_separate_su(
    route, fitted_display_case
):
    _source, project = fitted_display_case
    operation = {
        'free': project.display.parameters.free,
        'all': project.display.parameters.all,
        'fittable': project.display.parameters.fittable,
    }[route]
    named_table(document(operation()), REFERENCE['free'])


def test_fit_results_include_the_full_parameter_table_and_four_explanations(fitted_display_case):
    _source, project = fitted_display_case
    soup = document(project.display.fit.results())
    table = named_table(soup, REFERENCE['fit'])
    assert table.select('tbody tr'), 'Gate 8: fit results include actual fitted-parameter rows'
    after = ' '.join(str(item) for item in table.next_siblings)
    prose = BeautifulSoup(after, 'html.parser').get_text(' ', strip=True).casefold()
    for label, terms in REFERENCE['explanation_terms'].items():
        assert label in prose and all(term in prose for term in terms), (
            'Gate 8: the fitted table explains start, value, s.u. and relative change below it: '
            + label
        )


@pytest.mark.parametrize('route', ['fit', 'free', 'all', 'fittable'])
def test_every_parameter_name_links_to_its_app_documentation_explanation(
    route, fitted_display_case
):
    _source, project = fitted_display_case
    operations = {
        'fit': project.display.fit.results,
        'free': project.display.parameters.free,
        'all': project.display.parameters.all,
        'fittable': project.display.parameters.fittable,
    }
    headers = REFERENCE['fit' if route == 'fit' else 'free']
    table = named_table(document(operations[route]()), headers)
    links = json.loads(
        (ROOT / 'website/surfaces/docs/assets/reference/parameter-links.json').read_text()
    )
    valid = {value for key, value in links.items() if '.' in key}
    for row in table.select('tbody tr'):
        cells = row.find_all('td', recursive=False)
        assert len(cells) == len(headers), (
            'Gate 8: parameter rows match the complete shared column vocabulary'
        )
        parameter = cells[headers.index('parameter')]
        link = parameter.find('a', href=True)
        assert link is not None and link.get_text(strip=True), (
            'Gate 8: every parameter name is an actionable documentation link'
        )
        href = unquote(link['href'])
        assert not href.lower().startswith(('javascript:', 'data:')) and any(
            href.endswith(path) for path in valid
        ), 'Gate 8: each parameter link reaches an explanation from the app documentation index'
        uid = (
            cells[headers.index('category')].get_text(strip=True)
            + '.'
            + parameter.get_text(strip=True)
        )
        if uid in links:
            assert href.endswith(links[uid]), (
                'Gate 8: a recognised parameter links its own explanation'
            )


def progress(text):
    lines = text.splitlines(keepends=True)
    start = next(
        (index for index, line in enumerate(lines) if re.search(r'\biter\b.*\btime\b', line)), None
    )
    assert start is not None, 'Gate 8: notebook fit emits the actual progress-table header'
    return without_time(''.join(lines[start:]))


def notebook_progress(outputs):
    candidates = [
        ''.join(
            output.get('text', '')
            for output in outputs
            if output['output_type'] == 'stream' and output.get('name') == 'stdout'
        )
    ]
    for output in outputs:
        data = output.get('data', {})
        rich = BeautifulSoup(data.get('text/html', ''), 'html.parser').get_text()
        plain = data.get('text/plain', '')
        # Notebook progress may update one rich output block instead of writing stdout.
        candidates.append(rich if re.search(r'\biter\b.*\btime\b', rich) else plain)
    actual = {
        progress(candidate)
        for candidate in candidates
        if re.search(r'\biter\b.*\btime\b', candidate)
    }
    assert len(actual) == 1, 'Gate 8: the notebook exposes one complete streamed progress table'
    return actual.pop()


def test_notebook_fit_streams_the_same_real_progress_rows_as_the_cli(
    tmp_path, fitted_display_case
):
    source, _project = fitted_display_case
    code = (
        'import easydiffraction as edi\nproject = edi.Project.load('
        + repr(str(source))
        + ')\nproject.analysis.fit()'
    )
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code)])
    with environment({'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}):
        NotebookClient(
            notebook,
            kernel_name='python3',
            timeout=120,
            resources={'metadata': {'path': str(tmp_path)}},
        ).execute()
    notebook_rows = notebook_progress(notebook.cells[0].outputs)
    cli = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(source),
            '--dry',
            '--report',
            'human',
            '--verbosity',
            'compact',
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        timeout=120,
    )
    assert cli.returncode == 0, 'Gate 8: the real comparison CLI completes the same corpus case'
    assert_human_stream(cli.stdout)
    assert notebook_rows == progress(cli.stdout), (
        'Gate 8: the notebook fit streams the shared CLI progress rows, apart from duration values'
    )


@pytest.mark.parametrize('transport', ['stdout', 'html', 'plain'])
def test_progress_observer_accepts_native_notebook_stream_and_rich_transports(transport):
    text = (
        '   iter   time (s)   Rwp (%)  reduced χ²   change\n'
        '                       22.22       24.22\n'
        '      1      0.014     18.11       16.84   30.4% ↓\n'
        '  done · converged · 1 iters · reduced χ² 16.84 · Rwp 18.11 % · 0.02 s\n'
    )
    output = {'output_type': 'stream', 'name': 'stdout', 'text': text}
    if transport != 'stdout':
        output = {
            'output_type': 'display_data',
            'data': {
                'text/html' if transport == 'html' else 'text/plain': '<pre>' + text + '</pre>'
                if transport == 'html'
                else text,
            },
        }
    assert notebook_progress([output]) == progress(text), (
        'Gate 8: native notebook transports preserve the same complete progress rows'
    )
