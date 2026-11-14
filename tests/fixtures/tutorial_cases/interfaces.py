"""Owner 4ba6d9b35: declared tutorial coverage, fixed catalog columns and visible limits."""

import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from tests.fixtures.tutorial_cases.contract import INTERFACES

LABELS = {'app': 'Application', 'python': 'Python', 'cli': 'Command line'}


def link_is_case(address, case):
    return any(
        PurePosixPath(part).stem == case for part in unquote(urlparse(address).path).split('/')
    )


def assert_scope_prefix(title, declared):
    if set(declared) == set(INTERFACES):
        return
    prefix = re.split(r'[:\u2014\u2013]', title, maxsplit=1)[0].casefold()
    prefix = re.sub(r'[^a-z]+', ' ', prefix).strip()
    if set(declared) == {'app'} and re.match(r'(built in|app only|application only)\b', prefix):
        return
    if set(declared) == {'python', 'cli'} and re.match(r'(your )?own (ai )?assistant\b', prefix):
        return
    assert all(
        re.search(r'\b' + re.escape(LABELS[item].casefold()) + r'\b', prefix) for item in declared
    ), 'Gate 3/4: a subset title begins with a prefix naming its declared interface limit'
    assert not any(
        re.search(r'\b' + re.escape(LABELS[item].casefold()) + r'\b', prefix)
        for item in set(INTERFACES) - set(declared)
    ), 'Gate 3/4: a subset title never advertises an undeclared interface'


def assert_catalogue_coverage(row, declared, title=None, case=None):
    cells = row.find_all('td', recursive=False)
    assert len(cells) == 4, (
        'Gate 3/4: the all-tutorials catalog retains all three interface columns'
    )
    assert_scope_prefix(title or cells[0].get_text(' ', strip=True), declared)
    for interface, cell in zip(INTERFACES, cells[1:], strict=True):
        links = cell.find_all('a', href=True)
        if interface not in declared:
            assert not links and cell.get_text(strip=True) in {'—', '\u2013', '-'}, (
                'Gate 3/4: each undeclared interface is a dash with no tutorial link'
            )
        else:
            expected_label = 'Open the ' + LABELS[interface] + ' tutorial'
            assert len(links) == 1 and (
                links[0].get('aria-label') in {expected_label, LABELS[interface]}
                if case
                else bool(links[0].get('aria-label', '').strip())
            ), 'Gate 3/4: every declared interface has exactly its accessible tutorial link'
            visible = [
                value.strip()
                for value in links[0].find_all(string=True)
                if value.strip()
                and not any(
                    tag.name in {'title', 'desc'} and tag.find_parent('svg') is not None
                    for tag in value.parents
                )
            ]
            assert not visible and links[0].find('svg') is not None, (
                'Gate 3/4: declared catalog link cells use their interface icon without text'
            )
            if case:
                assert link_is_case(links[0]['href'], case), (
                    'Gate 3/4: each declared tutorial link names the same case'
                )
