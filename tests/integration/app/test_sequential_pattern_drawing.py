"""Only the current calculated curve and visible fills during a real running scan."""

import os
import signal
import subprocess
from contextlib import suppress
from pathlib import Path

import pytest
from test_table_about_and_scan_views import ROOT

CASES = {
    'observer': 'test_pixel_observer_rejects_stale_and_empty_drawing',
    'current': 'test_drawn_pattern:current',
    'fills': 'test_drawn_pattern:fills',
}


@pytest.fixture(scope='module')
def drawing_receipts(tmp_path_factory):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Sequential drawing requires the actual native application test host'
    prefix = ROOT / '.pixi/envs/app'
    environment = {
        **os.environ,
        'PATH': str(prefix / 'bin') + os.pathsep + os.environ['PATH'],
        'CONDA_PREFIX': str(prefix),
    }
    receipts = {}
    for kind, phase in CASES.items():
        directory = tmp_path_factory.mktemp('sequential-' + kind)
        command = [
            'bash',
            str(ROOT / 'tests/fixtures/sequential_drawing/run.sh'),
            str(binary.resolve()),
            '-input',
            str(ROOT / 'tests/unit/app/tst_sequential_pattern_drawing.qml'),
            '-o',
            '-,txt',
            'SequentialPatternDrawing::' + phase,
        ]
        try:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except OSError as error:
            result = subprocess.CompletedProcess(command, 127, '', str(error))
        else:
            try:
                stdout, stderr = process.communicate(timeout=50)
                result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                # The display servers and fit worker share this process group.
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                result = subprocess.CompletedProcess(
                    command, 124, stdout, stderr + '\nThe drawing actor exceeded its watchdog'
                )
        print(
            f'Sequential drawing {kind}: status={result.returncode}, images={directory}',
            flush=True,
        )
        print(result.stdout + result.stderr, flush=True)
        receipts[kind] = result
    return receipts


@pytest.mark.parametrize('kind', CASES)
def test_current_scan_pattern_is_drawn_without_stale_curve_or_missing_fill(drawing_receipts, kind):
    result = drawing_receipts[kind]
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real running scan must satisfy its drawing contract: ' + output
    )
    function, _, tag = CASES[kind].partition(':')
    expected = f'::SequentialPatternDrawing::{function}({tag})'
    assert expected in output and '0 failed' in output, (
        'The exact requested real scan case must complete, not an empty or different actor: '
        + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'Neither current-curve nor structure-fill drawing may be skipped'
    )
