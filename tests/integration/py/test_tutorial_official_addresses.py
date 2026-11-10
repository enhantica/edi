"""Owner ad40429ab: every user source uses official addresses and usable setup commands."""

import json

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.official_addresses import (
    APP,
    DOCS,
    INDEX,
    assert_public_addresses,
    assert_setup,
    resolve_official,
)


@pytest.mark.parametrize('surface', ['pages', 'notebooks', 'scripts'])
def test_all_user_sources_use_the_official_addresses(surface):
    if surface == 'pages':
        paths = sorted((ROOT / 'website/surfaces/docs').rglob('*.md'))
    else:
        suffix = '*.ipynb' if surface == 'notebooks' else '*.py'
        paths = sorted((ROOT / 'docs/user/tutorials').glob(suffix))
    assert paths, 'Gate 3/5/6: each user-facing source surface is populated'
    errors = []
    for path in paths:
        payload = path.read_text()
        if path.suffix == '.ipynb':
            payload = json.dumps(json.loads(payload), ensure_ascii=False)
        try:
            assert_public_addresses(payload)
        except AssertionError:
            errors.append(str(path.relative_to(ROOT)))
    assert not errors, (
        'Gate 3/5/6: every user source uses official publication addresses: ' + ', '.join(errors)
    )


@pytest.mark.parametrize('page', ['python/setup.md', 'cli/python.md'])
def test_python_setup_sources_are_usable_without_placeholders_or_legacy_imports(page):
    assert_setup(
        (ROOT / 'website/surfaces/docs' / page).read_text(),
        install_routes=page.startswith('python/'),
    )


GOOD = f'''# Set up Python
```toml
[pypi-options]
extra-index-urls = ["{INDEX}"]
```
```console
pixi add --pypi easydiffraction
python -m pip install easydiffraction --extra-index-url {INDEX}
python -c "import easydiffraction as edi; print(edi.Project)"
```
[Contributor documentation](https://github.com/enhantica/edi/blob/main/CONTRIBUTING.md)
'''


@pytest.mark.parametrize(
    'damage',
    [
        'version',
        'wheel-link',
        'legacy-import',
        'no-import',
        'no-pixi',
        'bad-index',
        'source-build',
        'source-build-bold',
        'source-build-html',
        'dev-command',
    ],
)
def test_setup_observer_refuses_each_non_user_installation_route(damage):
    assert_setup(GOOD, install_routes=True)
    broken = {
        'version': GOOD + '\neasydiffraction = "==VERSION"',
        'wheel-link': GOOD + '\npip install WHEEL_LINK',
        'legacy-import': GOOD.replace('import easydiffraction as edi', 'import edi'),
        'no-import': GOOD.replace('import easydiffraction as edi', 'pass'),
        'no-pixi': GOOD.replace('pixi add --pypi easydiffraction', 'pixi install'),
        'bad-index': GOOD.replace(INDEX, 'https://example.org/simple/'),
        'source-build': GOOD + '\n## From source\npixi run core-build\n',
        'source-build-bold': GOOD + '\n## **From source**\n',
        'source-build-html': GOOD + '<h2><em>From source</em><a>anchor</a></h2>',
        'dev-command': GOOD + '\n```console\ngit clone https://github.com/enhantica/edi\n```',
    }[damage]
    with pytest.raises(AssertionError, match='Gate 6:'):
        assert_setup(broken, install_routes=True)


@pytest.mark.parametrize(
    'spelling',
    [
        'https://enhantica.github.io/edi/',
        'https://ENHANTICA.GITHUB.IO/edi/',
        'https://enhantica%2egithub.io/edi/',
    ],
)
def test_address_observer_rejects_old_hosts_and_keeps_github_source_links(spelling):
    assert_public_addresses(GOOD + '\n' + APP + '\n' + DOCS)
    with pytest.raises(AssertionError, match='Gate 3/5/6:'):
        assert_public_addresses('User documentation: ' + spelling)


@pytest.mark.parametrize(
    'damage',
    ['missing', 'traversal', 'symlink', 'http', 'anchor', 'case-host', 'port', 'unknown-service'],
)
def test_official_mapping_cannot_hide_a_missing_or_escaping_service_target(tmp_path, damage):
    roots = {kind: tmp_path / kind for kind in ['docs', 'downloads', 'app', 'contributor']}
    for root in roots.values():
        root.mkdir()
        (root / 'index.html').write_text('<p id="intro">real artifact</p>')
    (roots['downloads'] / 'pypi/simple').mkdir(parents=True)
    (roots['downloads'] / 'pypi/simple/index.html').write_text('real index')
    for address in [DOCS, DOCS + 'dev/', APP, INDEX]:
        assert resolve_official(address, roots).is_file(), (
            'Gate 3/5/6: each official service resolves against its own artifact'
        )
    assert resolve_official('https://github.com/enhantica/edi', roots) is None, (
        'Gate 3/5/6: GitHub repository sources remain external links'
    )
    if damage == 'symlink':
        (roots['docs'] / 'escape.html').symlink_to(roots['app'] / 'index.html')
    target = {
        'missing': DOCS + 'absent/',
        'traversal': DOCS + '../outside.html',
        'symlink': DOCS + 'escape.html',
        'http': DOCS.replace('https:', 'http:'),
        'anchor': DOCS + '#absent',
        'case-host': DOCS.upper() + 'absent/',
        'port': 'https://easydiffraction.org:8443/',
        'unknown-service': 'https://docs.easydiffraction.org/',
    }[damage]
    with pytest.raises(AssertionError, match='Gate 3/5/6:'):
        resolve_official(target, roots)
