#  adaptation: before the summary named failed files; after it retains exact
# counts/chi-square/time but omits names. Progress, ETA, resume and TTY assertions stay.
"""gates for truthful, deterministic sequential-fit progress."""

from __future__ import annotations

import ast
import csv
import io
import math
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import edi
import edi.__main__ as cli

from tests.fixtures.cli_performance.table_assertions import cells, table_rows, terminal_lines

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = Path(
    os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
)
CASE = CORPUS_ROOT / 'cosio-d20-scan-3f'


class _Capture(io.StringIO):
    """A text sink with an explicit terminal capability."""

    def __init__(self, *, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class _Clock:
    """Deterministic callable clock; exhaustion exposes accidental extra reads."""

    def __init__(self, *values: float) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def _terminal_visible_lines(stream: str) -> list[str]:
    return terminal_lines(stream)


def _scan_events() -> tuple[SimpleNamespace, list[SimpleNamespace]]:
    preamble = SimpleNamespace(total_files=3)
    completions = [
        SimpleNamespace(file_name='cosio_213K.dat', converged=True, reduced_chi_square=3.91),
        SimpleNamespace(file_name='cosio_287K.dat', converged=False, reduced_chi_square=8.44),
        SimpleNamespace(file_name='cosio_301K.dat', converged=True, reduced_chi_square=4.81),
    ]
    return preamble, completions


class _FakeAnalysis:
    fitting_mode = 'sequential'

    def __init__(self) -> None:
        self.iteration_subscribers: list[bool] = []

    def fit(
        self,
        *,
        on_iteration: Any = None,
        on_start: Any = None,
        on_scan_start: Any = None,
        on_file_complete: Any = None,
    ) -> SimpleNamespace:
        del on_start
        assert on_scan_start is not None, (
            ' scan reporting requires an explicit whole-scan preamble callback'
        )
        assert on_file_complete is not None, (
            ' scan reporting requires an explicit per-file completion callback'
        )
        preamble, completions = _scan_events()
        on_scan_start(preamble)
        for index, completion in enumerate(completions, start=1):
            self.iteration_subscribers.append(on_iteration is not None)
            if on_iteration is not None:
                on_iteration(
                    SimpleNamespace(
                        iteration=index,
                        reduced_chi_square=completion.reduced_chi_square,
                    )
                )
            on_file_complete(completion)
        return SimpleNamespace()


class _FakeProject:
    _scan_declared = True
    fitting_mode = 'sequential'

    def __init__(self) -> None:
        self.analysis = _FakeAnalysis()


def _run_fake_human(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verbosity: Any,
    tty: bool,
) -> tuple[str, _FakeProject]:
    project = _FakeProject()
    monkeypatch.setattr(cli.edi._edi, '_metric_variant', lambda _project: 'powder')
    output = _Capture(tty=tty)
    monkeypatch.setattr(cli.sys, 'stdout', output)
    # Start plus one reading after each declared completion. There is no wall-clock tolerance:
    # these are the only values from which elapsed and ETA may be rendered.
    clock = _Clock(0.0, 61.0, 161.0, 300.0)
    assert cli._run_human(project, verbosity, 'scan-demo', clock=clock) == 0, (
        ' injected-clock scan reporting must complete successfully'
    )
    return output.getvalue(), project


def _copy_unfitted_project(tmp_path: Path) -> tuple[Path, list[str]]:
    project_dir = tmp_path / 'scan'
    shutil.copytree(CASE / 'project', project_dir)
    analysis = project_dir / 'analysis' / 'analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 1000' in text, (
        ' live-event fixture requires the corpus iteration declaration'
    )
    analysis.write_text(
        text.replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'),
        encoding='utf-8',
    )
    results = project_dir / 'analysis' / 'results.csv'
    if results.exists():
        results.unlink()
    data_files = sorted(
        path.name for path in (project_dir / 'experiments' / 'd20_scan').glob('*.dat')
    )
    assert data_files, ' live-event fixture requires declared scan data files'
    return project_dir, data_files


def _seed_resume_rows(
    project_dir: Path,
    *,
    completed: int,
    failed_index: int,
) -> list[dict[str, str]]:
    reference = CASE / 'diffraction-lib' / 'project' / 'analysis' / 'results.csv'
    with reference.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames is not None, (
            ' resume fixture requires the scan writer reference header'
        )
        fieldnames = list(reader.fieldnames)
        rows = [dict(row) for row in reversed(list(reader))]
    assert len(rows) == 3 and 0 <= failed_index < completed <= len(rows), (
        ' resume fixture requires three ordered writer rows and one prior failure'
    )
    seeded = rows[:completed]
    seeded[failed_index]['fit_result.success'] = 'False'
    with (project_dir / 'analysis' / 'results.csv').open(
        'w', newline='', encoding='utf-8'
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(seeded)
    return seeded


def _read_result_rows(project_dir: Path) -> list[dict[str, str]]:
    with (project_dir / 'analysis' / 'results.csv').open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def _assert_failure_count_without_file_list(lines, rows):
    failures = sum(row['fit_result.success'].lower() != 'true' for row in rows)
    final = cells(table_rows('\n'.join(lines))[-1])
    assert (final['ok'], final['failed']) == (str(len(rows) - failures), str(failures)), (
        'The final table row retains complete successful and failed counts, including resumed rows'
    )
    assert not any(line.startswith(('failed ·', 'scan ·')) for line in lines), (
        'The final table replaces the separate summary and failed-file list'
    )


def test_native_scan_declares_total_and_one_completion_per_input_file(tmp_path: Path) -> None:
    project_dir, data_files = _copy_unfitted_project(tmp_path)
    starts: list[object] = []
    completions: list[object] = []
    project = edi.Project.load(project_dir)

    project.analysis.fit(on_scan_start=starts.append, on_file_complete=completions.append)

    assert len(starts) == 1, ' requires exactly one whole-scan preamble event'
    assert starts[0].total_files == len(data_files), (
        ' preamble N must come from the scan input set, not iteration-number restarts'
    )
    assert len(completions) == len(data_files), (
        ' requires exactly one completion event for every declared scan file'
    )
    with (project_dir / 'analysis' / 'results.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(data_files), (
        ' event comparison requires one scan-owned result row per declared input file'
    )
    for event, row in zip(completions, rows, strict=True):
        assert Path(event.file_name).name == Path(row['file_path']).name, (
            " completion file identity must be the scan writer's own result identity"
        )
        assert event.converged is (row['fit_result.success'].lower() == 'true'), (
            " completion success must be the scan writer's own outcome"
        )
        assert math.isclose(
            float(format(event.reduced_chi_square, '.2g')),
            float(row['fit_result.reduced_chi_square']),
            rel_tol=0.0,
            abs_tol=1e-12,
        ), " completion chi-square must be the scan writer's own value"


def test_core_renderers_use_declared_counts_and_injected_elapsed_values() -> None:
    required = {'ScanPreamble', 'ScanFileRecord', 'scan_progress_line', 'scan_summary'}
    assert required <= set(edi.__all__), (
        ' core scan events and renderers must be public and surface-bookkept'
    )

    line = edi.scan_progress_line(
        completed=3,
        total_files=7,
        elapsed_seconds=159.0,
        measured_completed=3,
        ok_count=2,
        fail_count=1,
        file_name='cosio_213K',
        reduced_chi_square=4.81,
    )
    assert line == (
        '[██████░░░░░░░░] · 3/7 · 43% · elapsed 2m39s · eta 3m32s · '
        '2 ok · 1 fail · cosio_213K · reduced χ² 4.81'
    ), ' progress content must use the house groups and mean-elapsed ETA formula'

    summary = edi.scan_summary(
        total_files=3,
        ok_count=2,
        fail_count=1,
        chi2_min=3.91,
        chi2_max=8.44,
        elapsed_seconds=892.0,
        measured_completed=3,
    )
    assert summary == (
        'scan · 3 files · 2 converged · 1 failed · reduced χ² 3.91-8.44 · 14m52s\n'
    ), ' failed scan summary must retain counts and omit the failed-file list'


def test_unknown_total_never_fabricates_percentage_or_eta() -> None:
    line = edi.scan_progress_line(
        completed=4,
        total_files=None,
        elapsed_seconds=31.0,
        measured_completed=4,
        ok_count=3,
        fail_count=1,
        file_name='cosio_213K',
        reduced_chi_square=4.81,
    )
    assert '4' in line and 'cosio_213K' in line, (
        ' unknown-N progress must retain the observed count and current file'
    )
    assert '%' not in line and 'eta' not in line.lower(), (
        ' unknown-N progress must not guess a percentage or ETA'
    )


def test_non_tty_emits_one_line_per_file_without_carriage_returns(monkeypatch) -> None:
    output, _ = _run_fake_human(monkeypatch, verbosity=edi.VerbosityEnum.COMPACT, tty=False)
    assert '\r' not in output, 'Piped progress has no carriage returns'
    progress = table_rows(output)
    assert len(progress) == 3, 'Piped progress retains one complete row per completed file'
    first, second, final = [cells(row) for row in progress]
    assert (first['count'], first['percent']) == ('1/3', '33.3%'), (
        'The progress group retains the actual total and first completion fraction'
    )
    assert (first['elapsed'], first['left']) == ('1m01s', '2m02s'), (
        'The injected clock still determines elapsed and current-run ETA exactly'
    )
    assert (second['ok'], second['failed']) == ('1', '1'), (
        'The failure column updates as soon as its file completes'
    )
    assert final == {
        'bar': '██████████',
        'percent': '100.0%',
        'count': '3/3',
        'ok': '2',
        'failed': '1',
        'elapsed': '5m00s',
        'left': '',
        'chi2': '4.81',
        'range': '3.91-8.44',
        'file': 'cosio_301K',
    }, 'The final row replaces the old summary while retaining every independent final fact'
    assert not any(line.startswith('scan ·') for line in output.splitlines()), (
        'No duplicate summary follows the complete final row'
    )


def test_partial_resume_uses_current_run_eta_and_counts_prior_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_dir, _ = _copy_unfitted_project(tmp_path)
    _seed_resume_rows(project_dir, completed=1, failed_index=0)
    output = _Capture(tty=False)
    monkeypatch.setattr(cli.sys, 'stdout', output)

    project = edi.Project.load(project_dir)
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.COMPACT,
            'partial-resume',
            clock=_Clock(0.0, 60.0, 120.0),
        )
        == 0
    ), ' partial resume with a prior failure must complete'

    rows = _read_result_rows(project_dir)
    lines = output.getvalue().splitlines()
    progress = table_rows('\n'.join(lines))
    assert len(progress) == 2 and '2/3' in progress[0], (
        ' partial resume must emit only the two newly completed files while retaining N'
    )
    assert (cells(progress[0])['elapsed'], cells(progress[0])['left']) == ('1m00s', '1m00s'), (
        ' resume ETA must divide this run elapsed by this run completions, not by the '
        'historical-plus-current completed count'
    )
    assert 'Elapsed' in output.getvalue() and 'Elapsed (this run)' not in output.getvalue(), (
        'The Elapsed heading remains unchanged while its clock still measures only this invocation'
    )
    _assert_failure_count_without_file_list(lines, rows)


