# SPDX-License-Identifier: BSD-3-Clause
"""Render published GitHub release notes for the user documentation."""

import json
import re
import sys
from html import escape
from operator import itemgetter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/release'))
import versions

INTERFACES = json.loads(
    (Path(__file__).resolve().parents[1] / 'data/release-interfaces.json').read_text(
        encoding='utf-8'
    )
)
NOTE = re.compile(r'^(- .+?) <!-- interfaces: ([a-z,-]+) -->[ \t]*$', re.MULTILINE)
HEADING = re.compile(r'^#{1,6} +(.+?)[ #]*$')
LEGACY_NOTE = re.compile(r'^(- )<!-- interfaces: ([a-z,-]+) --> (.+)$', re.MULTILINE)
RELEASE_DATE = re.compile(r'<!-- edi release date ([0-9]{4}-[0-9]{2}-[0-9]{2}) -->')
# Older notes repeated the version as their own first heading.
VERSION_HEADING = re.compile(r'\A# EasyDiffraction [^\n]*\n+')
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
# The descriptions of the matching GitHub labels.
DESCRIPTIONS = {
    'desktop': 'Affects the EasyDiffraction desktop app',
    'web': 'Affects the EasyDiffraction web app',
    'python': 'Affects the Python API in scripts or notebooks',
    'cli-python': 'Affects the CLI installed from the Python package',
    'cli-standalone': 'Affects the standalone CLI executable',
}


def _pills(interfaces: list[str]) -> str:
    return ' '.join(
        f'**:{icon}: {short}**{{ .ed-release-interface }}'
        for icon, _, short in (INTERFACES[interface] for interface in interfaces)
    )


def _label_note(match: re.Match[str]) -> str:
    interfaces = match[2].split(',')
    text = match[1]
    for interface in reversed(interfaces):
        _, label, short = INTERFACES[interface]
        text = text.removesuffix(f' `{short}`').removesuffix(f' `{label}`')
    return text + ' ' + _pills(interfaces)


def _label_legacy_note(match: re.Match[str]) -> str:
    interfaces = match[2].split(',')
    text = match[3]
    for interface in interfaces:
        text = text.removeprefix(f'`{INTERFACES[interface][1]}` ')
    return match[1] + text + ' ' + _pills(interfaces)


def _flatten_headings(body: str) -> str:
    """Show a note's own headings as bold lines, so "On this page" lists only the releases."""
    lines, fenced = [], False
    for line in body.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
        heading = None if fenced else HEADING.match(line)
        lines.append(f'**{heading[1]}**' if heading else line)
    return '\n'.join(lines)


def _date(release: dict) -> str:
    """The release date: the recorded one, else the publication date."""
    recorded = RELEASE_DATE.search(release['body'] or '')
    return recorded[1] if recorded else release['published_at'][:10]


def _day(release: dict) -> str:
    """The release day as users read it: ``26 Nov 2026``, or ``13 Nov`` for an old YYYY.MM.N."""
    date = _date(release)
    if versions.is_new(release['tag_name'].removeprefix('v')):
        return versions.shown_date(date)
    _, month, day = map(int, date.split('-'))
    return f'{day} {MONTHS[month - 1]}'


def _title(release: dict) -> str:
    """The release title, as GitHub shows it: ``EasyDiffraction 26.17 (26 Nov 2026)``."""
    version = release['tag_name'].removeprefix('v')
    if versions.is_new(version):
        title = versions.release_title(version, _date(release))
    else:
        # Old releases show their tag and day, as their titles on GitHub do.
        title = f'{release["tag_name"]} ({_day(release)})'
    return escape(title) + (' preview' if release['prerelease'] else '')


def latest_release(pages: list[list[dict]]) -> str:
    """The home page line naming the latest published release, or nothing before the first."""
    releases = [
        release
        for page in pages
        for release in page
        if not release['draft'] and not release['prerelease']
    ]
    if not releases:
        return ''
    latest = max(releases, key=itemgetter('published_at'))
    tag = latest['tag_name']
    # Users read a YY.N version without the tag's "v".
    shown = tag.removeprefix('v') if versions.is_new(tag.removeprefix('v')) else tag
    return (
        '<p class="ed-landing__release" markdown="span">EasyDiffraction '
        f'[{escape(shown)}](changelog.md) · released {_day(latest)}</p>'
    )


def render(pages: list[list[dict]]) -> str:
    """List public releases by publication date, with previews clearly marked."""
    releases = sorted(
        (release for page in pages for release in page if not release['draft']),
        key=itemgetter('published_at'),
        reverse=True,
    )
    sections = [
        # The navigation shows each About page's icon (the nav-icon check).
        "---\nicon: fa5/bullhorn\n---\n\n# What's new",
        (
            'Changes in published EasyDiffraction releases, newest first. '
            'The labels show which part of EasyDiffraction a change affects:'
        ),
        '\n'.join(f'- {_pills([key])} {text}' for key, text in DESCRIPTIONS.items()),
    ]
    for release in releases:
        body = VERSION_HEADING.sub('', release['body'] or '')
        body = NOTE.sub(_label_note, body)
        body = LEGACY_NOTE.sub(_label_legacy_note, body).strip()
        body = _flatten_headings(body)
        sections.extend([f'## [{_title(release)}]({release["html_url"]})', body, '---'])
    if not releases:
        sections.extend([
            'No releases have been published yet.',
            '## Release note example',
            'These example notes show how affected interfaces will appear.',
            '- Improve plot zoom. ' + _pills(['desktop', 'web']) + '\n'
            '- Read project metadata from a script or notebook. ' + _pills(['python']),
        ])
    return '\n\n'.join(sections).removesuffix('\n\n---') + '\n'
