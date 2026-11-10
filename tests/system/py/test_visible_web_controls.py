"""Web-load overflow and tutorial placement observed on real production controls."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.tutorial_recipe.long_collection import build

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def observed(tmp_path_factory):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Visible web-control gates require the actual Qt test host'
    folder = tmp_path_factory.mktemp('visible-web-controls')
    collection = build(folder / 'collection')
    command = [
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_visible_web_controls.qml'),
        '-o',
        '-,txt',
        '-maxwarnings',
        '0',
    ]
    with (folder / 'native.log').open('w') as output:
        subprocess.run(
            command,
            cwd=ROOT,
            env={
                **os.environ,
                'QT_QPA_PLATFORM': 'offscreen',
                'QT_QUICK_BACKEND': 'software',
                'EDI_ONLINE_SOURCES': 'easydiffraction=' + collection.as_uri(),
                'QT_QUICK_CONTROLS_HOVER_ENABLED': '1',
                'OMP_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1',
            },
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    text = (folder / 'native.log').read_text()
    return text, [
        json.loads(line.partition('VISIBLE_WEB_RESULT ')[2])
        for line in text.splitlines()
        if 'VISIBLE_WEB_RESULT ' in line
    ]


@pytest.mark.parametrize('kind', ['structure', 'data'])
@pytest.mark.parametrize('property_name', ['elision', 'placement'])
def test_visible_web_cells_and_target_row_contract(kind, property_name, observed):
    text, records = observed
    found = [row for row in records if row['id'] == property_name + '-' + kind]
    assert len(found) == 1, (
        'Each production dialog completes its actual overflow or callout observation: '
        + property_name
        + '-'
        + kind
        + ' / '
        + '\n'.join(line for line in text.splitlines() if line.startswith(('FAIL!', '   Loc:')))
    )
    assert not found[0]['errors'], (
        'Overflow uses an ellipsis with full tooltips; the callout does not cover its target: '
        + repr(found[0])
    )
