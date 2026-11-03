"""Inspect names and current folders on actual native Save-as choosers."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('source', ['folder', 'zip'])
@pytest.mark.parametrize('output', ['folder', 'zip'])
@pytest.mark.parametrize('copy', ['copy', 'move'])
def test_real_save_chooser_receives_project_name_and_current_folder(source, output, copy):
    tag = source + '-' + output + '-' + copy
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Chooser-default gates require the actual app test host'
    run = subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_project_archive.qml'),
            '-o',
            '-,txt',
            'ProjectArchive::test_save_chooser_defaults:' + tag,
        ],
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    text = run.stdout + run.stderr
    assert run.returncode == 0, (
        'Every native Save-as path must hand the correct defaults to its chooser: ' + text
    )
    receipt = re.escape('ProjectArchive::test_save_chooser_defaults(' + tag + ')')
    assert (
        len(re.findall(r'^PASS\s*:\s*(?:edi_app::)?' + receipt + r'\s*$', text, re.MULTILINE)) == 1
    ), 'Each chooser-default path must produce exactly one completed passing receipt: ' + text
    assert not re.search(r'^(?:FAIL!|QFATAL|SKIP)\s*:', text, re.MULTILINE), (
        'A skipped or failed chooser path cannot qualify its name and starting folder'
    )
