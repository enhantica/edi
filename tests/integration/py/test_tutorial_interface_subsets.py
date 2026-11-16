"""Owner 4ba6d9b35: default coverage and subsets come from declarations, not missing files."""

import pytest
import yaml
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.contract import (
    CASES,
    INTERFACES,
    cases_for,
    declared_interfaces,
    interfaces_for,
    read_records,
)
from tests.fixtures.tutorial_cases.interfaces import assert_catalogue_coverage


@pytest.mark.parametrize('selection', [None, ['app'], ['python'], ['cli'], ['python', 'cli']])
def test_case_interface_selection_defaults_to_all_and_respects_every_declared_subset(
    tmp_path, selection
):
    rows = [{'id': case} for case in CASES]
    if selection is not None:
        rows[0]['interfaces'] = selection
    folder = tmp_path / 'docs/user/cli'
    folder.mkdir(parents=True)
    (folder / 'projects.yml').write_text(yaml.safe_dump({'projects': rows}))
    expected = list(INTERFACES) if selection is None else selection
    assert list(interfaces_for(CASES[0], tmp_path)) == expected, (
        'Gate 1/3/4: default-all and explicit tutorial subsets retain their exact declaration'
    )
    for interface in INTERFACES:
        assert (CASES[0] in cases_for(interface, root=tmp_path)) == (interface in expected), (
            'Gate 1/3/4: a gate requires artifacts only on declared interfaces'
        )
    assert (CASES[0] in cases_for('app', 'python', root=tmp_path)) == (
        {'app', 'python'} <= set(expected)
    ), 'Gate 3/4: cross-interface stage comparisons require both interfaces to be declared'

    (folder / 'projects.yml').write_text(yaml.safe_dump({'projects': []}))
    assert list(interfaces_for(CASES[0], tmp_path)) == list(INTERFACES), (
        'Gate 1/3/4: a missing selected case cannot opt out of any required tutorial interface'
    )
    assert cases_for('app', 'python', 'cli', root=tmp_path) == CASES, (
        'Gate 1/3/4: missing declarations still collect all selected case witnesses'
    )
    with pytest.raises(AssertionError, match='one source interface declaration'):
        interfaces_for('undeclared-noncase', tmp_path)


@pytest.mark.parametrize('selection', [[], ['other'], ['app', 'app'], 'python'])
def test_invalid_tutorial_subsets_are_refused(selection):
    with pytest.raises(AssertionError, match='Gate 1/3/4:'):
        declared_interfaces({'interfaces': selection})


@pytest.mark.parametrize(
    'damage',
    [None, 'missing-prefix', 'extra-link', 'missing-dash', 'wrong-case', 'link-text', 'svg-text'],
)
def test_subset_catalogue_observer_requires_prefix_dashes_and_only_declared_links(damage):
    soup = BeautifulSoup(
        '<table><tr><td>Python only: Control</td><td>—</td>'
        '<td><a href="python/tutorials/cases/control/" aria-label="Open the Python tutorial">'
        '<svg><title>Python</title><desc>Interface icon</desc></svg></a></td>'
        '<td>—</td></tr></table>',
        'html.parser',
    )
    row = soup.tr
    assert_catalogue_coverage(row, ['python'], case='control')
    if damage == 'missing-prefix':
        row.td.string = 'Control'
    elif damage == 'extra-link':
        row.find_all('td')[1].append(BeautifulSoup('<a href="app/">Open</a>', 'html.parser').a)
    elif damage == 'missing-dash':
        row.find_all('td')[3].string = ''
    elif damage == 'wrong-case':
        row.a['href'] = 'python/tutorials/cases/other/'
    elif damage == 'link-text':
        row.a.append('Unexpected visible text')
    elif damage == 'svg-text':
        row.a.svg.append(
            BeautifulSoup('<text>Unexpected visible text</text>', 'html.parser').find('text')
        )
    if damage:
        with pytest.raises(AssertionError, match='Gate 3/4:'):
            assert_catalogue_coverage(row, ['python'], case='control')


def test_real_case_record_export_keeps_declared_interface_coverage():
    for record in read_records():
        assert set(declared_interfaces(record)) == set(interfaces_for(record['id'])), (
            'Gate 1: exported tutorial interfaces equal the independent registry declaration'
        )


@pytest.mark.parametrize('selection', [['app'], ['python'], ['cli'], ['python', 'cli']])
def test_real_table_renderer_obeys_a_declared_case_subset(selection, tmp_path, monkeypatch):
    from tests.integration.py.test_tutorial_docs_presentation import site_module  # noqa: PLC0415

    renderer = site_module('render_experiments', monkeypatch)
    for interface in ['user-guide', 'application', 'python', 'cli']:
        relative = interface + '/tutorials/index.md'
        target = tmp_path / relative
        target.parent.mkdir(parents=True)
        target.write_text((renderer.DOCS / relative).read_text())
    record = dict(read_records()[2])
    for interface in ['application', 'cli']:
        relative = interface + '/tutorials/cases/' + record['id'] + '.md'
        target = tmp_path / relative
        target.parent.mkdir(parents=True)
        target.write_text((renderer.DOCS / relative).read_text())
    monkeypatch.setattr(renderer, 'DOCS', tmp_path)
    record['interfaces'] = selection
    renderer.write_tutorial_tables([record], {'python/tutorials/cases/' + record['id'] + '.md'})
    soup = BeautifulSoup((tmp_path / 'user-guide/tutorials/index.md').read_text(), 'html.parser')
    from tests.fixtures.tutorial_cases.interfaces import link_is_case  # noqa: PLC0415

    rows = [
        row
        for row in soup.select('tr')
        if any(link_is_case(link['href'], record['id']) for link in row.select('a[href]'))
    ]
    assert len(rows) == 1, 'Gate 3/4: a declared subset remains one real generated catalog row'
    assert_catalogue_coverage(rows[0], selection, case=record['id'])
