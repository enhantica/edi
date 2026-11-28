# SPDX-License-Identifier: BSD-3-Clause
"""Release versions, one place for every tool that makes, reads or compares one (edi ADR-0106).

A release is YY.N: the year's last two digits and a counter within the year (26.17, then 27.1).
Releases up to November 2026 were YYYY.MM.N; they keep their tags and still sort first.
"""

import datetime
import re

NEW = re.compile(r'([1-9][0-9])\.([1-9][0-9]*)')
OLD = re.compile(r'([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')
# A test build's version: 0.0.<run>.<attempt> from the installers workflow, 0.0.0 from a
# local package run. Only an installer's file name takes it; a release plan never does.
TESTING = re.compile(r'0\.0\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?')
# Any release version, without anchors, for building other patterns (tags, file names).
PATTERN = r'(?:[0-9]{4}\.(?:0[1-9]|1[0-2])\.(?:0|[1-9][0-9]*)|[1-9][0-9]\.[1-9][0-9]*)'

# Stable releases a year already had under the old form, so its counter carries on from them:
# 2026 had v2026.11.0, .8 to .14, .20, .22, .24 and .27 to .31, so its first YY.N is 26.17.
OLD_RELEASES = {2026: 16}

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def version_key(version: str) -> tuple[int, int, int, int]:
    """The order of releases: every old YYYY.MM.N before the YY.N releases of its year and after.

    Plain numbers would put 26.17 below 2026.11.31, so the year leads and the form comes second.
    """
    if match := NEW.fullmatch(version):
        return 2000 + int(match[1]), 1, int(match[2]), 0
    match = OLD.fullmatch(version)
    if not match or int(match[1]) < 2000:
        raise ValueError(f'Invalid calendar release version: {version}')
    return int(match[1]), 0, int(match[2]), int(match[3])


def is_version(version: str) -> bool:
    try:
        version_key(version)
    except (TypeError, ValueError):
        return False
    return True


def is_new(version: str) -> bool:
    return NEW.fullmatch(version) is not None


def next_version(versions: list[str], today: datetime.date) -> str:
    """The next free YY.N for today, given every version already taken, drafts included.

    A retry never comes here: it finds the version its draft or release already holds.
    """
    keys = [version_key(version) for version in versions]
    if any(key[0] > today.year for key in keys):
        raise ValueError('The release calendar cannot move backwards')
    counter = max([
        OLD_RELEASES.get(today.year, 0),
        *(key[2] for key in keys if key[0] == today.year and key[1] == 1),
    ])
    return f'{today.year % 100:02d}.{counter + 1}'


def shown_date(date: str) -> str:
    """A date as users read it: ``26 Nov 2026``."""
    day = datetime.date.fromisoformat(date)
    return f'{day.day} {MONTHS[day.month - 1]} {day.year}'


def release_title(version: str, date: str, *, preview: bool = False) -> str:
    """A GitHub release's title: ``v26.17 · 26 Nov 2026``, or ``v2026.11.14 · 13 Nov 2026``."""
    if not is_new(version):
        version_key(version)
    title = f'v{version} · {shown_date(date)}'
    return title + ' preview' if preview else title


def release_titles(version: str, date: str, *, preview: bool = False) -> set[str]:
    """Every title a release may carry: the current one and the one used before it.

    Releases published before the titles were shortened kept ``EasyDiffraction 26.17 (26 Nov
    2026)`` or ``v2026.11.14 (13 Nov)`` until they were renamed.
    """
    if is_new(version):
        old = f'EasyDiffraction {version} ({shown_date(date)})'
    else:
        day = datetime.date.fromisoformat(date)
        old = f'v{version} ({day.day} {MONTHS[day.month - 1]})'
    old = old + ' preview' if preview else old
    return {release_title(version, date, preview=preview), old}


def installer_stem(version: str, platform: str, kind: str) -> str:
    """An installer download's name without its suffix: ``EasyDiffraction-26.17-macOS-arm64``.

    `platform` is the name downloads show (macOS-arm64, Windows-x64, Linux-x64). Old releases were
    named EasyDiffraction-Installer-<version>-<platform>.
    """
    offline = '-Offline' if kind == 'offline' else ''
    if is_new(version):
        return f'EasyDiffraction{offline}-{version}-{platform}'
    if not TESTING.fullmatch(version):
        version_key(version)
    return f'EasyDiffraction-Installer{offline}-{version}-{platform}'
