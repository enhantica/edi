# SPDX-License-Identifier: BSD-3-Clause
"""Round-trip interface labels from a merged PR through GitHub and the docs."""

import datetime
import importlib.util
from pathlib import Path

import pytest


def load(path):
    source = Path(__file__).resolve().parents[3] / path
    spec = importlib.util.spec_from_file_location(source.stem, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load('tools/release/plan.py')
DOCS = load('website/render_release_notes.py')
COMMIT = 'a' * 40


def plan_with_labels(*labels):
    request = {
        'number': 3,
        'title': 'Improve plot zoom',
        'merged_at': '2026-11-04T12:00:00Z',
        'merge_commit_sha': COMMIT,
        'labels': ['[scope] bug', *labels],
    }
    return PLAN.release_plan(
        [request],
        [],
        COMMIT,
        {COMMIT},
        datetime.date(2026, 11, 5),
    )


def test_interface_labels_render_once():
    release = plan_with_labels('[interface] web', '[interface] desktop')
    assert release['notes']['Fixed'][0]['interfaces'] == ['desktop', 'web']
    github = PLAN.markdown_notes(release)
    assert 'Improve plot zoom' in github
    assert github.rstrip().endswith('`Desktop app` `Web app` <!-- interfaces: desktop,web -->')
    published = {
        'draft': False,
        'prerelease': True,
        'name': 'edi 2026.11.0',
        'published_at': '2026-11-05T12:00:00Z',
        'html_url': 'https://github.com/enhantica/edi/releases/tag/v2026.11.0',
        'body': github,
    }
    page = DOCS.render([[published, {**published, 'draft': True, 'name': 'Private draft'}]])
    assert page.count('.ed-release-interface') == 2
    assert ':lucide-monitor: Desktop app' in page
    assert ':lucide-globe: Web app' in page
    assert '`Desktop app`' not in page
    assert 'Private draft' not in page
    assert page.index('Improve plot zoom') < page.index(':lucide-monitor: Desktop app')


def test_notes_without_interfaces_keep_their_existing_text():
    assert PLAN.markdown_note({'title': 'Improve plot zoom'}) == '- Improve plot zoom'


def test_unknown_interface_fails_instead_of_losing_the_label():
    with pytest.raises(ValueError, match='unique known identifiers'):
        PLAN.markdown_note({'title': 'Improve plot zoom', 'interfaces': ['unknown']})


def test_new_notes_require_at_least_one_interface():
    with pytest.raises(ValueError, match='at least one release interface label'):
        plan_with_labels()


def test_one_note_can_affect_every_interface():
    interfaces = list(PLAN.INTERFACES)
    release = plan_with_labels(*(f'[interface] {key}' for key in reversed(interfaces)))
    assert release['notes']['Fixed'][0]['interfaces'] == interfaces
