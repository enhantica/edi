# SPDX-License-Identifier: BSD-3-Clause
"""``python -m edi`` — edi's command-line entry point.

    python -m edi fit <project-dir> [--dry] [--verbosity ...] [--report ...] [--stream]
    python -m edi calc <project-dir> [--dry] [--verbosity ...] [--report machine|human]
    python -m edi undo <project-dir> [--dry] [--verbosity ...] [--report machine|human]

This exists because an example script was doing the job: ``examples/fit_ncaf.py`` had accreted
argument parsing, verbosity handling and two output formats, which made it an undeclared
public interface with no stability contract and a path that breaks the moment the file is
renamed. The example is an example again; this is the supported entry point.

**No formatting lives here.** Both reports are rendered by ``edi::core``
(``edi.machine_report`` and the streaming formatters), so this module, a notebook, and the later
desktop/WASM surfaces all render one implementation. This file only parses arguments, chooses a
stream, and prints.

Two channels with different jobs:

* ``--report machine`` is the *verification* channel — the versioned ``key=value`` record
  defined by crysta and emitted by the engine's own emitter, so ``crysta fit`` and
  ``edi fit`` can be compared with ``diff`` rather than by reading two terminals.
* ``--report human`` (the default) is the *user* channel, owned by edi and free to evolve.

Streams follow the contract: the selected report goes entirely to **stdout**, and **stderr carries
only what is not part of the contract** — warnings and errors. That is what keeps
``diff <(crysta fit P --verbosity compact) <(python -m edi fit P --report machine --verbosity
compact)`` a single comparison.
"""

from __future__ import annotations

import argparse
import contextlib
import math
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Self

import edi

# One verbosity for both channels, so --verbosity means the same thing whichever --report is
# chosen.
_VERBOSITY = {
    'off': edi.VerbosityEnum.OFF,
    'compact': edi.VerbosityEnum.COMPACT,
    'full': edi.VerbosityEnum.FULL,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m edi',
        description='Fit a complete .edi project directory.',
    )
    subcommands = parser.add_subparsers(dest='command', required=True)
    # `fit` only. A speculative subcommand family would be inventing an interface nobody asked for;
    # this is what exists and what was requested.
    fit = subcommands.add_parser('fit', help='refine a project directory')
    fit.add_argument(
        'project',
        help='project directory (structures/, experiments/, analysis/) with embedded measured'
        ' data',
    )
    # The minimization conditions — descent, chi-square tolerance and iteration budget — are
    # declared in the project's analysis/analysis.edi (`_minimizer.*`), never on this command
    # line: like diffraction-lib's `fit`, it takes the project and --dry (plus the output-channel
    # options below). The valid descent ids are documented beside the other analysis.edi fields
    # (docs/user/guides/complete-project-loading.md).
    fit.add_argument(
        '--verbosity',
        choices=('off', 'compact', 'full'),
        default='compact',
        help="how much to report: 'off' prints nothing, 'compact' the summary, 'full' adds "
        'per-bank R-factors, every iteration and every refined parameter (default: compact)',
    )
    fit.add_argument(
        '--report',
        choices=('machine', 'human'),
        default='human',
        help="which channel to print: 'human' is the readable view, 'machine' the versioned "
        'key=value record that is byte-comparable with `crysta fit` (default: human)',
    )
    fit.add_argument(
        '--stream',
        action='store_true',
        help='stream live per-iteration progress. The human report streams a single fit (rows '
        'appear as each iteration completes); this flag adds live record=progress records to the '
        'machine report, emitted before the terminal record=fit (default: off, so machine output '
        'is byte-identical to a non-streamed run). A SCAN (_fitting_mode.type sequential or '
        'independent) reports per-FILE progress on the human channel instead — one self-updating '
        'line on a TTY, one line per file otherwise, per-iteration rows at --verbosity full — '
        'and never streams on the machine channel: its per-file iteration sequences a single-fit '
        'progress record cannot honestly represent.',
    )
    # A fit PERSISTS the refined project by default (the anchor's `fit [--dry]`); --dry opts
    # out and leaves the project tree byte-identical.
    fit.add_argument(
        '--dry',
        action='store_true',
        help='refine without writing: leave the project tree byte-identical (the default writes '
        'the refined project back into its own directory)',
    )
    # The forward calculation, mirroring `crysta <project-dir> calc`. The output is the
    # versioned record=calc machine record, byte-comparable with crysta's by construction
    # (both render through crysta's own emitter).
    calc = subcommands.add_parser('calc', help='forward-calculate a project directory')
    calc.add_argument(
        'project',
        help='project directory (structures/, experiments/, analysis/) with embedded measured '
        'data or a declared _data_range grid',
    )
    calc.add_argument(
        '--dry',
        action='store_true',
        help='calculate without writing: leave the project tree byte-identical (the default '
        'writes the _data_calc series into each experiment file, replacing any previous '
        'calculated block)',
    )
    calc.add_argument(
        '--verbosity',
        choices=('off', 'compact', 'full'),
        default='compact',
        help="how much to report: 'off' prints nothing; 'compact' and 'full' are identical "
        'for a calculation — it has no iterations or parameters (default: compact)',
    )
    calc.add_argument(
        '--report',
        choices=('machine', 'human'),
        default='machine',
        help="which channel to print: 'machine' (the default) is the versioned record=calc "
        "byte-comparable with `crysta <dir> calc`; 'human' is the readable view",
    )
    undo = subcommands.add_parser('undo', help='undo the last fit of a project directory')
    undo.add_argument('project', help='project directory previously fitted (and saved)')
    undo.add_argument(
        '--dry',
        action='store_true',
        help='preview: report what undo would restore without writing anything',
    )
    undo.add_argument(
        '--verbosity',
        choices=('off', 'compact', 'full'),
        default='compact',
        help="how much to report: 'off' prints nothing, 'compact' the summary, 'full' adds "
        'every restored parameter (default: compact)',
    )
    undo.add_argument(
        '--report',
        choices=('machine', 'human'),
        default='machine',
        help="which channel to print: 'machine' (the default) is the versioned key=value record "
        "byte-comparable with `crysta undo`; 'human' is the readable view",
    )
    return parser


