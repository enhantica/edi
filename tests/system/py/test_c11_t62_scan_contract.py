""": bounded live scan, event timing, cancellation and dry-run I/O."""

import csv
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
CASE = (
    Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))
    / 'cosio-d20-scan-3f/project'
)


def _project(tmp_path, mode='sequential'):
    target = tmp_path / mode
    shutil.copytree(CASE, target)
    path = target / 'analysis/analysis.edi'
    path.write_text(
        path
        .read_text()
        .replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1')
        .replace('_fitting_mode.type sequential', f'_fitting_mode.type {mode}')
    )
    return target


def _rows(target):
    path = target / 'analysis/results.csv'
    return list(csv.DictReader(path.open())) if path.exists() else []


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_completion_event_arrives_before_the_next_files_iteration(tmp_path, mode):
    target = _project(tmp_path, mode)
    complete = []
    iteration_counts = []

    def iteration(_row):
        count = len(_rows(target))
        iteration_counts.append(count)
        assert len(complete) == count, (
            ' gate 5: each committed row must have emitted its event before '
            'the next file starts iterating; CSV polling delivers it too late'
        )

    project = edi.Project.load(target)
    result = project.analysis.fit(
        on_iteration=iteration, on_file_complete=complete.append, on_scan_start=lambda _p: None
    )
    assert len(complete) == 3 and set(iteration_counts) == {0, 1, 2}, (
        ' gate 5: real callbacks must exercise every boundary of the short scan'
    )
    report = edi.machine_report(project, result, edi.VerbosityEnum.FULL)
    retained = set(re.findall(r'^iter\.(\d+)\.', report, re.MULTILINE))
    assert len(retained) <= 2, (
        ' gate 5: retained history must be bounded by one file (one step plus polish), '
        'even when a subscriber receives every scan iteration'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('cancel', ['predicate', 'keyboard'])
def test_python_cancellation_preserves_prefix_and_resumes(tmp_path, mode, cancel):
    target = _project(tmp_path, mode)
    completed = []
    second_started = []

    def iteration(row):
        if completed:
            second_started.append(row)
            if cancel == 'keyboard':
                raise KeyboardInterrupt

    kwargs = {
        'on_iteration': iteration,
        'on_file_complete': completed.append,
        'on_scan_start': lambda _p: None,
    }
    if cancel == 'predicate':
        kwargs['should_cancel'] = lambda: bool(second_started)
    try:
        result = edi.Project.load(target).analysis.fit(**kwargs)
    except KeyboardInterrupt:
        pytest.fail(' gate 6: callback KeyboardInterrupt must become a CANCELLED result')
    assert result.status == edi.FitStatus.CANCELLED, (
        ' gate 6: Python cancellation must return CANCELLED'
    )
    assert len(completed) == len(_rows(target)) == 1, (
        ' gate 6: no row or completion event may survive for the interrupted second file'
    )
    prefix = (target / 'analysis/results.csv').read_bytes()
    resumed = []
    edi.Project.load(target).analysis.fit(on_file_complete=resumed.append)
    assert len(resumed) == 2 and len(_rows(target)) == 3, (
        ' gate 6: cancellation must leave a resumable prefix, without duplicate rows'
    )
    assert (target / 'analysis/results.csv').read_bytes().startswith(prefix), (
        ' gate 6: resume preserves previously committed results bytes'
    )


DRY_AUDIT = r"""
import json, pathlib, runpy, sys
project, logfile, mode = sys.argv[1:]
copies = []
def audit(event, args):
    if event == 'shutil.copyfile' and pathlib.Path(args[0]).suffix == '.dat':
        copies.append(str(args[0]))
sys.addaudithook(audit)
sys.argv = ['edi', 'fit', project, '--dry', '--report', 'machine', '--verbosity', 'off']
try:
    runpy.run_module('edi', run_name='__main__')
finally:
    pathlib.Path(logfile).write_text(json.dumps(copies))
"""


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_dry_run_does_not_open_scan_data_for_copying(tmp_path, mode):

    target = _project(tmp_path, mode)
    before = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
    log = tmp_path / 'copies.json'
    result = subprocess.run(
        [sys.executable, '-c', DRY_AUDIT, str(target), str(log), mode],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        env={**os.environ, 'OMP_NUM_THREADS': '1'},
    )
    assert result.returncode == 0, (
        f' gate 5: instrumented dry run must perform the real fit: {result.stderr}'
    )
    assert json.loads(log.read_text()) == [], (
        ' gate 5: --dry must read scan data in place, never open them for copying'
    )
    after = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
    assert before == after, ' gate 5: --dry must preserve every source project byte'


@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize('cancel', ['predicate', 'on_start', 'on_iteration'])
def test_direct_fit_cancellation_uses_the_same_python_contract(tmp_path, mode, cancel):
    target = _project(tmp_path, mode)
    # Before: joint cancellation ran on a declared scan. F9 now refuses that
    # boundary; retain the admitted direct-fit callback contract on a non-scan.
    if mode == 'joint':
        analysis = target / 'analysis/analysis.edi'
        analysis.write_text(analysis.read_text().split('_sequential_fit.data_dir')[0])
    visited = []

    def interrupt(row):
        visited.append(row)
        raise KeyboardInterrupt

    kwargs = {'should_cancel': lambda: True} if cancel == 'predicate' else {cancel: interrupt}
    try:
        result = edi.Project.load(target).analysis.fit(**kwargs)
    except KeyboardInterrupt:
        pytest.fail(' gate 6: every direct-fit callback must translate KeyboardInterrupt')
    assert result.status == edi.FitStatus.CANCELLED, (
        ' gate 6: single and joint Python fits must return CANCELLED'
    )
    if cancel != 'predicate':
        assert visited, ' gate 6: cancellation control must reach the selected callback'


@pytest.mark.parametrize('cancel', ['predicate', 'on_start', 'on_iteration'])
def test_declared_scan_joint_refusal_precedes_every_cancellation_callback(tmp_path, cancel):
    target = _project(tmp_path, 'joint')
    before = {
        path.relative_to(target): path.read_bytes() for path in target.rglob('*') if path.is_file()
    }
    calls = []

    def interrupt(*args):
        calls.append(args)
        return True

    kwargs = {'should_cancel': interrupt} if cancel == 'predicate' else {cancel: interrupt}
    with pytest.raises(ValueError, match='declares a scan'):
        edi.Project.load(target).analysis.fit(**kwargs)
    assert not calls, (
        'Scan admission: declared joint scans refuse before any cancellation or fit callback'
    )
    assert before == {
        path.relative_to(target): path.read_bytes() for path in target.rglob('*') if path.is_file()
    }, 'Scan admission: a refused joint scan preserves every source and result byte'


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('callback', ['on_scan_start', 'on_file_complete'])
def test_scan_boundary_keyboard_interrupt_is_also_clean(tmp_path, mode, callback):
    target = _project(tmp_path, mode)
    visited = []

    def interrupt(row):
        visited.append(row)
        raise KeyboardInterrupt

    try:
        result = edi.Project.load(target).analysis.fit(**{callback: interrupt})
    except KeyboardInterrupt:
        pytest.fail(' gate 6: scan boundary callbacks must translate KeyboardInterrupt')
    assert visited, ' gate 6: the scan-boundary cancellation probe must reach its callback'
    assert result.status == edi.FitStatus.CANCELLED, (
        ' gate 6: all scan callback boundaries share the clean cancellation contract'
    )
    expected = 1 if callback == 'on_file_complete' else 0
    assert len(_rows(target)) == expected, (
        ' gate 6: a completion interrupt retains its committed row; '
        'a scan-start interrupt commits none'
    )
    resumed = []
    edi.Project.load(target).analysis.fit(on_file_complete=resumed.append)
    assert len(resumed) == 3 - expected, ' gate 6: boundary cancellation remains resumable'


# Boundary means the first/middle/last FILE, not an arbitrary count of minimizer
# polls. on_scan_start runs once, so its positions are fresh/one-row/two-row
# resumes; the fully completed resume separately exercises the zero-fit path.
BOUNDARIES = [
    *[('on_file_complete', position) for position in (1, 2, 3)],
    *[('on_iteration', position) for position in (1, 2, 3)],
    *[('on_scan_start', prior) for prior in (0, 1, 2, 3)],
]
CANCEL_ROUTES = [
    'keyboard',
    'keyboard-subclass',
    'sigint',
    'predicate',
    'predicate-truthy',
    'predicate-keyboard',
    'predicate-bool-keyboard',
    'sigint-predicate',
]


def _model_state(project):
    return [(p.value, p.uncertainty, p.free) for p in project.parameters]


def _array_state(values):
    return values.shape, values.dtype.str, values.tobytes()


def _calculated_state(project):
    return [
        _array_state(np.asarray(experiment.data.intensity_calc))
        for experiment in project.experiments
    ]


def _model_bytes(target):
    return {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*.edi')}


def _ledger_bytes(target):
    return {
        name: (target / 'analysis' / name).read_bytes()
        for name in ('results.csv', 'results-provenance.csv')
        if (target / 'analysis' / name).exists()
    }


def _prefill(target, count):
    if count:
        complete = []
        edi.Project.load(target).analysis.fit(
            on_file_complete=complete.append,
            should_cancel=lambda: len(complete) >= count,
        )
    assert len(_rows(target)) == count, (
        ' terminal-boundary probe must establish exactly its declared real resume prefix'
    )


class _CallbackInterrupt(KeyboardInterrupt):
    pass


class _CancelAnswer:
    def __init__(self, interrupt):
        self.interrupt = interrupt

    def __bool__(self):
        if self.interrupt:
            raise KeyboardInterrupt
        return True


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('entry', ['analysis', 'native'])
@pytest.mark.parametrize('route', CANCEL_ROUTES)
@pytest.mark.parametrize(('boundary', 'position'), BOUNDARIES)
def test_every_reachable_scan_boundary_observes_cancel_before_writeback(
    tmp_path, mode, entry, route, boundary, position
):
    target = _project(tmp_path, mode)
    prior = position if boundary == 'on_scan_start' else 0
    _prefill(target, prior)
    project = edi.Project.load(target)
    before = (_model_state(project), _model_bytes(target))
    # Settle the lazy calculated baseline before scan entry. Check both the
    # buffers returned now and the live owner after every cancellation route.
    held_patterns = [
        np.asarray(experiment.data.intensity_calc) for experiment in project.experiments
    ]
    held = [(pattern, _array_state(pattern)) for pattern in held_patterns]
    completed, reached, single_preambles = [], [], []
    armed = False
    frozen_rows = {}

    def predicate():
        if not armed:
            return False
        if route == 'predicate-keyboard':
            raise KeyboardInterrupt
        if route in {'predicate-truthy', 'predicate-bool-keyboard'}:
            return _CancelAnswer(route == 'predicate-bool-keyboard')
        return True

    def signal_flag(_signum, _frame):
        nonlocal armed
        armed = True

    def request():
        nonlocal armed, frozen_rows
        if reached:
            return
        reached.append((boundary, position))
        frozen_rows = _ledger_bytes(target)
        if route in {'sigint', 'sigint-predicate'}:
            os.kill(os.getpid(), signal.SIGINT)
        elif route == 'keyboard':
            raise KeyboardInterrupt
        elif route == 'keyboard-subclass':
            raise _CallbackInterrupt
        else:
            armed = True

    def scan_start(_row):
        if boundary == 'on_scan_start':
            request()

    def complete(row):
        completed.append(row)
        if boundary == 'on_file_complete' and len(completed) == position:
            request()

    def iteration(_row):
        if boundary == 'on_iteration' and len(completed) + 1 == position:
            request()

    fit = project.analysis.fit if entry == 'analysis' else getattr(project, f'fit_{mode}')
    outcome = _call_scan_probe(
        fit,
        route,
        signal_flag,
        {
            'on_start': single_preambles.append,
            'on_scan_start': scan_start,
            'on_file_complete': complete,
            'on_iteration': iteration,
            'should_cancel': predicate,
        },
    )

    assert reached == [(boundary, position)], (
        ' each cancellation channel must actually reach its selected callback boundary'
    )
    expected_rows = (
        prior if boundary == 'on_scan_start' else position - (boundary == 'on_iteration')
    )
    assert not single_preambles, ' a scan must not emit the single-fit preamble'
    _assert_boundary_cancel(
        target,
        project,
        outcome,
        expected_rows,
        frozen_rows,
        before,
        held,
    )


def _call_scan_probe(fit, route, signal_flag, callbacks):
    previous_handler = signal.getsignal(signal.SIGINT)
    signal.signal(
        signal.SIGINT, signal_flag if route == 'sigint-predicate' else signal.default_int_handler
    )
    try:
        try:
            return fit(**callbacks)
        except KeyboardInterrupt:
            pytest.fail(' scan callbacks must return cancellation, never leak KeyboardInterrupt')
    finally:
        signal.signal(signal.SIGINT, previous_handler)


def _assert_boundary_cancel(target, project, outcome, expected_rows, frozen_rows, before, held):
    # Evaluate every consequence before the final assertion: a wrong success may
    # ALSO have published values, patterns or rows, and the diagnostic must name it.
    defects = []
    if outcome.status != edi.FitStatus.CANCELLED:
        defects.append('outcome is not CANCELLED')
    if _model_state(project) != before[0]:
        defects.append('fitted parameter/uncertainty state was written back')
    if any(pattern.tobytes() != state[2] for pattern, state in held):
        defects.append('a previously returned calculated column was mutated in place')
    if _calculated_state(project) != [state for _, state in held]:
        defects.append('live calculated state changed after cancellation')
    if _model_bytes(target) != before[1]:
        defects.append('input model files changed')
    after_rows = _ledger_bytes(target)
    if len(_rows(target)) != expected_rows or any(
        after_rows.get(name) != content for name, content in frozen_rows.items()
    ):
        defects.append('finished results/provenance rows were changed or new rows followed cancel')
    assert not defects, (
        ' all callback-boundary cancellation routes must stop before publication, '
        'including the last event and a no-op resume: ' + '; '.join(defects)
    )
    resumed = []
    edi.Project.load(target).analysis.fit(on_file_complete=resumed.append)
    assert len(resumed) == 3 - expected_rows and len(_rows(target)) == 3, (
        ' a boundary cancel must resume exactly the uncommitted files without duplicates'
    )
    for name, prefix in frozen_rows.items():
        assert (target / 'analysis' / name).read_bytes().startswith(prefix), (
            ' resume must retain every completed results and provenance row byte'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('entry', ['analysis', 'native'])
def test_scan_never_calls_the_single_fit_preamble_even_on_noop_resume(tmp_path, mode, entry):
    target = _project(tmp_path, mode)
    project = edi.Project.load(target)
    fit = project.analysis.fit if entry == 'analysis' else getattr(project, f'fit_{mode}')
    calls = []
    for _ in range(2):
        fit(on_start=calls.append)
    assert not calls and len(_rows(target)) == 3, (
        ' on_start is not a scan callback: fresh scans and no-op resumes keep it silent'
    )
