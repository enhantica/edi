"""Open a real web download through native controls without destroying active handlers."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('route', ['open', 'recent'])
@pytest.mark.parametrize('state', ['empty', 'replace'])
def test_web_zip_opens_from_real_controls_without_destroying_a_signal_handler(route, state):
    fixture = ROOT / 'tests/fixtures/project_archive/browser-saved-project.zip'
    manifest = json.loads(fixture.with_suffix('.json').read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == manifest['sha256'], (
        'The desktop opening witness must retain the actual frozen web download bytes'
    )
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Desktop ZIP reopening requires the actual app test host'
    identity = 'test_web_zip_lifecycle:' + route + '-' + state
    run = subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_project_archive.qml'),
            '-o',
            '-,txt',
            'ProjectArchive::' + identity,
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        'Opening or reopening the web ZIP through real controls must not abort: ' + output
    )
    assert not re.search(
        r'Object destroyed while.*(?:QML|signal)|signal handlers? (?:is|are) in progress|'
        r'use QObject::deleteLater|QFATAL|SIGABRT|Aborted|ASSERT failure',
        output,
        re.IGNORECASE | re.DOTALL,
    ), 'ZIP opening must not emit Qt active-signal-handler destruction diagnostics: ' + output
    completed = re.escape('ProjectArchive::test_web_zip_lifecycle(' + route + '-' + state + ')')
    assert (
        len(re.findall(r'^PASS\s*:\s*(?:edi_app::)?' + completed + r'\s*$', output, re.MULTILINE))
        == 1
    ), 'Each actual Open or Recent route must finish with exactly one passing receipt: ' + output
    assert not re.search(r'^(?:FAIL!|SKIP)\s*:', output, re.MULTILINE), (
        'An incomplete desktop ZIP route cannot count as a crash-free opening'
    )
