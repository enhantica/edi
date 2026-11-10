"""Owner 4ba6d9b35: actual catalog subsets advertise their scope and no absent links."""

from urllib.parse import urlparse

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_versions import assistant_version_sites  # noqa: F401
from tests.fixtures.tutorial_cases.contract import interfaces_for, read_records
from tests.fixtures.tutorial_cases.interfaces import assert_catalogue_coverage, link_is_case


def table_rows(root):
    page = root / 'user-guide/tutorials/index.html'
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    tables = soup.select('[data-example-catalogue] table')
    assert len(tables) == 1, 'Gate 3/4: the actual all-tutorials catalog has one shared table'
    return [
        row for row in tables[0].find_all('tr') if len(row.find_all('td', recursive=False)) == 4
    ]


def test_built_case_catalogue_uses_declared_interfaces_for_prefixes_and_dashes(
    assistant_version_sites,  # noqa: F811 - actual public docs builder
):
    rows = table_rows(assistant_version_sites['preview'])
    for record in read_records():
        matches = [
            row
            for row in rows
            if any(link_is_case(link['href'], record['id']) for link in row.select('a[href]'))
        ]
        assert len(matches) == 1, 'Gate 3/4: every case occurs once in the all-tutorials table'
        assert_catalogue_coverage(matches[0], interfaces_for(record['id']), case=record['id'])


@pytest.mark.parametrize('mode', ['built-in', 'own'])
def test_built_assistant_catalogue_rows_declare_their_distinct_interface_subsets(
    mode,
    assistant_version_sites,  # noqa: F811 - actual public docs builder
):
    rows = table_rows(assistant_version_sites['preview'])
    target = (
        '/application/tutorials/assistant/'
        if mode == 'built-in'
        else '/python/tutorials/assistant/'
    )
    matches = [
        row
        for row in rows
        if any(
            (urlparse(link['href']).path.rstrip('/').removesuffix('/index.html') + '/').endswith(
                target
            )
            for link in row.select('a[href]')
        )
    ]
    assert len(matches) == 1, (
        'Gate 3/4: built-in and own-assistant tutorials each have their own catalog row'
    )
    assert_catalogue_coverage(matches[0], ['app'] if mode == 'built-in' else ['python', 'cli'])
