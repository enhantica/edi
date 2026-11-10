"""Owner ad40429ab: verify the built user pages and map official services to artifacts."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.official_addresses import (
    DOCS,
    addresses,
    assert_public_addresses,
    assert_setup,
    resolve_official,
)
from tests.fixtures.tutorial_cases.pipeline import executed_inputs, stage


@pytest.fixture(scope='module')
def official_site(tmp_path_factory):
    root = stage(tmp_path_factory.mktemp('official-user-site') / 'source')
    for folder in ['data', 'app/qml', 'app/src']:
        shutil.copytree(ROOT / folder, root / folder)
    for source in (ROOT / 'docs/user/tutorials').glob('*.py'):
        shutil.copy2(source, root / 'docs/user/tutorials' / source.name)
    executed_inputs(root)  # Publication-only control outputs; no notebook execution claim.
    result = subprocess.run(
        [sys.executable, str(root / 'website/build.py'), 'surfaces', '--base-url', DOCS],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
        env={**os.environ, 'NO_COLOR': '1'},
    )
    (root / 'official-site-build.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'Gate 3/5/6: build the actual public user pages before checking their addresses: '
        + result.stdout[-2000:]
        + result.stderr[-3000:]
    )
    return root / 'website/_build'


def test_every_built_page_prompt_and_llms_index_uses_official_addresses(official_site):
    paths = [*official_site.rglob('*.html'), official_site / 'llms.txt']
    errors = []
    for path in paths:
        assert path.is_file(), 'Gate 3/5/6: the actual docs build includes its assistant index'
        try:
            assert_public_addresses(path.read_text())
        except AssertionError:
            errors.append(str(path.relative_to(official_site)))
    assert not errors, (
        'Gate 3/5/6: no built user page, prompt or assistant index names the old host: '
        + ', '.join(errors)
    )


@pytest.mark.parametrize('page', ['python/setup/index.html', 'cli/python/index.html'])
def test_built_setup_pages_use_real_commands_and_public_imports(page, official_site):
    path = official_site / page
    assert path.is_file(), 'Gate 6: the built setup page exists at its user address'
    assert_setup(path.read_text(), install_routes=page.startswith('python/'))


def test_all_official_links_resolve_in_the_corresponding_built_artifacts(official_site):
    roots = {
        'docs': official_site,
        'downloads': Path(
            os.environ.get('EDI_TUTORIAL_DOWNLOAD_ROOT', ROOT / 'build/publish-tree')
        ),
        'app': Path(os.environ.get('EDI_TUTORIAL_APP_ROOT', ROOT / 'build/wasm/site')),
        'contributor': Path(os.environ.get('EDI_TUTORIAL_CONTRIBUTOR_ROOT', ROOT / 'site/dev')),
    }
    links = set()
    for path in [*official_site.rglob('*.html'), official_site / 'llms.txt']:
        links.update(addresses(path.read_text()))
    assert links, 'Gate 3/5/6: built user pages expose real service links to resolve'
    errors = []
    for address in sorted(links):
        try:
            resolve_official(address, roots)
        except AssertionError as error:
            errors.append(address + ': ' + str(error))
    assert not errors, (
        'Gate 3/5/6: every official link resolves under the declared build mapping: '
        + '\n'.join(errors)
    )