def run_fit(args: argparse.Namespace) -> int:
    # `--dry` promises a byte-identical tree. A scan writes analysis/results.csv DURING the
    # fit, before any persistence decision is reached, so its outputs go to a disposable
    # directory. Nothing is copied — the project is loaded and its scan data read IN PLACE,
    # and
    # `_dry_run_into` makes the disposable directory the project's path, where crysta's driver
    # writes the results (seeding them from the loaded project's committed rows, so a dry run
    # resumes exactly as a real one would). A single or joint fit writes nothing while it runs,
    # and the save below is skipped under --dry. The reports carry numbers and status, never
    # paths; the human header's project name is taken from the original argument.
    with contextlib.ExitStack() as stack:
        project = edi.Project.load(args.project)
        if args.dry and _is_scan(project):
            project._dry_run_into(
                stack.enter_context(tempfile.TemporaryDirectory(prefix='edi-dry-'))
            )
        verbosity = _VERBOSITY[args.verbosity]

        with _CancelOnSigint():
            if args.report == 'human':
                code = _run_human(project, verbosity, Path(args.project).name)
            else:
                code = _run_machine(project, verbosity, stream=args.stream)
        if code == _EXIT_CANCELLED:
            print(_resume_hint(project, dry=args.dry), file=sys.stderr)
        # Persist the refined project by default (results and the pre-fit snapshot are already in
        # the model). The human channel narrates the save; the machine channel writes silently,
        # keeping stdout the versioned record and nothing else. Under --dry this is skipped. A
        # cancelled fit (exit 130) saves nothing.
        if code == 0 and not args.dry:
            if args.report == 'human':
                project.save()
            else:
                project._save_silent()
        return code


# The conventional exit status of a run stopped by SIGINT (128 + 2).
_EXIT_CANCELLED = 130


