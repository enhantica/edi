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
    """Replay CR/LF column semantics and return each completed visible row."""
    row: list[str] = []
    cursor = 0
    completed: list[str] = []
    for character in stream:
        if character == '\r':
            cursor = 0
        elif character == '\n':
            completed.append(''.join(row).rstrip())
            row = []
            cursor = 0
        else:
            if cursor == len(row):
                row.append(character)
            else:
                row[cursor] = character
            cursor += 1
    if row:
        completed.append(''.join(row).rstrip())
    return completed


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
    def __init__(self) -> None:
        self.analysis = _FakeAnalysis()


def _run_fake_human(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verbosity: Any,
    tty: bool,
) -> tuple[str, _FakeProject]:
    project = _FakeProject()
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
    assert f'{failures} failed' in lines[-1], (
        ' summary must retain the complete failure count, including resumed rows'
    )
    assert not any(line.startswith('failed ·') for line in lines), (
        ' scan summary must omit the per-file failed list'
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
            event.reduced_chi_square,
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
        '2 ok · 1 fail · cosio_213K · χ² 4.81'
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
    assert summary == ('scan · 3 files · 2 converged · 1 failed · χ² 3.91-8.44 · 14m52s\n'), (
        ' failed scan summary must retain counts and omit the failed-file list'
    )


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


def test_non_tty_emits_one_line_per_file_without_carriage_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _ = _run_fake_human(
        monkeypatch,
        verbosity=edi.VerbosityEnum.COMPACT,
        tty=False,
    )
    assert '\r' not in output, (
        ' non-TTY output must contain no carriage returns that pollute captured logs'
    )
    lines = output.splitlines()
    progress = [line for line in lines if line.startswith('[')]
    assert len(progress) == 3, (
        ' non-TTY output must emit exactly one progress line per completed file'
    )
    assert '1/3' in progress[0] and '33%' in progress[0], (
        ' first line must use the scan preamble N and first completion count'
    )
    assert 'elapsed 1m01s' in progress[0] and 'eta 2m02s' in progress[0], (
        ' elapsed and ETA must come exactly from the injected clock values'
    )
    assert '1 ok' in progress[1] and '1 fail' in progress[1], (
        ' live progress must expose failures as soon as a file fails'
    )
    assert lines[-1:] == [
        'scan · 3 files · 2 converged · 1 failed · χ² 3.91-8.44 · 5m00s',
    ], ' final progress must freeze before the truthful failure-count summary'


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
    progress = [line for line in lines if line.startswith('[')]
    assert len(progress) == 2 and '2/3' in progress[0], (
        ' partial resume must emit only the two newly completed files while retaining N'
    )
    assert 'elapsed 1m00s' in progress[0] and 'eta 1m00s' in progress[0], (
        ' resume ETA must divide this run elapsed by this run completions, not by the '
        'historical-plus-current completed count'
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
            clock=_Clock(0.0),
        )
        == 0
    ), ' completed no-op resume must complete without a new fit'

    lines = output.getvalue().splitlines()
    assert not any(line.startswith('[') for line in lines), (
        ' completed no-op resume must not fabricate a per-file completion line'
    )
    _assert_failure_count_without_file_list(lines, seeded)
    assert 'scan · 3 files · 2 converged · 1 failed' in lines[-1] and 'χ²' in lines[-1], (
        ' completed no-op summary must aggregate counts and chi-square over committed rows'
    )
    assert '0s' not in lines[-1], (
        ' completed no-op summary must not present zero elapsed as a measured fit time'
    )


def test_tty_updates_in_place_then_freezes_before_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _ = _run_fake_human(
        monkeypatch,
        verbosity=edi.VerbosityEnum.COMPACT,
        tty=True,
    )
    assert output.count('\r') >= 2, ' TTY progress must update earlier file completions in place'
    visible_lines = _terminal_visible_lines(output)
    assert visible_lines == [
        '[██████████████] · 3/3 · 100% · elapsed 5m00s · 2 ok · 1 fail',
        'scan · 3 files · 2 converged · 1 failed · χ² 3.91-8.44 · 5m00s',
    ], (
        ' TTY output must overwrite the longer penultimate progress row completely, '
        'freeze the exact 100% row, and then show the truthful failure-count summary'
    )


def test_scan_iteration_stream_is_suppressed_by_default_and_present_at_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda row, _previous: f'ITER {row.iteration}')
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
    run_human = functions.get('_run_human', '')
    assert 'edi.scan_progress_line' in run_human and 'edi.scan_summary' in run_human, (
        ' CLI must delegate scan progress and summary formatting to the core'
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
    monkeypatch.setattr(cli.edi, 'stream_header', lambda _p, _name: 'HEADER\n')
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda _row, _previous: 'ROW')
    monkeypatch.setattr(cli.edi, 'summary_line', lambda _outcome: 'SUMMARY\n')
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
