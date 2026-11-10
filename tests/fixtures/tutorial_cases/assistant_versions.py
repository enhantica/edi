"""Owner 3d85ed388: official prompt links across official, preview and local builds."""

import os
import shutil
import subprocess
import sys

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.pipeline import executed_inputs, stage

USER_BASE = 'https://easydiffraction.org/'
PROMPT_BASE = 'https://easydiffraction.org/'
PREVIEW_REF = 'e04-t45-examples-and-tutorials'
BASES = {
    'main': PROMPT_BASE,
    'preview': USER_BASE,
    'local': 'http://127.0.0.1:8873/',
}
_SHARED_SITES = pytest.StashKey[dict]()


@pytest.fixture(scope='module')
def assistant_version_sites(tmp_path_factory, request):
    cached = request.session.stash.get(_SHARED_SITES, None)
    if cached is not None:
        return cached
    sites = {}
    commit = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    for version, base in BASES.items():
        root = stage(tmp_path_factory.mktemp('assistant-' + version) / 'source')
        shutil.copytree(ROOT / 'data', root / 'data')
        shutil.copytree(ROOT / 'app/qml', root / 'app/qml')
        shutil.copytree(ROOT / 'app/src', root / 'app/src')
        for source in (ROOT / 'docs/user/tutorials').glob('*.py'):
            shutil.copy2(source, root / 'docs/user/tutorials' / source.name)
        # Authored notebook outputs isolate URL publication, never scientific accuracy.
        executed_inputs(root)
        result = subprocess.run(
            [sys.executable, str(root / 'website/build.py'), 'surfaces', '--base-url', base],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            env={
                **os.environ,
                'GITHUB_REF_NAME': 'main' if version == 'main' else PREVIEW_REF,
                'EDI_PREVIEW_PAGES_REF': '' if version == 'main' else PREVIEW_REF,
                'GITHUB_SHA': commit,
                'EDI_DOCS_REF': commit,
                'GITHUB_WORKSPACE': str(root),
                'NO_COLOR': '1',
            },
        )
        (root / 'assistant-version-build.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, (
            'Gate 3/5: the public docs build must publish the version before checking prompts: '
            + version
            + ': '
            + result.stdout[-2000:]
            + result.stderr[-3000:]
        )
        sites[version] = root / 'website/_build'
    request.session.stash[_SHARED_SITES] = sites
    return sites