class _CancelOnSigint:
    """The first Ctrl+C cancels cleanly; the second exits hard.

    The first SIGINT restores the default disposition and raises KeyboardInterrupt. The fit
    runs natively, so the handler runs at the engine's next cancel poll between iterations,
    where edi turns the KeyboardInterrupt into a clean cancel: the fit returns CANCELLED and a
    scan keeps every committed row as its resume point. With the default disposition back, a
    second SIGINT terminates the process at once. The previous handler is restored on exit.
    """

    def __init__(self) -> None:
        self._previous = None

    @staticmethod
    def _on_sigint(_signum: int, _frame: object) -> None:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        raise KeyboardInterrupt

    def __enter__(self) -> Self:
        self._previous = signal.signal(signal.SIGINT, self._on_sigint)
        return self

    def __exit__(self, *_exc: object) -> None:
        signal.signal(signal.SIGINT, self._previous)


def _exit_code(outcome: object) -> int:
    """130 for a cancelled fit (the SIGINT convention), else 0."""
    return _EXIT_CANCELLED if getattr(outcome, 'status', None) == edi.FitStatus.CANCELLED else 0


def _resume_hint(project: edi.Project, *, dry: bool) -> str:
    """The stderr line a cancelled run ends with: what was kept and how to continue."""
    if not _is_scan(project):
        return 'edi fit: cancelled - the project was left unchanged.'
    if dry:
        return 'edi fit: cancelled - a --dry run keeps nothing; the project was left unchanged.'
    return (
        'edi fit: cancelled - every finished file is kept; run the same command again to resume '
        'from the next file.'
    )


def _fit(project: edi.Project, **kwargs: object):
    """Fit the project via the analysis facade (joint or single per its fitting mode)."""
    return project.analysis.fit(**kwargs)


def _is_scan(project: edi.Project) -> bool:
    """True iff the project declares a scan mode, whose progress a single-fit renderer cannot show.

    . A scan is N fits, so the single-fit streaming contract does not hold over it: the engine
    fires no whole-scan preamble (a fabricated one would report numbers no fit produced), and the
    per-iteration callbacks it does fire restart their numbering at every file. Rendering those
    through the single-fit streamer produced headerless rows, a first `change` computed against a
    synthetic zero, and several restarted sequences run together as if they were one descent.
    """
    # The ONE scan-mode set, from the package (edi/__init__.py), never a second copy here —
    # a duplicated enumeration in the CLI is the same drift class the mode contract just
    # paid for.
    return project.analysis.fitting_mode in edi._SCAN_FITTING_MODES


