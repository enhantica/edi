"""Every authored built-in title and callout renders Markdown as visible emphasis."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']


@pytest.fixture(scope='module')
def rendered(tmp_path_factory):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Callout rendering requires the real Qt app test host'
    folder = tmp_path_factory.mktemp('callout-markup')
    command = [
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'),
        '-o',
        '-,txt',
        '-maxwarnings',
        '0',
        *[
            'TutorialNavigation::test_required_callout_manifest_markup:' + entry['id']
            for entry in MANIFEST
        ],
        'TutorialNavigation::test_required_callout_emphasis_is_rendered',
        'TutorialNavigation::test_required_callout_rendering_observer_controls',
    ]
    env = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    }
    with (folder / 'native.log').open('w') as output:
        subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=max(60, 5 * len(MANIFEST)),
            check=False,
        )
    return [
        json.loads(line.partition('TUTORIAL_MARKUP_RESULT ')[2])
        for line in (folder / 'native.log').read_text().splitlines()
        if 'TUTORIAL_MARKUP_RESULT ' in line
    ]


def result(rendered, name):
    found = [row for row in rendered if row['id'] == name]
    assert len(found) == 1, 'The actual callout renderer completes exactly one case: ' + name
    return found[0]


@pytest.mark.parametrize('name', [entry['id'] for entry in MANIFEST])
def test_every_manifest_title_and_callout_renders_emphasis_without_raw_markers(name, rendered):
    row = result(rendered, name)
    assert row['checked'] > 1, 'Every manifest includes its title and written step content'
    assert not row['errors'], (
        'No built-in title or callout shows raw markers or loses declared emphasis: '
        + name
        + ' / '
        + repr(row['errors'])
    )


def test_actual_callout_renders_bold_and_code_instead_of_stripping_them(rendered):
    assert not result(rendered, 'emphasis')['errors'], (
        'Actual emphasis matches independent Qt Markdown metrics, including marked titles'
    )


def test_real_renderer_positive_and_literal_strip_title_escape_controls(rendered):
    row = result(rendered, 'observer-controls')
    assert row['checked'] == 4 and not row['errors'], (
        'A real positive renderer passes and literal, strip-only and raw-title escapes are caught'
    )
