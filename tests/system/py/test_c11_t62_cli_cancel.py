""": real SIGINT delivered at a deterministic live callback boundary."""

import csv
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CASE = (
    Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))
    / 'cosio-d20-scan-3f/project'
)

SIGNALLED_CLI = r"""
import os, runpy, signal, sys
import edi
project, report, second = sys.argv[1:]
real = edi.Analysis.fit
def fit(self, **kwargs):
    completed = []
    sent = []
    original_iteration = kwargs.get('on_iteration')
    original_complete = kwargs.get('on_file_complete')
    def complete(row):
        completed.append(row)
        if original_complete: original_complete(row)
    def iteration(row):
        if original_iteration: original_iteration(row)
        if completed and not sent:
            sent.append(True)
            os.kill(os.getpid(), signal.SIGINT)
            if second == 'yes': os.kill(os.getpid(), signal.SIGINT)
    kwargs.setdefault('on_scan_start', lambda _p: None)
    kwargs.update(on_iteration=iteration, on_file_complete=complete)
    return real(self, **kwargs)
edi.Analysis.fit = fit
sys.argv = ['edi', 'fit', project, '--report', report, '--verbosity', 'compact']
runpy.run_module('edi', run_name='__main__')
"""


@pytest.mark.parametrize('report', ['human', 'machine'])
@pytest.mark.parametrize('second', ['no', 'yes'])
def test_sigint_cancels_live_cli_and_second_signal_exits(tmp_path, report, second):
    target = tmp_path / 'scan'
    shutil.copytree(CASE, target)
    analysis = target / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
        )
    )
    env = {**os.environ, 'OMP_NUM_THREADS': '1'}
    result = subprocess.run(
        [sys.executable, '-c', SIGNALLED_CLI, str(target), report, second],
        text=True,
        check=False,
        capture_output=True,
        timeout=5,
        env=env,
    )
    if second == 'yes':
        assert result.returncode in {130, -signal.SIGINT}, (
            ' gate 6: the second SIGINT must exit hard, without waiting for fit completion'
        )
    else:
        assert result.returncode == 130, ' gate 6: first SIGINT must produce CLI exit 130'
        assert 'Traceback' not in result.stdout + result.stderr, (
            ' gate 6: first SIGINT is clean cancellation, not a Python traceback'
        )
        if report == 'machine':
            assert 'status=cancelled' in result.stdout, (
                ' gate 6: machine output must identify cancellation'
            )
        else:
            assert 'resume' in (result.stdout + result.stderr).lower(), (
                ' gate 6: human cancellation must explain how to resume'
            )
    csv_path = target / 'analysis/results.csv'
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1, ' gate 6: interrupted second file must not commit a results row'
    prefix = csv_path.read_bytes()
    resumed = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(target),
            '--report',
            'machine',
            '--verbosity',
            'off',
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert resumed.returncode == 0, ' gate 6: ordinary CLI rerun must resume after cancellation'
    assert len(list(csv.DictReader(csv_path.open()))) == 3 and csv_path.read_bytes().startswith(
        prefix
    ), ' gate 6: CLI resume must append only missing files and retain its committed prefix'