def _run_human(project: edi.Project, verbosity, project_name: str, *, clock=time.monotonic) -> int:
    # The human report streams for a SINGLE fit: the header + pre-fit row on `on_start`, each
    # iteration row as it completes, the summary after — killing the ~30 s silence. Nothing
    # here formats: the core owns every line (stream_header / iteration_line / summary_line /
    # parameter_table, and for a scan scan_progress_line / scan_summary); this only chooses
    # stdout, flushes per line, and threads `previous`.
    # `clock` is the injected time source for the scan progress line's elapsed/ETA —
    # a zero-argument callable returning seconds. Injected so the values are testable facts
    # rather than wall-clock reads inside assertions; production callers never pass it.
    if verbosity == edi.VerbosityEnum.OFF:
        if _is_scan(project):
            # The OFF contract prints nothing, but a scan fit still declares both scan-event
            # subscribers: the seam is part of the call contract, and OFF gates EMISSION, not
            # subscription. The no-op subscribers write nothing.
            outcome = _fit(
                project,
                on_scan_start=lambda _preamble: None,
                on_file_complete=lambda _record: None,
            )
        else:
            outcome = _fit(project)  # run the fit, print nothing — the OFF contract
        return _exit_code(outcome)

    if _is_scan(project):
        # The scan progress view — the whole-scan replacement for the single-fit streaming
        # this branch used to suppress outright. The core fires a scan
        # preamble (carrying the file total) and one completion event per fitted file; this
        # surface renders every line through the core's renderers (edi.scan_progress_line /
        # edi.scan_summary) and only chooses the emission mode: in place on a TTY, one line per
        # file when stdout is not one — notebook-tests, docs and CI read this output, and a
        # carriage return would pollute the logs those gates parse. Per-iteration output is
        # SUPPRESSED at default verbosity (a 213-file scan is ~165,000 iteration rows, which
        # moves the cursor and makes in-place updating impossible) and reachable at FULL, where
        # the progress lines fall back to one-per-file emission for the same cursor reason.
        stream_iterations = verbosity == edi.VerbosityEnum.FULL
        tty = bool(getattr(sys.stdout, 'isatty', lambda: False)()) and not stream_iterations
        started = clock()
        # Review-1 F2 — ONE population, ONE time basis. `tally` folds every committed row of THIS
        # SCAN exactly once: the preamble's already-committed resume rows first, then one per
        # file completed during this call. Every scan-wide quantity below (completed/ok/fail and
        # the χ² range) comes from that one fold, so no counter is seeded from history while the
        # facts beside it describe only this invocation. The fold is INCREMENTAL — the retired
        # form re-scanned every prior row on every event, so file N cost N and a 5 184-file scan
        # slowed quadratically. `prior` marks where this call's rows begin, and it exists for
        # exactly one reason: TIME. A committed row records iterations, never duration, so the
        # injected clock can only ever measure the rows after `prior`, and that count — not the
        # whole-scan total — is what the renderers receive as
        # `measured_completed`.
        # Prose note: this function must not contain the scan line's format literals — the core
        # owns every one of them — so the groups are described here by name, never quoted.
        state = {'total': None, 'elapsed': 0.0}
        live = [False]
        last_width = [0]
        tally = _ScanTally()
        prior = [0]
        previous = [0.0]

        def _emit_progress(line: str) -> None:
            if tty:
                # An in-place rewrite must cover the PREVIOUS line's full width: `\r` moves the
                # cursor, it erases nothing, so any SHORTER successor — the frozen 100 % line
                # dropping eta/file/χ², a shorter file name — would leave the predecessor's
                # tail visible (owner-measured on the 213-file scan: the stale ` · 2 fail ·
                # <file> · χ² …` read as a doubled fail group). Space padding, not an ANSI
                # erase, so a TTY that interprets no escape sequences still shows a clean line;
                # every character this line emits is single-column, so its length is its width.
                padding = ' ' * max(0, last_width[0] - len(line))
                sys.stdout.write('\r' + line + padding)
                last_width[0] = len(line)
                live[0] = True
            else:
                sys.stdout.write(line + '\n')
            sys.stdout.flush()

        def on_scan_start(preamble: object) -> None:
            state['total'] = preamble.total_files
            # Resume seeding: the rows an interrupted earlier run already committed join the
            # scan's population, so a resumed scan starts truthful (`39/213`, not `1/213`) AND
            # can still name the failures among them. Empty on a fresh scan; a preamble source
            # that carries no resume rows (a test fake) means the same thing.
            for row in getattr(preamble, 'completed_rows', []):
                tally.add(row)
            prior[0] = tally.completed

        def on_file_complete(record: object) -> None:
            tally.add(record)
            state['elapsed'] = clock() - started
            _emit_progress(
                edi.scan_progress_line(
                    completed=tally.completed,
                    total_files=state['total'],
                    elapsed_seconds=state['elapsed'],
                    measured_completed=tally.completed - prior[0],
                    ok_count=tally.ok,
                    fail_count=tally.failed,
                    file_name=record.file_name,
                    reduced_chi_square=record.reduced_chi_square,
                )
            )

        def on_scan_iteration(record: object) -> None:
            sys.stdout.write(edi.iteration_line(record, previous[0]) + '\n')
            sys.stdout.flush()
            previous[0] = record.reduced_chi_square

        # The terminal FitResultBase serves only the exit status here: the scan summary below is
        # the whole scan's report, while summary_line / parameter_table describe ONE fit's
        # terminal state, which a scan does not have.
        if stream_iterations:
            outcome = _fit(
                project,
                on_scan_start=on_scan_start,
                on_file_complete=on_file_complete,
                on_iteration=on_scan_iteration,
            )
        else:
            outcome = _fit(project, on_scan_start=on_scan_start, on_file_complete=on_file_complete)
        if live[0]:
            # Freeze the in-place line: the bar finishes at 100% and stays; the summary follows.
            sys.stdout.write('\n')
        # Every group below comes from the SAME fold — counts and χ² bounds alike — so the
        # summary cannot report a χ² range over a narrower set than the files it counts.
        # Failures are counted, never listed: the per-file outcome is in analysis/results.csv.
        # `measured_completed` carries the one quantity that legitimately covers less: the
        # clock.
        sys.stdout.write(
            edi.scan_summary(
                total_files=state['total'] if state['total'] is not None else tally.completed,
                ok_count=tally.ok,
                fail_count=tally.failed,
                chi2_min=tally.chi2_min,
                chi2_max=tally.chi2_max,
                elapsed_seconds=state['elapsed'],
                measured_completed=tally.completed - prior[0],
            )
        )
        skipped = _skipped_line(project)
        if skipped:
            sys.stdout.write(skipped + '\n')
        sys.stdout.flush()
        return _exit_code(outcome)

    return _stream_single_fit(project, verbosity, project_name)


