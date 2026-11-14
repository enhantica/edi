"""Preferences and public documentation contracts."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'app/qml'
DOCS = ROOT / 'website/surfaces/docs'
TABS = [
    'Appearance',
    'Interface',
    'Projects',
    'Performance',
    'Updates',
    'AI assistance',
    'Advanced',
]


def preferences():
    return (QML / 'Components/AppPreferencesDialog.qml').read_text()


def test_preferences_tab_order_and_removed_controls():
    source = preferences()
    tabs = re.findall(
        r'objectName: "preferences.tab.[^"]+"\s+[^{}]*?text: qsTr\("([^"]+)"\)', source
    )
    assert tabs == TABS, 'Preferences must offer the seven approved tabs in order'
    for removed in [
        'Enable user guides',
        'Feedback address',
        'preferences.zoom',
        'preferences.language',
    ]:
        assert removed not in source, (
            'Preferences must omit the removed guides, feedback, zoom and language controls'
        )
    assert re.search(r'(?:width|contentWidth):\s*720\b', source), (
        'Preferences must use the approved 720 pixel width'
    )


@pytest.mark.parametrize(
    'name', ['showFitResults', 'checkUpdateOnStart', 'autoCollapse', 'ai.copyTechnicalDetails']
)
def test_boolean_preferences_use_aligned_selectors(name):
    source = preferences()
    location = source.index('objectName: "preferences.' + name + '"')
    opening = source.rfind('{', 0, location)
    declaration = re.search(r'([A-Za-z.]+)\s*$', source[:opening])[1]
    assert 'CheckBox' not in declaration, (
        'Boolean preferences must use labelled selectors instead of checkboxes'
    )


def test_preferences_retains_working_controls():
    source = preferences()
    for name in [
        'theme',
        'colours',
        'mapColours',
        'hiddenRange',
        'momentColours',
        'toolTipLevel',
        'toolTipDelay',
        'sideBarSide',
        'textShow',
        'scanRenderer',
        'loggingLevel',
        'diagnostics',
        'resetSettings',
        'online.sources.add',
        'ai.sources.add',
        'ai.workReport',
        'ai.copyConnection',
    ]:
        assert '"preferences.' + name + '"' in source, (
            'The redesigned tabs must retain each working preference and action'
        )


def test_stacked_uses_palette_while_map_retains_its_selector():
    source = preferences()
    assert '"preferences.mapColours"' in source, (
        'Map must retain its independent colour map selector'
    )
    assert 'scanStackedPalette' not in source, (
        'Stacked must follow the single shared palette without storing a separate selection'
    )
    location = source.find('"preferences.stackedColours"')
    if location >= 0:
        end = source.find('\n            }', location)
        block = source[location:end]
        assert 'scanColourMap' not in block and 'colourMapNames' not in block, (
            'Stacked must follow the shared palette rather than offer colour maps'
        )
    for path in QML.rglob('*.qml'):
        if 'Stacked' in path.name:
            assert 'colourMapNames' not in path.read_text(), (
                'Stacked toolbars must not retain a colour map selector'
            )


def test_citation_uses_zenodo_doi_and_consistent_title():
    citation = (ROOT / 'CITATION.cff').read_text()
    assert '10.5281/zenodo.24127939' in citation, (
        'The citation must use the approved Zenodo record DOI'
    )
    source = (QML / 'Pages/Home/CitationDialog.qml').read_text()
    assert 'How to cite' in source, 'The citation dialog must retain the common How to cite title'
    assert 'external' in source.lower(), 'The DOI link must carry the external resource icon'
    assert 'InfoDialog.InfoButton {' in source and 'objectName: "citation.doi"' in source, (
        'The clickable DOI must have no underline'
    )
    for label, value in [('Copy as text', 'text'), ('Copy as BibTeX', 'bibtex')]:
        assert label in source and 'copyText(dialog.citation.' + value in source, (
            'Both citation formats must copy their corresponding citation content'
        )
    info = (QML / 'Components/InfoDialog.qml').read_text()
    assert source.count('InfoDialog.InfoButton {') == 3, (
        'DOI and both citation copy actions must use the common background-free button'
    )
    assert 'actions: [' in source and 'property alias actions: buttons.contentData' in info, (
        'Citation actions must populate the common dialog footer'
    )
    assert (
        'footer: EaElements.DialogButtonBox {' in info
        and 'standardButtons: Dialog.Close' in source
    ), 'Citation copy actions must be in the footer beside Close'
    assert re.search(r'^# How to cite$', (DOCS / 'about/citation.md').read_text(), re.MULTILINE), (
        'The website and app must use the same How to cite title'
    )


def test_cosio_example_starting_moments():
    path = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/project/structures/cosio.edi'
    source = path.read_text().split('_atom_site_moment.symmform', 1)[1]
    for site, expected in [('Co1', [2, 2, 2]), ('Co2', [0, 2, 0])]:
        row = re.search(r'^' + site + r'\s+([^\n]+)', source, re.MULTILINE)
        assert row is not None, 'The magnetic CoSiO example must contain both cobalt moments'
        actual = [float(re.sub(r'\([^)]*\)', '', v)) for v in row[1].split()[:3]]
        assert actual == expected, 'CoSiO must start with visible approved cobalt moments'


def survey():
    pages = list(DOCS.glob('about/**/survey*.md'))
    assert len(pages) == 1, 'About must contain one persistent Survey page'
    return pages[0].read_text() + '\n' + (DOCS / 'assets/survey/survey.js').read_text()


def test_survey_navigation_and_question_groups():
    source = survey().lower()
    for phrase in [
        'event',
        'general',
        'position',
        'field',
        'experience',
        'documentation',
        'tutorial',
        'missing',
        'nice',
        'email',
        'consent',
        '15',
    ]:
        assert phrase in source, (
            'Survey must contain every recorded question group and the amended duration'
        )
    for phrase in [
        'web application',
        'desktop application',
        'jupyter',
        'scripting',
        'standalone',
        'command-line tool as a python package',
    ]:
        assert phrase in source, 'Survey must distinguish all six interfaces'
    for phrase in ['fullprof', 'gsas-ii', 'topas', 'jana', 'none', 'other']:
        assert phrase in source, 'Survey tools must contain all recorded choices'
    nav = ROOT / 'website/mkdocs.yml'
    candidates = (
        [nav]
        if nav.exists()
        else list((ROOT / 'website').glob('**/mkdocs*.yml')) + [ROOT / 'website/build.py']
    )
    assert any(re.search(r'Get in touch[\s\S]*Survey', p.read_text()) for p in candidates), (
        'Navigation must place Survey below Get in touch'
    )
    community = (DOCS / 'about/community.md').read_text()
    assert re.search(r'\[[^]]*[Ss]urvey[^]]*\]\([^)]*survey', community), (
        'Get in touch must link readers to the persistent survey'
    )


def test_survey_ai_questions_are_separate():
    source = survey().lower()
    for phrase in [
        'not interested',
        'built-in assistant',
        'chatgpt',
        'claude',
        'github copilot',
        'gemini',
        'local',
        'institution',
        'api key',
        'subscription',
        'free',
        'measured data',
        'not sure',
    ]:
        assert phrase in source, (
            'The AI section must offer the recorded interest, use, providers, '
            'access and data questions'
        )


def test_online_sources_documented_collection_passes_real_checker():
    pages = [p for p in DOCS.rglob('*.md') if 'edi-data-index/1' in p.read_text()]
    assert pages, 'The user documentation must explain the online collection schema'
    examples = []
    for page in pages:
        examples.extend(
            (page, block)
            for block in re.findall(r'```json\s*\n(.*?)```', page.read_text(), re.DOTALL)
            if 'edi-data-index/1' in block
        )
    assert examples, 'The online sources page must provide a complete JSON index example'
    page, block = examples[0]
    document = json.loads(block)
    assert {entry['kind'] for entry in document['entries']} >= {
        'structure',
        'experiment',
        'project',
    }, 'The documented example must include structure, experiment and project entries'
    files = [p for p in DOCS.rglob('index.json') if json.loads(p.read_text()) == document]
    assert files, (
        'The documented collection must ship its named files and index for readers to try'
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/data/build_collection.py'),
            'check',
            str(files[0].parent),
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        'The documented collection example must pass the actual collection checker: '
        + result.stderr
    )


@pytest.mark.parametrize(
    'instant',
    [
        '2030-05-09T23:59:59Z',
        '2030-05-10T00:00:00Z',
        '2030-05-11T12:00:00Z',
        '2030-05-12T23:59:59Z',
        '2030-05-13T00:00:00Z',
    ],
)
def test_survey_event_windows_in_browser(instant):
    survey()
    files = list(DOCS.rglob('*events*.json'))
    assert len(files) == 1, 'Survey events must be declared in one file'
    pages = list(DOCS.glob('about/**/survey*.md'))
    result = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/survey/events.mjs'),
            str(DOCS),
            str(pages[0].relative_to(DOCS)),
            str(files[0]),
            instant,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'The real survey combobox must enforce active event dates: ' + result.stderr
    )
