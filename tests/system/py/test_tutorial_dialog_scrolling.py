"""The finite Tutorials viewport is navigated by real wheel input before the row click."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def scroll_run(tmp_path_factory, request):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Tutorial scrolling uses the actual Qt app test host'
    positions = [
        item.callspec.params['position']
        for item in request.session.items
        if item.path == request.node.path
    ]
    folder = tmp_path_factory.mktemp('tutorial-row-scrolling')
    command = [
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'),
        '-o',
        '-,txt',
        '-maxwarnings',
        '0',
        *[
            'TutorialNavigation::test_required_chooser_reaches_rows_by_scrolling:' + position
            for position in positions
        ],
    ]
    with (folder / 'native.log').open('w') as log:
        run = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=30 * len(positions),
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        )
    return run.returncode, (folder / 'native.log').read_text()


@pytest.mark.parametrize('position', ['first', 'half-row', 'last'])
def test_tutorial_row_is_scrolled_into_view_before_its_real_click(position, scroll_run):
    exit_code, output = scroll_run
    assert exit_code == 0, (
        'Real rows are scrolled into the finite viewport and clicked without changing selection '
        'or directly setting the list position: ' + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'A real scroll witness cannot be replaced by a skipped native case'
    )
    rows = [
        json.loads(line.partition('TUTORIAL_ROW_SCROLL ')[2])
        for line in output.splitlines()
        if 'TUTORIAL_ROW_SCROLL ' in line
    ]
    found = [row for row in rows if row['tag'] == position]
    assert len(found) == 1, 'The selected real-host scroll witness completes exactly once'