def test_completed_noop_resume_reports_all_committed_facts_without_fake_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_dir, _ = _copy_unfitted_project(tmp_path)
    seeded = _seed_resume_rows(project_dir, completed=3, failed_index=1)
    output = _Capture(tty=False)
    monkeypatch.setattr(cli.sys, 'stdout', output)

    project = edi.Project.load(project_dir)
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.COMPACT,
            'completed-resume',
            clock=_Clock(0.0, 1.0, 2.0, 3.0),
        )
        == 0
    ), 'A second CLI Fit runs the completed scan again'

    lines = output.getvalue().splitlines()
    progress = table_rows('\n'.join(lines))
    fresh = _read_result_rows(project_dir)
    assert [row['file_path'] for row in fresh] == [row['file_path'] for row in seeded], (
        'The second pass emits a fresh generation for every dataset identity'
    )
    assert len(progress) >= len(fresh), (
        'The second pass displays progress for every actual completion'
    )
    _assert_failure_count_without_file_list(lines, fresh)
    final = cells(progress[-1])
    assert final['count'] == '3/3' and final['percent'] == '100.0%' and not final['left'], (
        'The new generation reaches its exact count with no remaining-time estimate'
    )
    assert final['elapsed'] == '3s', (
        'The final progress row uses the controlled current-invocation clock'
    )
    values = [float(row['fit_result.reduced_chi_square']) for row in fresh]
    assert final['range'] == f'{min(values):.2f}-{max(values):.2f}', (
        'The final progress range describes the newly produced rows only'
    )
    assert final['file'] == Path(fresh[-1]['file_path']).stem, (
        'The final progress row names the new pass terminal file'
    )
    assert final['chi2'] == f'{values[-1]:.2f}', (
        'The final progress row uses the newly produced terminal metric'
    )


