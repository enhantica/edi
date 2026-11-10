"""Owner 9eedd683b: folded walkthroughs leave Tutorials and keep working old URLs."""

import importlib.util
import json
from urllib.parse import urljoin, urlsplit

import pytest
import yaml
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.contract import ROOT

RETIRED = {
    'application/first-fit/': 'application/tutorials/',
    'application/scans/': 'application/tutorials/',
    'python/tutorials/example-fit/': 'python/tutorials/',
    'cli/tutorials/example-fit/': 'cli/tutorials/',
}


def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
    elif isinstance(value, str):
        yield value


@pytest.mark.parametrize('interface', ['Application', 'Python', 'Command line'])
def test_folded_walkthrough_entries_are_gone_from_each_tutorials_section(interface):
    navigation = yaml.load(
        (ROOT / 'website/surfaces/mkdocs.yml').read_text(), Loader=yaml.BaseLoader
    )['nav']
    sections = [
        item[interface] for item in navigation if isinstance(item, dict) and interface in item
    ]
    assert len(sections) == 1, 'Gate 3: every interface has exactly one docs navigation section'
    tutorials = [
        item['Tutorials'] for item in sections[0] if isinstance(item, dict) and 'Tutorials' in item
    ]
    assert len(tutorials) == 1, 'Gate 3: each interface has one Tutorials section'
    entries = list(walk(tutorials[0]))
    assert not {'Example fit', 'Work with a scan'} & set(entries), (
        'Gate 3: Example fit and Work with a scan leave every Tutorials section'
    )
    assert not any(value.removesuffix('.md').strip('/') + '/' in RETIRED for value in entries), (
        'Gate 3: renaming a legacy navigation label cannot leave its retired URL in Tutorials'
    )


def redirect_target(mapping, old):
    seen = set()
    current = old
    while current in mapping:
        assert current not in seen, 'Gate 3: old tutorial URLs redirect without a cycle'
        seen.add(current)
        current = mapping[current]
    assert seen, 'Gate 3: every retired walkthrough URL has an explicit redirect: ' + old
    assert current.startswith(RETIRED[old]) and current != RETIRED[old], (
        'Gate 3: a retired walkthrough leads to a case tutorial on the same interface'
    )
    return current


@pytest.mark.parametrize('old', RETIRED)
def test_old_walkthrough_urls_generate_real_redirects_to_case_tutorials(
    old, tmp_path, monkeypatch
):
    mapping = json.loads((ROOT / 'website/redirects.json').read_text())
    target = redirect_target(mapping, old)
    for new in mapping.values():
        path = tmp_path / new / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '<title>Page moved - EasyDiffraction</title>'
            if new in mapping
            else '<h1>Case tutorial</h1>'
        )
    monkeypatch.syspath_prepend(str(ROOT / 'website'))
    spec = importlib.util.spec_from_file_location(
        'tutorial_redirect_builder', ROOT / 'website/build.py'
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder._write_redirects(tmp_path, 'https://docs.example/preview/')
    current = old
    while current in mapping:
        page = BeautifulSoup((tmp_path / current / 'index.html').read_text(), 'html.parser')
        refresh = page.find('meta', attrs={'http-equiv': 'refresh'})
        assert refresh is not None, 'Gate 3: the old URL emits an actual automatic redirect page'
        destination = refresh['content'].split('url=', 1)[1]
        resolved = urlsplit(urljoin('https://docs.example/preview/' + current, destination)).path
        assert resolved == '/preview/' + mapping[current], (
            'Gate 3: generated redirect links resolve correctly below a hosted path prefix'
        )
        canonical = page.find('link', rel='canonical')
        assert (
            canonical is not None
            and canonical['href'] == 'https://docs.example/preview/' + mapping[current]
        ), 'Gate 3: the generated legacy page names its canonical current tutorial URL'
        current = mapping[current]
    assert current == target and (tmp_path / target / 'index.html').is_file(), (
        'Gate 3: the complete redirect chain terminates at a real current case page'
    )


@pytest.mark.parametrize('escape', ['missing', 'cycle', 'wrong-interface', 'overview'])
def test_redirect_observer_refuses_missing_cyclic_and_wrong_destinations(escape):
    old = 'python/tutorials/example-fit/'
    good = 'python/tutorials/cases/pd-neut-cwl_y2o3-spodi/'
    assert redirect_target({old: good}, old) == good, (
        'Gate 3: a valid case redirect passes the observer'
    )
    broken = {
        'missing': {},
        'cycle': {old: old},
        'wrong-interface': {old: 'application/tutorials/cases/pd-neut-cwl_y2o3-spodi/'},
        'overview': {old: 'python/tutorials/'},
    }[escape]
    with pytest.raises(AssertionError, match='Gate 3:'):
        redirect_target(broken, old)