BOUNDARY_CLI = r"""
import csv, json, os, pathlib, runpy, signal, sys
import edi
project, report, boundary, position, witness = sys.argv[1:]
position = int(position)
real = edi.Analysis.fit
seen = []
def fit(self, **kwargs):
    completed = []
    def wrap(name):
        original = kwargs.get(name)
        def callback(row):
            if original: original(row)
            if name == 'on_file_complete': completed.append(row)
            selected = (name == boundary and (
                name == 'on_scan_start'
                or name == 'on_file_complete' and len(completed) == position
                or name == 'on_iteration' and len(completed) + 1 == position))
            if selected and not seen:
                seen.append([name, position])
                root = pathlib.Path(project)
                rows = {name: (root / 'analysis' / name).read_text()
                        for name in ('results.csv', 'results-provenance.csv')
                        if (root / 'analysis' / name).exists()}
                pathlib.Path(witness).write_text(json.dumps({'seen': seen, 'rows': rows}))
                os.kill(os.getpid(), signal.SIGINT)
        return callback
    # Observer-only timing seams. Keep each real human renderer; machine output
    # subscribes to no scan events, so attach the same engine-boundary observer.
    for name in ('on_scan_start', 'on_file_complete', 'on_iteration'):
        kwargs[name] = wrap(name)
    return real(self, **kwargs)
edi.Analysis.fit = fit
sys.argv = ['edi', 'fit', project, '--report', report, '--verbosity', 'full']
runpy.run_module('edi', run_name='__main__')
"""


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('report', ['human', 'machine'])
@pytest.mark.parametrize(
    ('boundary', 'position'),
    [
        *[('on_file_complete', position) for position in (1, 2, 3)],
        *[('on_iteration', position) for position in (1, 2, 3)],
        *[('on_scan_start', prior) for prior in (0, 1, 2, 3)],
    ],
)
def test_cli_sigint_at_every_scan_boundary_preserves_model_and_finished_rows(
    tmp_path, mode, report, boundary, position
):
    target = tmp_path / 'scan'
    shutil.copytree(CASE, target)
    analysis = target / 'analysis/analysis.edi'
    analysis.write_text(
        analysis
        .read_text()
        .replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1')
        .replace('_fitting_mode.type sequential', f'_fitting_mode.type {mode}')
    )
    prior = position if boundary == 'on_scan_start' else 0
    if prior:
        completed = []
        edi.Project.load(target).analysis.fit(
            on_file_complete=completed.append, should_cancel=lambda: len(completed) >= prior
        )
    before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*.edi')}
    witness = tmp_path / 'boundary.json'
    env = {**os.environ, 'OMP_NUM_THREADS': '1'}
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            BOUNDARY_CLI,
            str(target),
            report,
            boundary,
            str(position),
            str(witness),
        ],
        text=True,
        check=False,
        capture_output=True,
        timeout=5,
        env=env,
    )
    assert witness.exists(), (
        ' CLI SIGINT probe must reach its real scan callback before claiming cancellation'
    )
    witnessed = json.loads(witness.read_text())
    assert witnessed['seen'] == [[boundary, position]], (
        ' CLI interruption must occur at the selected first/middle/last or no-op boundary'
    )
    expected_rows = (
        prior if boundary == 'on_scan_start' else position - (boundary == 'on_iteration')
    )
    csv_path = target / 'analysis/results.csv'
    rows = list(csv.DictReader(csv_path.open())) if csv_path.exists() else []
    defects = []
    if result.returncode != 130:
        defects.append(f'exit {result.returncode}, expected 130')
    if 'Traceback' in result.stdout + result.stderr:
        defects.append('unclean KeyboardInterrupt traceback')
    if report == 'machine' and 'status=cancelled' not in result.stdout:
        defects.append('machine result did not report cancelled')
    if 'resume' not in (result.stdout + result.stderr).lower():
        defects.append('missing resume guidance')
    if {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*.edi')} != before:
        defects.append('fitted model was saved despite cancellation')
    if len(rows) != expected_rows:
        defects.append('wrong number of finished rows retained')
    for name, content in witnessed['rows'].items():
        if (target / 'analysis' / name).read_text() != content:
            defects.append('finished results/provenance rows changed after cancel')
    assert not defects, (
        ' SIGINT at every CLI scan boundary must cancel before write-back: ' + '; '.join(defects)
    )
    resumed = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(target),
            '--report',
            'machine',
            '--verbosity',
            'off',
        ],
        text=True,
        check=False,
        capture_output=True,
        timeout=5,
        env=env,
    )
    assert resumed.returncode == 0 and len(list(csv.DictReader(csv_path.open()))) == 3, (
        ' every CLI boundary cancellation must leave a valid, nonduplicating resume point'
    )
    for name, content in witnessed['rows'].items():
        assert (target / 'analysis' / name).read_text().startswith(content), (
            ' a resumed CLI must preserve the exact already-finished ledger prefix'
        )
