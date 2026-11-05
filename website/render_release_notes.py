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
NOTE = re.compile(r'^(- )<!-- interfaces: ([a-z,-]+) --> (.+)$', re.MULTILINE)


def _label_note(match: re.Match[str]) -> str:
    labels = []
    text = match[3]
    for interface in match[2].split(','):
        icon, label = INTERFACES[interface]
        text = text.removeprefix(f'`{label}` ')
        labels.append(f'**:{icon}: {label}**{{ .ed-release-interface }}')
    return match[1] + ' '.join(labels) + ' ' + text


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
        body = NOTE.sub(_label_note, release['body'] or '').strip()
        # Keep release headings subordinate to the version heading in the page outline.
        body = re.sub(r'^#{1,2}(?= )', '###', body, flags=re.MULTILINE)
        sections.extend([
            f'## {title}',
            f'**{channel}** · {date} · [View on GitHub]({release["html_url"]})',
            body,
            '---',
        ])
    if not releases:
        sections.append('No releases have been published yet.')
    return '\n\n'.join(sections).removesuffix('\n\n---') + '\n'