def _skipped_line(project: edi.Project) -> str:
    """What crysta noted about the scan's files, from analysis/scan-notes.csv."""
    directory = getattr(getattr(project, 'metadata', None), 'path', None)
    if directory is None:
        return ''
    try:
        lines = (Path(directory) / 'analysis' / 'scan-notes.csv').read_text('utf-8').splitlines()
    except OSError:
        return ''
    if not lines or lines[0] != 'file_path,negative_points,skipped_dataset,refusal':
        return ''
    files = points = 0
    refused = []
    for line in lines[1:]:
        cells = line.split(',')
        if len(cells) != 4 or not cells[1].isdigit():
            continue
        points += int(cells[1])
        files += cells[2] == 'True'
        if cells[3]:
            refused.append(f'  {cells[0].rsplit("/", 1)[-1]}: {cells[3]}')
    out = []
    if files or points:
        out.append(
            f'Skipped: {files} file(s) with no intensity above zero, '
            f'{points} point(s) with a negative intensity'
        )
    if refused:
        out.append(f'Refused: {len(refused)} file(s), recorded as failed')
        out.extend(refused[:10])
        if len(refused) > 10:
            out.append(f'  ... and {len(refused) - 10} more')
    if out:
        out.append('(analysis/scan-notes.csv)')
    return '\n'.join(out)


class _ScanTally:
    """The scan-wide aggregates, folded one committed row at a time.

    Constant work per row, so a scan's progress costs the same at file 5 000 as at file 1.
    """

    def __init__(self) -> None:
        self.completed = 0
        self.ok = 0
        self.chi2_min = float('nan')
        self.chi2_max = float('nan')

    @property
    def failed(self) -> int:
        return self.completed - self.ok

    def add(self, record: object) -> None:
        chi = record.reduced_chi_square
        if not math.isnan(chi):  # a refused file has none
            self.chi2_min = chi if math.isnan(self.chi2_min) else min(self.chi2_min, chi)
            self.chi2_max = chi if math.isnan(self.chi2_max) else max(self.chi2_max, chi)
        self.completed += 1
        self.ok += 1 if record.converged else 0


