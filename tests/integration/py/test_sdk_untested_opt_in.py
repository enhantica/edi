"""The real SDK checker admits explicit local untested metadata without bypassing other checks."""

import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.untested_sdk.generate import clean_env, make, write_manifest

ROOT = Path(__file__).resolve().parents[3]


def check(tmp_path, platform, tested=None, allow=None, *, ci=None, damage=None):
    prefix, repo, _, _, manifest = make(tmp_path, platform)
    if tested is not None:
        manifest['tested'].update(copy.deepcopy(tested))
    if damage == 'fingerprint':
        manifest['fingerprint']['packages'][0]['version'] = '0.9'
    path = write_manifest(prefix, manifest)
    if damage == 'binary':
        (prefix / 'lib/libcrysta_core.a').write_bytes(b'changed after manifest hashing')
    script = repo / 'tools/ci/crysta_sdk.py'
    script.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/crysta_sdk.py', script)
    env = clean_env()
    if platform == 'osx-arm64':
        env['MACOSX_DEPLOYMENT_TARGET'] = '11.0'
    if allow is not None:
        env['EDI_ALLOW_UNTESTED_SDK'] = allow
    if ci:
        env[ci] = 'true'
    before = path.read_bytes()
    result = subprocess.run(
        [sys.executable, str(script), 'check', '--sdk', str(prefix), '--platform', platform],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert path.read_bytes() == before, 'The consumer check never rewrites qualification evidence'
    assert 'Traceback' not in result.stderr, 'SDK qualification refusals are explicit diagnostics'
    return result


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_a_fully_qualified_sdk_remains_accepted_without_an_override(tmp_path, platform):
    result = check(tmp_path, platform)
    assert result.returncode == 0, (
        'The independent SDK fixture otherwise meets every consumer check'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('tiers', ['both', 'cpp_tier', 'corpus'])
@pytest.mark.parametrize('allow', [None, '0', 'true', '01', '1'])
def test_untested_manifest_tiers_require_the_exact_local_opt_in(tmp_path, platform, tiers, allow):
    selected = ['cpp_tier', 'corpus'] if tiers == 'both' else [tiers]
    tested = {tier: {'untested': True} for tier in selected}
    result = check(tmp_path, platform, tested, allow)
    if allow == '1':
        assert result.returncode == 0, (
            'The explicit local opt-in admits honestly untested SDK tiers'
        )
    else:
        assert result.returncode != 0, 'An untested SDK is refused without the exact local opt-in'


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('tier', ['cpp_tier', 'corpus'])
@pytest.mark.parametrize(('passed', 'total'), [(0, 0), (0, 7), (6, 7), (8, 7)])
def test_opt_in_never_admits_partial_or_vacuous_numeric_qualification(
    tmp_path, platform, tier, passed, total
):
    tested = {'cpp_tier': {'untested': True}, 'corpus': {'untested': True}}
    tested[tier] = {'passed': passed, 'total': total}
    result = check(tmp_path, platform, tested, '1')
    assert result.returncode != 0, 'The opt-in never converts a failed qualification into untested'
    assert tier in result.stderr, 'The refusal reaches and identifies the incomplete numeric tier'


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('ci', ['CI', 'GITHUB_ACTIONS'])
def test_untested_sdk_opt_in_is_never_a_ci_permission(tmp_path, platform, ci):
    tested = {tier: {'untested': True} for tier in ['cpp_tier', 'corpus']}
    result = check(tmp_path, platform, tested, '1', ci=ci)
    assert result.returncode != 0, 'CI never consumes an SDK whose qualification was skipped'
    assert 'CI' in result.stderr, 'The consumer refuses specifically at the CI opt-in boundary'


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize(
    ('damage', 'diagnostic'), [('binary', 'libcrysta_core'), ('fingerprint', 'fingerprint')]
)
def test_untested_opt_in_keeps_binary_hash_and_toolchain_checks(
    tmp_path, platform, damage, diagnostic
):
    tested = {tier: {'untested': True} for tier in ['cpp_tier', 'corpus']}
    result = check(tmp_path, platform, tested, '1', damage=damage)
    assert result.returncode != 0, (
        'The opt-in never bypasses binary integrity or ABI compatibility'
    )
    assert diagnostic in result.stderr, 'The admitted local path reaches the damaged SDK property'


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('tier', ['cpp_tier', 'corpus'])
def test_an_untested_marker_cannot_hide_behind_retained_numeric_counts(tmp_path, platform, tier):
    tested = {tier: {'untested': True, 'passed': 7, 'total': 7}}
    result = check(tmp_path, platform, tested)
    assert result.returncode != 0, (
        'Untested tiers require opt-in even when they retain old numeric counts'
    )
