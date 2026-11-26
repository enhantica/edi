# SPDX-License-Identifier: BSD-3-Clause
"""Release versions YY.N and their order against the old YYYY.MM.N releases (edi ADR-0106)."""

import datetime
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('release_plan', ROOT / 'tools/release/plan.py')
PLAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLAN)

# The 16 stable releases of 2026 before YY.N.
OLD_2026 = [
    '2026.11.0',
    *(f'2026.11.{n}' for n in range(8, 15)),
    '2026.11.20',
    '2026.11.22',
    '2026.11.24',
    *(f'2026.11.{n}' for n in range(27, 32)),
]


def test_old_releases_sort_before_the_first_year_counter():
    ordered = ['2026.11.0', '2026.11.31', '26.17', '26.18', '27.1']
    shuffled = ['26.18', '2026.11.31', '27.1', '2026.11.0', '26.17']
    assert sorted(shuffled, key=PLAN.version_key) == ordered
    assert PLAN.version_key('2026.11.9') < PLAN.version_key('2026.11.10')
    assert PLAN.version_key('26.9') < PLAN.version_key('26.10')


@pytest.mark.parametrize(
    'version', ['26.0', '26.017', '05.1', '126.1', '2026.17', 'v26.17', '26.17 ', '2026.13.0']
)
def test_malformed_versions_are_refused(version):
    with pytest.raises(ValueError, match='Invalid'):
        PLAN.version_key(version)


def test_the_year_counter_carries_on_from_the_old_releases():
    assert len(OLD_2026) == 16
    today = datetime.date(2026, 11, 26)
    assert PLAN.next_calendar_version(OLD_2026, today) == '26.17'
    assert PLAN.next_calendar_version([*OLD_2026, '26.17'], today) == '26.18'
    december = datetime.date(2026, 12, 1)
    assert PLAN.next_calendar_version([*OLD_2026, '26.17', '26.18'], december) == '26.19'
    assert PLAN.next_calendar_version([*OLD_2026, '26.40'], datetime.date(2027, 1, 2)) == '27.1'
    assert PLAN.next_calendar_version(['27.1', '27.2'], datetime.date(2027, 3, 1)) == '27.3'


def test_the_calendar_cannot_move_backwards():
    with pytest.raises(ValueError, match='backwards'):
        PLAN.next_calendar_version(['27.1'], datetime.date(2026, 12, 31))


def test_a_rerun_keeps_its_version():
    commit = 'a' * 40
    request = {
        'number': 3,
        'title': 'Show the update date',
        'merged_at': '2026-11-26T12:00:00Z',
        'merge_commit_sha': commit,
        'labels': ['🐞 bug', '🖥️ desktop'],
    }
    history = [{'version': version, 'commit': 'b' * 40} for version in OLD_2026]
    first = PLAN.release_plan([request], history, commit, {commit}, datetime.date(2026, 11, 26))
    assert first['version'] == '26.17'
    again = PLAN.release_plan(
        [request], [*history, first], commit, {commit}, datetime.date(2026, 11, 27)
    )
    assert again == first


@pytest.mark.parametrize(
    ('version', 'preview', 'title'),
    [
        ('26.17', False, 'EasyDiffraction 26.17 (26 Nov 2026)'),
        ('26.17', True, 'EasyDiffraction 26.17 (26 Nov 2026) preview'),
        ('2026.11.31', False, 'v2026.11.31 (26 Nov)'),
    ],
)
def test_release_titles(version, preview, title):
    assert PLAN.release_title(version, '2026-11-26', preview=preview) == title


@pytest.mark.parametrize(
    ('version', 'platform', 'kind', 'stem'),
    [
        ('26.17', 'macOS-arm64', 'online', 'EasyDiffraction-26.17-macOS-arm64'),
        ('26.17', 'Windows-x64', 'offline', 'EasyDiffraction-Offline-26.17-Windows-x64'),
        ('27.1', 'Linux-x64', 'online', 'EasyDiffraction-27.1-Linux-x64'),
        (
            '2026.11.31',
            'macOS-arm64',
            'online',
            'EasyDiffraction-Installer-2026.11.31-macOS-arm64',
        ),
    ],
)
def test_installer_file_names(version, platform, kind, stem):
    assert PLAN.installer_stem(version, platform, kind) == stem


@pytest.mark.parametrize('version', ['0.0.0', '0.0.412.1'])
def test_test_builds_name_their_installers_but_never_plan_a_release(version):
    assert PLAN.installer_stem(version, 'Linux-x64', 'online') == (
        f'EasyDiffraction-Installer-{version}-Linux-x64'
    )
    with pytest.raises(ValueError, match='Invalid calendar release version'):
        PLAN.version_key(version)


@pytest.mark.parametrize('version', ['0.0.01', '0.1.2', '1.0'])
def test_other_versions_still_name_no_installer(version):
    with pytest.raises(ValueError, match='Invalid calendar release version'):
        PLAN.installer_stem(version, 'Linux-x64', 'online')


def test_download_names_in_the_release_tools():
    spec = importlib.util.spec_from_file_location('promote', ROOT / 'tools/release/promote.py')
    promote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(promote)
    assert promote.installer_name('26.17', 'macos-arm64', 'online') == (
        'EasyDiffraction-26.17-macOS-arm64.dmg'
    )
    assert promote.installer_name('26.17', 'windows-x86_64', 'offline') == (
        'EasyDiffraction-Offline-26.17-Windows-x64.exe'
    )
    assert promote.installer_name('26.17', 'linux-x86_64', 'online') == (
        'EasyDiffraction-26.17-Linux-x64.zip'
    )
