"""Late failure preserves published bytes and keeps tracking coherent across real surfaces."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.integration.py.test_report_save_workflow import rows
from tests.integration.py.test_report_storage import source

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def fault_library(tmp_path_factory):
    folder = tmp_path_factory.mktemp('report-publication-loader')
    library = folder / ('faults.dylib' if sys.platform == 'darwin' else 'faults.so')
    compiler = shutil.which('cc') or shutil.which('x86_64-conda-linux-gnu-cc')
    assert compiler, 'The pinned runner has a C compiler for its filesystem-failure observer'
    result = subprocess.run(
        [
            compiler,
            '-shared',
            '-fPIC',
            '-O1',
            str(ROOT / 'tests/fixtures/report_publication/faults.c'),
            '-o',
            str(library),
            *([] if sys.platform == 'darwin' else ['-ldl']),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'The test-only filesystem observer compiles without changing product code: '
        + result.stderr
    )
    return library


def fault_environment(library, directory, kind, receipt):
    environment = os.environ.copy()
    key = 'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
    environment[key] = str(library)
    environment['EDI_REPORT_FAULT_DIR'] = str(directory.resolve())
    environment['EDI_REPORT_FAULT_KIND'] = kind
    environment['EDI_REPORT_FAULT_LOG'] = str(receipt)
    return environment


def run_fault(path, surface, environment, output):
    if surface in {'core-python', 'python-save-html'}:
        args = [
            sys.executable,
            str(ROOT / 'tests/fixtures/report_publication/observe.py'),
            str(path),
            'save_html' if surface == 'python-save-html' else 'save',
            str(output),
        ]
    else:
        args = [sys.executable, '-m', 'edi', 'report', str(path)]
        if surface == 'cli-output':
            args += ['--output', str(output), '--online']
    return subprocess.run(
        args, env=environment, capture_output=True, text=True, check=False, timeout=20
    )


@pytest.mark.parametrize('surface', ['core-python', 'python-save-html', 'cli-save', 'cli-output'])
def test_write_failure_after_opening_preserves_the_previous_report_bytes(
    tmp_path, fault_library, surface
):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = edi.Project.load(path)
    project.report.save()
    output = path / 'reports' / (project.name + '.html')
    before, tracking = output.read_bytes(), rows(path)
    project.metadata.title = 'Content changed before a post-open failure'
    project.save()
    receipt = tmp_path / 'failure-receipt'
    environment = fault_environment(fault_library, output.parent, 'html', receipt)
    result = run_fault(path, surface, environment, output)
    assert receipt.exists() and 'write-after-open' in receipt.read_text(), (
        'The witness writes a real report prefix before ENOSPC; '
        + result.stdout
        + result.stderr
    )
    if surface.startswith('cli'):
        assert result.returncode != 0, 'The CLI reports an actual post-open write failure'
    else:
        assert json.loads(result.stdout)['failed'], (
            'The Python facade reports the actual write failure'
        )
    assert output.read_bytes() == before and rows(path) == tracking, (
        'A failed replacement preserves every old report byte and tracking field '
        'across core, Python and CLI'
    )


def test_settings_publication_failure_keeps_live_and_reopened_rows_consistent(
    tmp_path, fault_library
):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = edi.Project.load(path)
    project.report.save()
    settings = path / 'reports/report.edi'
    before = settings.read_bytes()
    project.metadata.title = 'A different report with the same destination name'
    project.save()
    receipt = tmp_path / 'settings-receipt'
    environment = fault_environment(fault_library, settings.parent, 'settings', receipt)
    result = run_fault(
        path, 'core-python', environment, settings.with_name(project.name + '.html')
    )
    assert receipt.exists() and 'settings-rename' in receipt.read_text(), (
        'The settings witness reaches the staged report.edi rename '
        'rather than an initial artifact refusal; ' + result.stdout + result.stderr
    )
    observed = json.loads(result.stdout)
    assert observed['failed'] and settings.read_bytes() == before, (
        'An unsuccessful settings publication is visible and preserves the previous persisted rows'
    )
    assert observed['live'] == observed['disk'], (
        'A failed report.edi publication leaves the open project and a true reload '
        'with identical report states'
    )
