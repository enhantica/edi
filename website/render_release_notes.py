# SPDX-License-Identifier: BSD-3-Clause
"""Render published GitHub release notes for the user documentation."""

import json
import re
from html import escape
from operator import itemgetter
from pathlib import Path

INTERFACES = json.loads(
    (Path(__file__).resolve().parents[1] / 'data/release-interfaces.json').read_text(
        encoding='utf-8'
    )
)
NOTE = re.compile(r'^(- .+?) <!-- interfaces: ([a-z,-]+) -->[ \t]*$', re.MULTILINE)
LEGACY_NOTE = re.compile(r'^(- )<!-- interfaces: ([a-z,-]+) --> (.+)$', re.MULTILINE)


def _pills(interfaces: list[str]) -> str:
    return ' '.join(
        f'**:{icon}: {label}**{{ .ed-release-interface }}'
        for icon, label in (INTERFACES[interface] for interface in interfaces)
    )


def _label_note(match: re.Match[str]) -> str:
    interfaces = match[2].split(',')
    labels = ' '.join(f'`{INTERFACES[interface][1]}`' for interface in interfaces)
    return match[1].removesuffix(' ' + labels) + ' ' + _pills(interfaces)


def _label_legacy_note(match: re.Match[str]) -> str:
    interfaces = match[2].split(',')
    text = match[3]
    for interface in interfaces:
        text = text.removeprefix(f'`{INTERFACES[interface][1]}` ')
    return match[1] + text + ' ' + _pills(interfaces)


def render(pages: list[list[dict]]) -> str:
    """List public releases by publication date, with previews clearly marked."""
    releases = sorted(
        (release for page in pages for release in page if not release['draft']),
        key=itemgetter('published_at'),
        reverse=True,
    )
    sections = [
        "# What's new",
        'Changes in published EasyDiffraction releases, newest first.',
    ]
    for release in releases:
        title = escape(release['name'] or release['tag_name'])
        date = release['published_at'][:10]
        channel = 'Prerelease' if release['prerelease'] else 'Stable'
        body = NOTE.sub(_label_note, release['body'] or '')
        body = LEGACY_NOTE.sub(_label_legacy_note, body).strip()
        # Keep release headings subordinate to the version heading in the page outline.
        body = re.sub(r'^#{1,2}(?= )', '###', body, flags=re.MULTILINE)
        sections.extend([
            f'## {title}',
            f'**{channel}** · {date} · [View on GitHub]({release["html_url"]})',
            body,
            '---',
        ])
    if not releases:
        sections.extend([
            'No releases have been published yet.',
            '## Release note example',
            'These example notes show how affected interfaces will appear.',
            '- Improve plot zoom. ' + _pills(['desktop', 'web']) + '\n'
            '- Read project metadata from a script or notebook. ' + _pills(['python']),
        ])
    return '\n\n'.join(sections).removesuffix('\n\n---') + '\n'