def test_tty_updates_in_place_then_freezes_before_summary(monkeypatch) -> None:
    output, _ = _run_fake_human(monkeypatch, verbosity=edi.VerbosityEnum.COMPACT, tty=True)
    assert output.count('\r') >= 2, 'TTY updates retain the actual in-place terminal protocol'
    visible = _terminal_visible_lines(output)
    assert len(visible) == 4 and visible[:2] == ['Sequential fit: scan-demo', ''], (
        'The final screen keeps project title, blank line, aligned headings and one summary row'
    )
    assert [part.split() for part in visible[2].split(' │ ')][:3] == [
        ['Progress'],
        ['OK', 'Failed'],
        ['Elapsed', 'Left'],
    ], 'The redrawn heading retains the owner-ordered mandatory groups'
    assert '3/3' in visible[3] and '100.0%' in visible[3], (
        'The final terminal row freezes the exact total and full progress bar'
    )
    assert 'scan ·' not in output, 'No separate summary is printed after the final terminal row'


def test_scan_iteration_stream_is_suppressed_by_default_and_present_at_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli.edi, 'iteration_line', lambda row, _previous, _variant: f'ITER {row.iteration}'
    )
    compact_output, compact = _run_fake_human(
        monkeypatch,
        verbosity=edi.VerbosityEnum.COMPACT,
        tty=False,
    )
    full_output, full = _run_fake_human(
        monkeypatch,
        verbosity=edi.VerbosityEnum.FULL,
        tty=False,
    )
    assert (
        'ITER ' not in compact_output and compact.analysis.iteration_subscribers == [False] * 3
    ), ' default scan verbosity must suppress per-iteration subscription and output'
    assert 'ITER 1' in full_output and full.analysis.iteration_subscribers == [True] * 3, (
        ' FULL scan verbosity must keep per-iteration diagnostics reachable'
    )


