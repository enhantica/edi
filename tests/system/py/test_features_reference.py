# SPDX-License-Identifier: BSD-3-Clause
"""Built Features claims follow the declared interface boundaries and actual CLI help."""

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'features_page_reference', ROOT / 'tests/fixtures/features_reference/page.py'
)
PAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAGE)
INTERFACES = {'application', 'python', 'cli'}
REQUIRED = {
    'crystal': {'file', 'cod', 'collection', 'manual', 'project'},
    'magnetic': {'file', 'manual'},
    'experiments': {
        'full_file',
        'full_web',
        'measured_file',
        'measured_web',
        'datasets',
        'manual',
        'project',
    },
}


def definition_rows(page):
    return [
        (table, row) for table in page['tables'] if table['definition'] for row in table['rows']
    ]


def check_definitions(page):
    rows = definition_rows(page)
    assert {row['part'] for _, row in rows} == set(REQUIRED), (
        'Definition tables must cover crystal structures, magnetic structures and experiments'
    )
    for group, required in REQUIRED.items():
        selected = [(table, row) for table, row in rows if row['part'] == group]
        assert required <= {PAGE.way(row['label'], group) for _, row in selected}, (
            'Each definition part must list the required creation and loading routes: ' + group
        )
        for table, row in selected:
            assert (
                len(table['columns']) == len(INTERFACES) and set(table['columns']) == INTERFACES
            ), 'Every ways-of-defining table must have exactly one column per interface'
            assert len(row['cells']) == len(table['columns']), (
                'Each definition row must fill every interface column'
            )


def check_magnetic(page):
    rows = [row for _, row in definition_rows(page) if row['part'] == 'magnetic']
    assert rows, 'The definition table must contain its magnetic-structure part'
    assert not any(PAGE.way(row['label'], 'magnetic') == 'cod' for row in rows), (
        'Magnetic structure definitions must have no COD entry'
    )
    manual = [row for row in rows if PAGE.way(row['label'], 'magnetic') == 'manual']
    assert manual, 'Magnetic manual creation must be explicitly listed as planned work'
    planned = page['legend'].get('planned')
    assert planned, 'The status legend must identify the planned-work mark'
    for row in manual:
        assert len(row['cells']) == len(INTERFACES) and all(
            planned['mark'] in PAGE.marks(cell) for cell in row['cells']
        ), 'Magnetic manual creation must be marked planned in every interface'


def check_partial_cells(page):
    partial = page['legend'].get('partial')
    assert partial, 'The status legend must identify the partial-work mark'
    for table in page['tables']:
        for row in table['rows']:
            for cell in row['all_cells']:
                if partial['mark'] not in PAGE.marks(cell):
                    continue
                label = cell.label()
                assert re.search(
                    r'\b(missing|unfinished|pending|planned|todo|only|without|lacks?|'
                    r'not yet|not implemented|not available|not supported|does not|limited to|'
                    r'drops?|omits?|loses?|lost)\b',
                    label,
                    re.IGNORECASE,
                ), 'Every partial cell must label the missing work: ' + row['label']
                detail = set(re.findall(r'[a-z]+', label.casefold())) - {
                    'partial',
                    'missing',
                    'unfinished',
                    'pending',
                    'planned',
                    'todo',
                    'only',
                    'work',
                    'feature',
                    'support',
                    'not',
                    'yet',
                    'implemented',
                    'available',
                    'currently',
                    'fully',
                    'complete',
                    'limited',
                    'to',
                    'without',
                    'lacks',
                    'does',
                    'drops',
                    'omits',
                    'loses',
                    'lost',
                }
                assert detail, 'A partial cell must name specific unfinished work'


def check_legend(page):
    partial = page['legend'].get('partial')
    assert partial, 'The rendered legend must contain a partial-work entry'
    assert not re.search(r'prepared|saved project|runs? from', partial['text'], re.IGNORECASE), (
        'The partial legend must describe unfinished work without prepared-project restrictions'
    )


def check_cli_cells(page):
    rows = definition_rows(page)
    assert rows, 'The CLI definition check requires the actual ways-of-defining tables'
    available, planned, unavailable = [
        page['legend'].get(name) for name in ('available', 'planned', 'unavailable')
    ]
    assert available and planned and unavailable, (
        'CLI table checks require the rendered status legend'
    )
    for table, row in rows:
        assert table['columns'].count('cli') == 1, (
            'Every definition table must identify exactly one CLI column'
        )
        cell = row['cells'][table['columns'].index('cli')]
        route = PAGE.way(row['label'], row['part'])
        expected = (
            available
            if route == 'project'
            else planned
            if route == 'manual' and row['part'] == 'magnetic'
            else unavailable
        )
        assert expected['mark'] in PAGE.marks(cell), (
            'CLI definitions must offer saved projects only and plan magnetic manual creation: '
            + row['label']
        )


@pytest.fixture(scope='module')
def features():
    site = Path(os.environ.get('EDI_DOCS_SITE', str(ROOT / 'website/_build')))
    path = site / 'user-guide/features/index.html'
    assert path.is_file(), 'The Features gate requires the actual built Features page'
    source = path.read_bytes()
    print('Built Features SHA-256:', hashlib.sha256(source).hexdigest())
    return PAGE.observe(source.decode('utf-8'))


def test_definition_tables_cover_three_parts_and_every_interface(features):
    check_definitions(features)


def test_magnetic_manual_creation_is_planned_and_cod_is_absent(features):
    check_magnetic(features)


def test_partial_cells_in_every_table_name_missing_work(features):
    check_partial_cells(features)


@pytest.mark.parametrize('interface', [0, 1], ids=['application', 'python'])
@pytest.mark.parametrize('explanation', ['absent', 'generic', 'specific', 'specific-drops'])
def test_definition_partial_explanations_reach_the_same_checker(interface, explanation):
    spec = importlib.util.spec_from_file_location(
        'features_authored_control', ROOT / 'tests/fixtures/features_reference/build.py'
    )
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    page = PAGE.observe(control.build(f'definition-partial-{interface}-{explanation}'))
    if explanation.startswith('specific'):
        check_partial_cells(page)
    else:
        with pytest.raises(AssertionError, match='partial cell'):
            check_partial_cells(page)


def test_partial_legend_does_not_describe_prepared_projects(features):
    check_legend(features)


def test_cli_definition_claims_match_actual_executable_help(features):
    suffix = '.exe' if os.name == 'nt' else ''
    extension = importlib.import_module('edi._edi')
    artifact = Path(extension.__file__).resolve().parents[2]
    native = Path(os.environ.get('EDI_NATIVE_CLI', str(artifact / f'cli/easydiffraction{suffix}')))
    assert native.is_file(), 'The selected compiled artifact must have its matching native CLI'
    for prefix in ([str(native)], [sys.executable, '-m', 'edi']):
        help_result = subprocess.run(
            [*prefix, '--help'], capture_output=True, text=True, timeout=5, check=False
        )
        assert help_result.returncode == 0 and 'project' in help_result.stdout.casefold(), (
            'Actual CLI help must run and identify project input before checking table claims'
        )
        for action in (
            'create-structure',
            'create-experiment',
            'load-structure',
            'load-experiment',
        ):
            result = subprocess.run(
                [*prefix, action, '--help'], capture_output=True, text=True, timeout=5, check=False
            )
            assert result.returncode != 0, (
                'A direct CLI definition entrance requires a table review: ' + action
            )
    check_cli_cells(features)
