"""Owner records 7836b4a78, e1f08e42b and 9a3e5e7bc at native docs seams."""

import copy
import importlib
import re

import pytest
import yaml
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.contract import (
    ROOT,
    cases_for,
    declared_interfaces,
    read_records,
)
from tests.fixtures.tutorial_cases.interfaces import assert_catalogue_coverage, link_is_case
from tests.fixtures.tutorial_cases.presentation import (
    RULES,
    assert_tag_cell,
    chips,
    notebook,
    text,
)
from tests.integration.py.test_tutorial_notebook_contract import record_for


def site_module(name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'website'))
    return importlib.import_module(name)


@pytest.mark.parametrize('case', cases_for('python'))
def test_native_page_has_docs_buttons_and_the_one_visible_notebook_tag_cell(
    case, tmp_path, monkeypatch
):
    record = record_for(case)
    document = copy.deepcopy(notebook(case))
    tags = [cell for cell in document['cells'] if chips(text(cell))]
    assert len(tags) == 1, 'Gate 3: each source notebook has one tags cell to publish'
    assert_tag_cell(tags[0], record)
    # No scientific output claim: this probe checks the conversion seam only.
    for cell in document['cells']:
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
    renderer = site_module('render_notebook_pages', monkeypatch)
    source, title = renderer.page(
        document,
        record,
        'notebooks/' + case + '.ipynb',
        renderer._Views(tmp_path / 'views', 'views/'),
    )
    assert title == record['title'], 'Gate 3: native docs keep the complete unique case title'
    headings = list(re.finditer(r'^# (.+)$', source, re.MULTILINE))
    assert len(headings) == 1 and headings[0][1] == record['title'], (
        'Gate 3: native docs have exactly the case H1'
    )
    for label, icon in [
        ('Open in Google Colab', ':simple-googlecolab:'),
        ('Download Notebook', ':fa5-download:'),
    ]:
        assert source.count(label) == 1 and icon in source[: headings[0].start()], (
            'Gate 3: each button has its icon and belongs to docs chrome above the title'
        )
    tag_source = text(tags[0]).strip()
    assert source.count(tag_source) == 1 and source.index(tag_source) > headings[0].start(), (
        'Gate 3: docs publish the same one visible notebook tags cell under the title'
    )
    assert not chips(source.replace(tag_source, '')), (
        'Gate 3: native docs never add a second page-header tags line'
    )


@pytest.fixture
def generated_tables(tmp_path, monkeypatch):
    renderer = site_module('render_experiments', monkeypatch)
    for folder in ['user-guide', 'application', 'python', 'cli']:
        page = folder + '/tutorials/index.md'
        target = tmp_path / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((renderer.DOCS / page).read_text())
    monkeypatch.setattr(renderer, 'DOCS', tmp_path)
    records = read_records()
    for interface in ['application', 'cli']:
        source = ROOT / 'website/surfaces/docs' / interface / 'tutorials/cases'
        destination = tmp_path / interface / 'tutorials/cases'
        destination.mkdir()
        for page in source.glob('*.md'):
            (destination / page.name).write_text(page.read_text())
    renderer.write_tutorial_tables(
        records, {'python/tutorials/cases/' + row['id'] + '.md' for row in records}
    )
    return tmp_path, records


