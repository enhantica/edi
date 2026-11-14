"""ADR-0083: a local qualified SDK cache still undergoes every binary/ABI check."""

import json
from pathlib import Path

import pytest

from tests.integration.py.test_c34_t28_pr_artifact import SHA, acquisition, fetch


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('change', ['unchanged', 'library', 'source', 'platform', 'abi', 'tier'])
def test_warm_sdk_revalidates_qualified_content_without_history_queries(
    tmp_path, platform, change
):
    context = acquisition(tmp_path, platform)
    code, output = fetch(context)
    assert code == 0, output
    home = context['root'] / 'build/crysta-sdk' / f'{SHA}-{platform}'
    for archive in Path(context['env']['CRYSTA_SDK_ARCHIVES']).iterdir():
        archive.unlink()
    manifest = home / 'share/crysta-sdk/manifest.json'
    row = json.loads(manifest.read_text())
    if change == 'library':
        (home / 'lib/libcrysta_core.a').write_bytes(b'changed after qualification')
    elif change == 'source':
        row['source_sha'] = 'b8' * 20
    elif change == 'platform':
        row['platform'] = 'win-64'
    elif change == 'abi':
        row['fingerprint']['packages'][0]['version'] = 'incompatible'
    elif change == 'tier':
        row['tested']['corpus']['passed'] -= 1
    manifest.write_text(json.dumps(row))
    before = (context['root'] / 'pixi.toml').read_bytes()
    code, output = fetch(context)
    assert (code == 0) == (change == 'unchanged'), output
    assert (context['root'] / 'pixi.toml').read_bytes() == before