def _stream_single_fit(project: edi.Project, verbosity, project_name: str) -> int:
    # The `change` basis is the previous row's reduced chi2; iteration 1's basis is the pre-fit
    # row's, so it shows its improvement over the initial model. Boxed for the callbacks.
    previous = [0.0]

    def on_start(preamble: object) -> None:
        sys.stdout.write(edi.stream_header(preamble, project_name))
        sys.stdout.flush()
        previous[0] = preamble.pre_fit.reduced_chi_square

    def on_iteration(record: object) -> None:
        sys.stdout.write(edi.iteration_line(record, previous[0]) + '\n')
        sys.stdout.flush()
        previous[0] = record.reduced_chi_square

    outcome = _fit(project, on_iteration=on_iteration, on_start=on_start)
    sys.stdout.write(edi.summary_line(outcome))
    if verbosity == edi.VerbosityEnum.FULL:
        sys.stdout.write(edi.parameter_table(outcome))
    sys.stdout.flush()
    return _exit_code(outcome)


def _run_machine(project: edi.Project, verbosity, *, stream: bool) -> int:
    # The machine channel is the versioned contract on stdout. With --stream, a record=progress is
    # written (flushed) after each accepted step, BEFORE the terminal record=fit; without it, the
    # output is byte-identical to a non-streamed run so the conformance is unaffected. At
    # verbosity off the record is empty, so streaming nothing is the honest OFF behaviour.
    if stream and verbosity != edi.VerbosityEnum.OFF and not _is_scan(project):

        def on_iteration(record: object) -> None:
            sys.stdout.write(edi.progress_report(record))
            sys.stdout.flush()

        outcome = _fit(project, on_iteration=on_iteration)
    else:
        outcome = _fit(project)
    # `end=''` because the core's reports are already newline-terminated, and an extra blank line
    # would be a spurious diff against `crysta fit`.
    report = edi.machine_report(project, outcome, verbosity)
    if report:
        print(report, end='')
    return _exit_code(outcome)


# The idempotence marker, byte-identical to crysta's (src/cli/main.cpp kCalcMarker): everything
# from this line on is regenerated by `calc`. The SHARED literal is load-bearing, not cosmetic —
# either engine's re-run must drop the block the other engine wrote, and the written trees must be
# byte-comparable.
_CALC_MARKER = '# --- calculated series (crysta calc; regenerated on every run) ---'


def _calc_target(directory: str, experiment) -> Path:
    """The experiment document a calc writes back into.

    ADR-0016: the path comes from crysta's one name -> path decision (``edi._entity_path``),
    which refuses by name a datablock name outside the persisted-name domain -- this module
    composes no path from a name itself.
    """
    path = Path(edi._entity_path(directory, 'experiment', experiment.name))
    if not path.is_file():
        raise ValueError(f'cannot write calculated series: {path} does not exist')
    return path


def _write_back_calculated(path: Path, grid, calculated) -> None:
    """Write the calculated series into the experiment's own .edi as a SEPARATE block.

    Mirrors crysta's `write_back_calculated` byte-for-byte: everything before the marker is
    preserved, any previous calculated block is dropped (repeated runs stay idempotent), and the
    `_data_calc` loop is appended. The measured columns are never touched. `{:g}` matches the
    C++ default `operator<<` double formatting (printf %g, 6 significant digits).
    """
    lines = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line == _CALC_MARKER:
            break
        lines.append(line)
    lines.extend((
        _CALC_MARKER,
        'loop_\n_data_calc.point_id\n_data_calc.x\n_data_calc.intensity_calc',
    ))
    lines.extend(
        f'{index + 1} {grid[index]:g} {value:g}' for index, value in enumerate(calculated)
    )
    path.write_text(''.join(f'{line}\n' for line in lines), encoding='utf-8')


