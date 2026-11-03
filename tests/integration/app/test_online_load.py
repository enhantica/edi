"""Check the real Qt menus and online search dialog."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('case', 'tag'),
    [
        ('new_experiment_wavelength', ''),
        ('actions_and_formats', 'structure'),
        ('actions_and_formats', 'experiment'),
        ('from_web_opens_source_selector', 'structure'),
        ('from_web_opens_source_selector', 'experiment'),
        ('from_web_opens_source_selector', 'measured'),
    ],
)
def test_online_load_controls(case, tag):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Online load controls require the production Qt test host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_online_load.qml'),
            '-o',
            '-,txt',
            f'OnlineLoad::test_{case}' + (f':{tag}' if tag else ''),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real online load controls must meet the UI contract: ' + output
    )
    assert f'::OnlineLoad::test_{case}({tag})' in output and '0 skipped' in output, (
        'The selected production UI case must execute without skipping: ' + output
    )