def test_scan_off_runs_without_subscribers_or_output(monkeypatch: pytest.MonkeyPatch) -> None:
    project = _FakeProject()
    monkeypatch.setattr(cli.edi._edi, '_metric_variant', lambda _project: 'powder')
    output = _Capture(tty=False)
    monkeypatch.setattr(cli.sys, 'stdout', output)
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.OFF,
            'scan-demo',
            clock=_Clock(),
        )
        == 0
    ), ' OFF scan must still complete successfully'
    assert not output.getvalue(), ' OFF scan must print nothing'
    assert project.analysis.iteration_subscribers == [False] * 3, (
        ' OFF scan must register no per-iteration subscriber'
    )


def test_cli_delegates_every_scan_line_to_core_renderers() -> None:
    source = (ROOT / 'lib' / 'edi' / '__main__.py').read_text(encoding='utf-8')
    module = ast.parse(source)
    functions = {
        node.name: ast.get_source_segment(source, node) or ''
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    reachable = {'_run_human'}
    pending = ['_run_human']
    while pending:
        name = pending.pop()
        assert name in functions, 'The delegated CLI formatting path must resolve'
        calls = {
            call.func.id
            for call in ast.walk(ast.parse(functions[name]))
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        for called in calls & functions.keys() - reachable:
            reachable.add(called)
            pending.append(called)
    run_human = '\n'.join(functions[name] for name in reachable)
    called = {
        call.func.attr
        for call in ast.walk(ast.parse(run_human))
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }
    assert {
        '_scan_progress_heading',
        '_scan_progress_row',
    } <= called, (
        'Both actual progress headings and complete row updates delegate to the shared core'
    )
    forbidden = ('████', 'elapsed ', ' eta ', 'failed ·')
    assert not any(token in run_human for token in forbidden), (
        ' CLI may choose stdout policy but must not own scan-line format literals'
    )


def test_single_fit_stream_contract_remains_byte_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preamble = SimpleNamespace(pre_fit=SimpleNamespace(reduced_chi_square=24.2159))

    class SingleAnalysis:
        fitting_mode = 'single'

        def __init__(self) -> None:
            self.events: list[str] = []

        def fit(self, *, on_iteration: Any, on_start: Any) -> SimpleNamespace:
            on_start(preamble)
            on_iteration(SimpleNamespace(iteration=1, reduced_chi_square=16.8435))
            self.events.append('fit')
            return SimpleNamespace()

    analysis = SingleAnalysis()
    project = SimpleNamespace(analysis=analysis)
    monkeypatch.setattr(cli.edi._edi, '_metric_variant', lambda _project: 'powder')
    monkeypatch.setattr(cli.edi, 'stream_header', lambda _p, _name, _variant: 'HEADER\n')
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda _row, _previous, _variant: 'ROW')
    monkeypatch.setattr(cli.edi, 'summary_line', lambda _outcome, _variant: 'SUMMARY\n')
    output = _Capture(tty=False)
    monkeypatch.setattr(cli.sys, 'stdout', output)
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.COMPACT,
            'single-demo',
            clock=_Clock(),
        )
        == 0
    ), ' single-fit compatibility control must complete successfully'
    assert output.getvalue() == 'HEADER\nROW\nSUMMARY\n', (
        ' must leave the existing single-fit stream byte-unchanged'
    )
    assert analysis.events == ['fit'], ' single-fit compatibility control must run one fit'
