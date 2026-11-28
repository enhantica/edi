"""Release presentation from literal publication examples and GitHub label metadata."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load('presentation_plan', 'tools/release/plan.py')
DOCS = load('presentation_docs', 'website/render_release_notes.py')
URL = 'https://github.com/enhantica/edi/releases/tag/v2026.11.14'
# Public GitHub label descriptions, read from the repository labels API.
# https://api.github.com/repos/enhantica/edi/labels?per_page=100
LABELS = [
    ('desktop', 'fa5-desktop', 'desktop', 'Affects the EasyDiffraction desktop app'),
    ('web', 'fa5-globe', 'web', 'Affects the EasyDiffraction web app'),
    ('python', 'simple-python', 'py', 'Affects the Python API in scripts or notebooks'),
    ('cli-python', 'simple-python', 'cli-py', 'Affects the CLI installed from the Python package'),
    ('cli-standalone', 'fa5-terminal', 'cli', 'Affects the standalone CLI executable'),
]


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize(
    ('version', 'date', 'expected'),
    [
        ('2026.11.14', '2026-11-13', 'v2026.11.14 · 13 Nov 2026'),
        ('2026.12.4', '2027-01-03', 'v2026.12.4 · 3 Jan 2027'),
        ('2028.02.9', '2028-02-29', 'v2028.02.9 · 29 Feb 2028'),
        ('2027.12.0', '2027-12-31', 'v2027.12.0 · 31 Dec 2027'),
    ],
)
def test_release_title_shows_the_tag_and_full_date(version, date, expected, preview):
    title = expected + (' preview' if preview else '')
    assert PLAN.release_title(version, date, preview=preview) == title, (
        'Titles use the v-tag, middle dot, full date with an unpadded day, and preview marker'
    )


def release(*, body, preview=False):
    return {
        'draft': False,
        'prerelease': preview,
        'tag_name': 'v2026.11.14',
        'name': 'An old Stable title',
        'published_at': '2027-01-03T23:45:00Z',
        'html_url': URL,
        'body': body,
    }


def test_generated_notes_start_at_the_first_change_section_without_an_inner_title():
    notes = PLAN.markdown_notes({
        'version': '2026.11.14',
        'notes': {
            'Added': [],
            'Fixed': [{'title': 'Keep zoom during reload'}],
            'Changed': [{'title': 'Show parameter names clearly'}],
        },
    })
    assert notes == (
        '## Fixed\n\n- Keep zoom during reload\n\n## Changed\n\n- Show parameter names clearly\n'
    ), 'Notes preserve nonempty change sections and items without an inner release title'


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('recorded', [False, True])
def test_whats_new_links_the_release_title_directly_to_its_change_sections(preview, recorded):
    body = '# EasyDiffraction 2026.11.14\n\n## Fixed\n\n- Keep zoom\n'
    if recorded:
        body += '\n<!-- edi release date 2026-11-13 -->\n'
    current = release(body=body, preview=preview)
    page = DOCS.render([[current, {**current, 'draft': True, 'name': 'Private draft'}]])
    title = 'v2026.11.14 · 13 Nov 2026' if recorded else 'v2026.11.14 · 3 Jan 2027'
    title += ' preview' if preview else ''
    heading = f'## [{title}]({URL})'
    assert [line for line in page.splitlines() if line.startswith('## ')] == [heading], (
        'The linked release heading shows the full recorded date or the publication date'
    )
    assert page.partition(heading + '\n')[2].lstrip('\n').startswith('**Fixed**\n\n- Keep zoom'), (
        'Change sections directly follow release headings, without extra channel/date/link lines'
    )
    assert (
        '# EasyDiffraction' not in page and 'Stable' not in page and 'Private draft' not in page
    ), 'Inner version headings, channel titles and unpublished drafts stay out of published notes'


def test_interface_pills_and_legend_use_short_labels_and_the_public_label_descriptions():
    body = PLAN.markdown_notes({
        'version': '2026.11.14',
        'notes': {
            'Fixed': [{'title': 'Keep controls consistent', 'interfaces': [r[0] for r in LABELS]}]
        },
    })
    page = DOCS.render([[release(body=body)]])
    legend, _, notes = page.partition('\n## [')
    # Emphasis is styling; the icon, short label and description carry the contract.
    legend, notes, plain = (text.replace('**', '') for text in (legend, notes, page))
    for _, icon, short, description in LABELS:
        pill = f':{icon}: {short}{{ .ed-release-interface }}'
        assert '- ' + pill + ' ' + description in legend, (
            'Short interface pills use independently recorded GitHub label descriptions'
        )
        assert notes.count(pill) == 1 and plain.count(pill) == 2, (
            'Every affected interface appears once beside the change and once in the legend'
        )
    assert '[interface]' not in page and '`desktop`' not in notes, (
        'User-facing interface pills replace process prefixes and raw source-label markup'
    )