@pytest.mark.parametrize('interface', ['user-guide', 'application', 'python', 'cli'])
def test_overview_has_one_sectioned_table_with_record_tags_and_accessible_links(
    interface, generated_tables
):
    folder, records = generated_tables
    soup = BeautifulSoup((folder / interface / 'tutorials/index.md').read_text(), 'html.parser')
    assert 'Choose an example' not in soup.get_text(' ', strip=True), (
        'Gate 3/4: overviews remove the obsolete Choose an example introduction'
    )
    tables = soup.select('[data-example-catalogue] table')
    assert len(tables) == 1, 'Gate 3/4: each overview has one all-tutorials table'
    table = tables[0]
    sections = table.select('[data-tutorial-section]')
    assert [row['data-tutorial-section'] for row in sections] == [
        name for name, _ in RULES['sections']
    ], 'Gate 3/4: table section rows follow the five declared sections in order'
    assert all(row.select_one('svg') is not None for row in sections), (
        'Gate 3/4: every section row carries its shared app icon'
    )
    rows = [
        row
        for row in table.select('[data-example-row]')
        if any(
            link_is_case(link['href'], record['id'])
            for link in row.select('a[href]')
            for record in records
        )
    ]
    relevant = {'application': 'app', 'python': 'python', 'cli': 'cli'}.get(interface)
    selected = [row for row in records if relevant is None or relevant in declared_interfaces(row)]
    assert len(rows) == len(selected), (
        'Gate 3/4: an overview includes every selected case exactly once'
    )
    expected = [
        row for section, _ in RULES['sections'] for row in selected if row['section'] == section
    ]
    for row, record in zip(rows, expected, strict=True):
        assert [tag.get_text(' ', strip=True) for tag in row.select('.ed-tag')] == [
            tag['label'] for tag in record['tags']
        ], 'Gate 3/4: every overview row has exactly its record tag set'
        name = row.select_one('.ed-example-name')
        assert name is not None and (
            record['title'] in name.get_text(' ', strip=True)
            if len(declared_interfaces(record)) < 3
            else name.get_text(' ', strip=True) == record['title']
        ), 'Gate 3/4: overview row titles come from the corresponding case record'
        cells = row.find_all('td', recursive=False)
        assert len(cells) == (4 if interface == 'user-guide' else 1), (
            'Gate 3/4: only the all-interface table has link columns; interface tables link titles'
        )
        if interface != 'user-guide':
            assert name.find('a', href=True) is not None, (
                'Gate 3/4: overview titles link their tutorials'
            )
        else:
            assert_catalogue_coverage(
                row,
                declared_interfaces(record),
                title=cells[0].get_text(' ', strip=True),
                case=record['id'],
            )
    assert not table.select('thead th'), (
        'Gate 3/4: all tutorial tables start at section headings and omit column header rows'
    )


@pytest.mark.parametrize('interface', ['Application', 'Python', 'Command line'])
def test_built_navigation_groups_short_titles_under_the_five_iconed_sections(
    interface, monkeypatch
):
    builder = site_module('build', monkeypatch)
    records = read_records()
    monkeypatch.setattr(
        builder,
        'TUTORIAL_PAGES',
        [
            (
                row['section'],
                row.get('nav_title', row['title']),
                'python/tutorials/cases/' + row['id'] + '.md',
            )
            for row in records
        ],
    )
    config = builder._config_text(
        'surfaces',
        (ROOT / 'website/surfaces/mkdocs.yml').read_text(),
        ROOT / 'website/surfaces/docs/assets/site-components.css',
        None,
    )
    document = yaml.load(config, Loader=yaml.BaseLoader)
    matching_groups = [
        item[interface] for item in document['nav'] if isinstance(item, dict) and interface in item
    ]
    assert len(matching_groups) == 1, 'Gate 3/4: each interface uses its exact sentence-case name'
    groups = matching_groups[0]
    assert not any(isinstance(item, dict) and 'Examples' in item for item in groups), (
        'Gate 3/4: interface navigation uses Tutorials rather than Examples'
    )
    matching_tutorials = [
        item['Tutorials'] for item in groups if isinstance(item, dict) and 'Tutorials' in item
    ]
    assert len(matching_tutorials) == 1, (
        'Gate 3/4: each interface has exactly one Tutorials section'
    )
    tutorials = matching_tutorials[0]
    sections = [item for item in tutorials if isinstance(item, dict)]
    assert [next(iter(item)) for item in sections] == [name for name, _ in RULES['sections']], (
        'Gate 3/4: built navigation contains the five short section names in the owner order'
    )
    for name, icon in RULES['sections']:
        assert document['extra']['section_icons'][name].endswith('/' + icon), (
            'Gate 3/4: navigation sections use the declared shared icon'
        )
    names = [
        next(iter(entry))
        for item in sections
        for entries in item.values()
        for entry in entries
        if isinstance(entry, dict)
    ]
    case_names = {row['nav_title'] for row in records}
    names = [name for name in names if name in case_names]
    expected = [
        row['nav_title']
        for section, _ in RULES['sections']
        for row in records
        if row['section'] == section
        and {'Application': 'app', 'Python': 'python', 'Command line': 'cli'}[interface]
        in declared_interfaces(row)
    ]
    assert names == expected, 'Gate 3/4: built navigation uses the record short sample/code title'