def run_calc(args: argparse.Namespace) -> int:
    # The forward-calculation path, through the SAME analysis facade every edi surface uses.
    # The record's numbers are read back from where the facade left the results (each
    # experiment's data.intensity_calc), never computed alongside, so the record and the
    # written series can only describe what the facade actually did.
    started = time.perf_counter()
    project = edi.Project.load(args.project)
    # Every experiment's target is resolved (and refused by name when its name cannot be
    # persisted) BEFORE anything is calculated or written, so a refusal leaves the project
    # tree -- and any path outside it -- unchanged.
    targets = (
        []
        if args.dry
        else [_calc_target(args.project, experiment) for experiment in project.experiments]
    )
    project.analysis.calculate()
    total_points = 0
    checksum = 0.0
    for index, experiment in enumerate(project.experiments):
        calculated = experiment.data.intensity_calc
        total_points += len(calculated)
        # Accumulated value-by-value in experiment order, exactly as crysta's run_calc folds it —
        # per-experiment partial sums would round differently and break byte-comparability.
        for value in calculated:
            checksum += value
        if not args.dry:
            _write_back_calculated(targets[index], experiment.data.axis(), calculated)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    verbosity = _VERBOSITY[args.verbosity]
    if getattr(args, 'report', 'machine') == 'human':
        # The human channel, mirroring undo's shape: a readable line, silent at off.
        if verbosity != edi.VerbosityEnum.OFF:
            written = 'left unwritten (--dry)' if args.dry else 'written back'
            sys.stdout.write(
                f'Calculated {total_points} point(s) over '
                f'{len(project.experiments)} experiment(s); the _data_calc series was '
                f'{written}.\n'
            )
        return 0
    # The engine's own emitter (edi core -> crysta format_fit_report); empty at verbosity off.
    record = edi._calc_report(total_points, checksum, elapsed_ms, verbosity)
    if record:
        print(record, end='')
    return 0


def run_undo(args: argparse.Namespace) -> int:
    # Undo the last fit — restore the persisted start state, clear the snapshot, and save the
    # restored project back unless --dry or the outcome was a no-op (a no-op mutates nothing,
    # byte-identically). The machine record mirrors `crysta undo` byte-for-byte.
    project = edi.Project.load(args.project)
    restored, was_no_op = project._undo_fit()
    verbosity = _VERBOSITY[args.verbosity]
    if not args.dry and not was_no_op:
        if args.report == 'human':
            project.save()
        else:
            project._save_silent()
    if verbosity == edi.VerbosityEnum.OFF:
        return 0
    if args.report == 'machine':
        lines = [
            'schema=8',
            'record=undo',
            f'was_no_op={"true" if was_no_op else "false"}',
            f'restored={len(restored)}',
        ]
        if verbosity == edi.VerbosityEnum.FULL:
            lines.extend(f'restored_parameter={name}' for name in restored)
        sys.stdout.write('\n'.join(lines) + '\n')
    elif was_no_op:
        sys.stdout.write('Nothing to undo: no fit state is recorded in this project.\n')
    else:
        sys.stdout.write(f'Restored {len(restored)} parameter(s) to their pre-fit state.\n')
        if verbosity == edi.VerbosityEnum.FULL:
            sys.stdout.write(''.join(f'  {name}\n' for name in restored))
    return 0


def main(argv: list[str] | None = None) -> int:
    # Argument parsing is NOT a run: argparse exits on its own for a usage error, and no record is
    # emitted, because nothing was attempted. Everything below has reached the point of
    # attempting a fit, so a failure there yields the minimal error RECORD on stdout — a parser
    # gets a well-formed "this run produced no fit" rather than silence it cannot distinguish
    # from a crash.
    args = build_parser().parse_args(argv)
    try:
        if args.command == 'undo':
            return run_undo(args)
        if args.command == 'calc':
            return run_calc(args)
        return run_fit(args)
    except (edi.IoError, ValueError) as error:
        # The record is contract content and goes to stdout; the prose explanation is not, and goes
        # to stderr beside the non-zero exit. At --verbosity off the record is empty and nothing is
        # written, exactly as a successful fit prints nothing there.
        record = edi.error_report(_VERBOSITY[args.verbosity])
        if record:
            print(record, end='')
        print(f'edi fit: {error}', file=sys.stderr)
        # An engine refusal keeps its catalogue code, so a script can tell the causes apart.
        for diagnostic in getattr(error, 'diagnostics', ()):
            if diagnostic.code:
                print(f'edi fit: {diagnostic.code}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
