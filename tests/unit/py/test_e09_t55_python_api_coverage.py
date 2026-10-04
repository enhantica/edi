"""unit coverage of public Python routing, values, and errors."""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any, override

import edi
import edi.__main__ as cli
import pytest


def test_python_analysis_facade_round_trips_mode_and_calculation() -> None:
    class ProjectDouble:
        fitting_mode = 'single'

        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def calculate(self) -> None:
            self.calls.append(('calculate', None))

    project = ProjectDouble()
    analysis = edi.Analysis(project)  # type: ignore[arg-type]
    assert analysis.fitting_mode == 'single', (
        'the analysis facade must expose the project fitting-mode spelling'
    )
    analysis.fitting_mode = 'joint'
    assert project.fitting_mode == 'joint', (
        'assigning the facade fitting mode must update the underlying project'
    )
    assert analysis.calculate() is None, (
        'the model-only calculation writes its result into the project and returns None'
    )
    assert [name for name, _payload in project.calls] == ['calculate'], (
        'the facade must issue exactly one call to the selected project operation'
    )


def test_structure_factory_round_trips_full_public_dict_and_rejects_retired_shape() -> None:
    structure = edi.StructureFactory.from_dict({
        'space_group': {'name_h_m': 'P 1', 'coord_system_code': 'abc', 'it_number': 1},
        'cell': {'length_a': {'value': 4.2, 'uncertainty': 0.1, 'free': True}},
        'atom_sites': [
            {
                'id': 'Si1',
                'type_symbol': 'Si',
                'wyckoff_letter': 'a',
                'adp_type': 'Biso',
                'fract': [0.1, 0.2, 0.3],
                'occupancy': 0.5,
                'adp_iso': 0.02,
            }
        ],
        'scattering_lengths_fm': {'Si': 4.1491},
    })
    assert (
        structure.space_group.name_h_m,
        structure.space_group.coord_system_code,
        structure.space_group.it_number,
    ) == ('P 1', 'abc', 1), 'the structure factory must preserve all supplied space-group fields'
    assert (
        structure.cell.length_a.value,
        structure.cell.length_a.uncertainty,
        structure.cell.length_a.free,
    ) == (4.2, 0.1, True), 'the parameter dict must preserve value uncertainty and freedom'
    assert len(structure.atom_sites) == 1, (
        'one supplied atom-site dict must produce exactly one public AtomSite'
    )
    site = structure.atom_sites[0]
    assert (site.id, site.type_symbol, site.wyckoff_letter, site.adp_type) == (
        'Si1',
        'Si',
        'a',
        'Biso',
    ), 'the atom-site public strings must round-trip without normalization'
    assert [site.fract_x.value, site.fract_y.value, site.fract_z.value] == [0.1, 0.2, 0.3], (
        'the fractional-coordinate shorthand must retain its three supplied values'
    )
    assert structure.scattering_lengths_fm == {'Si': 4.1491}, (
        'the open scattering-length map must retain its supplied element and value'
    )
    with pytest.raises(KeyError, match='space-group CATEGORY'):
        edi.StructureFactory.from_dict({'space_group': 'P 1'})


def test_cli_human_and_machine_channels_preserve_public_output_contract(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class AnalysisDouble:
        fitting_mode_reads = 0

        @property
        def fitting_mode(self) -> str:
            self.fitting_mode_reads += 1
            return 'single'

    analysis = AnalysisDouble()
    project = SimpleNamespace(analysis=analysis)
    preamble = SimpleNamespace(pre_fit=SimpleNamespace(reduced_chi_square=9.0))
    iteration = SimpleNamespace(reduced_chi_square=4.0)
    outcome = object()

    def fit(_project: object, **kwargs: Any) -> object:
        assert _project is project, 'the CLI must refine the project instance it was given'
        if 'on_start' in kwargs:
            kwargs['on_start'](preamble)
        if 'on_iteration' in kwargs:
            kwargs['on_iteration'](iteration)
        return outcome

    monkeypatch.setattr(cli, '_fit', fit)
    monkeypatch.setattr(cli.edi, 'stream_header', lambda _p, name: f'HEADER {name}\n')
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda _r, previous: f'ITER {previous}')
    monkeypatch.setattr(cli.edi, 'summary_line', lambda _outcome: 'SUMMARY\n')
    monkeypatch.setattr(cli.edi, 'parameter_table', lambda _outcome: 'PARAMETERS\n')
    monkeypatch.setattr(cli.edi, 'progress_report', lambda _record: 'PROGRESS\n')
    monkeypatch.setattr(cli.edi, 'machine_report', lambda _p, _o, _v: 'MACHINE\n')

    assert cli._run_human(project, edi.VerbosityEnum.FULL, 'demo') == 0, (
        'the full human channel must report successful completion'
    )
    assert capsys.readouterr().out == 'HEADER demo\nITER 9.0\nSUMMARY\nPARAMETERS\n', (
        'the full human channel must order header iteration summary and parameter table'
    )
    assert cli._run_human(project, edi.VerbosityEnum.OFF, 'demo') == 0, (
        'the off human channel must still complete the refinement'
    )
    assert not capsys.readouterr().out, 'the off human channel must write no stdout bytes'

    assert cli._run_machine(project, edi.VerbosityEnum.COMPACT, stream=True) == 0, (
        'the streamed machine channel must report successful completion'
    )
    assert capsys.readouterr().out == 'PROGRESS\nMACHINE\n', (
        'machine progress records must precede the terminal machine report'
    )
    monkeypatch.setattr(cli.edi, 'machine_report', lambda _p, _o, _v: '')
    assert cli._run_machine(project, edi.VerbosityEnum.OFF, stream=True) == 0, (
        'the off machine channel must complete without a terminal record'
    )
    assert not capsys.readouterr().out, 'the off machine channel must write no stdout bytes'
    assert analysis.fitting_mode_reads == 3, (
        'the two human runs and streamed machine run must each inspect the real project '
        'analysis fitting mode; OFF human still selects scan no-op subscribers'
    )


def test_cli_scan_branch_routes_events_and_each_emission_policy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class TerminalCapture(io.StringIO):
        @override
        def isatty(self) -> bool:
            return True

    class ScanAnalysis:
        fitting_mode = 'sequential'

        def __init__(self) -> None:
            self.iteration_subscribers: list[bool] = []

        def fit(self, **callbacks: Any) -> object:
            self.iteration_subscribers.append('on_iteration' in callbacks)
            callbacks['on_scan_start'](SimpleNamespace(total_files=2))
            for index, converged in enumerate((True, False), start=1):
                if 'on_iteration' in callbacks:
                    callbacks['on_iteration'](
                        SimpleNamespace(iteration=index, reduced_chi_square=float(index))
                    )
                callbacks['on_file_complete'](
                    SimpleNamespace(
                        file_name=f'scan-{index}.dat',
                        converged=converged,
                        reduced_chi_square=float(index),
                    )
                )
            return object()

    analysis = ScanAnalysis()
    project = SimpleNamespace(analysis=analysis)
    progress_lines = (
        'PROGRESS 1/2 · previous-file-with-a-long-name',
        'PROGRESS 2/2',
    )
    monkeypatch.setattr(
        cli.edi,
        'scan_progress_line',
        lambda **values: progress_lines[values['completed'] - 1],
    )
    monkeypatch.setattr(
        cli.edi,
        'scan_summary',
        lambda **values: f'SUMMARY {values["ok_count"]}/{values["fail_count"]}\n',
    )
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda row, _previous: f'ITER {row.iteration}')

    compact_clock = iter((0.0, 3.0, 8.0))
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.COMPACT,
            'scan',
            clock=lambda: next(compact_clock),
        )
        == 0
    ), 'the non-TTY compact scan route must complete'
    assert capsys.readouterr().out == f'{progress_lines[0]}\n{progress_lines[1]}\nSUMMARY 1/1\n', (
        'compact scan output must route one core-rendered line per completion and its summary'
    )

    full_clock = iter((0.0, 3.0, 8.0))
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.FULL,
            'scan',
            clock=lambda: next(full_clock),
        )
        == 0
    ), 'the non-TTY FULL scan route must complete'
    assert capsys.readouterr().out == (
        f'ITER 1\n{progress_lines[0]}\nITER 2\n{progress_lines[1]}\nSUMMARY 1/1\n'
    ), 'FULL scan output must retain scan-level iteration diagnostics before each completion'

    terminal = TerminalCapture()
    monkeypatch.setattr(cli.sys, 'stdout', terminal)
    tty_clock = iter((0.0, 3.0, 8.0))
    assert (
        cli._run_human(
            project,
            edi.VerbosityEnum.COMPACT,
            'scan',
            clock=lambda: next(tty_clock),
        )
        == 0
    ), 'the TTY compact scan route must complete'
    assert terminal.getvalue() == (
        '\r'
        + progress_lines[0]
        + '\r'
        + progress_lines[1]
        + ' ' * (len(progress_lines[0]) - len(progress_lines[1]))
        + '\nSUMMARY 1/1\n'
    ), (
        'TTY compact scan output must erase the longer predecessor before freezing its shorter '
        'successor and summary'
    )

    quiet = TerminalCapture()
    monkeypatch.setattr(cli.sys, 'stdout', quiet)
    assert cli._run_human(project, edi.VerbosityEnum.OFF, 'scan') == 0, (
        'the OFF scan route must still run with its no-op scan subscribers'
    )
    assert not quiet.getvalue(), 'the OFF scan route must write no output bytes'
    assert analysis.iteration_subscribers == [False, True, False, False], (
        'only FULL may subscribe to per-iteration scan output across every emission policy'
    )


def test_cli_run_fit_routing_and_error_record_are_python_api_contracts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FitArgsDouble:
        def __init__(self, *, verbosity: str, report: str, stream: bool) -> None:
            self.project = '/tmp/example'
            self.verbosity = verbosity
            self.report = report
            self.stream = stream
            self.dry_reads = 0

        @property
        def dry(self) -> bool:
            self.dry_reads += 1
            return False

    project = object()
    monkeypatch.setattr(cli.edi, 'Project', SimpleNamespace(load=lambda path: (project, path)))

    def human_runner(_loaded: object, _verbosity: object, _name: str) -> int:
        return 12

    def machine_runner(_loaded: object, _verbosity: object, *, stream: bool) -> int:
        assert stream, 'the machine runner must receive the public stream selection'
        return 34

    monkeypatch.setattr(cli, '_run_human', human_runner)
    monkeypatch.setattr(cli, '_run_machine', machine_runner)
    human = FitArgsDouble(verbosity='compact', report='human', stream=False)
    machine = FitArgsDouble(verbosity='full', report='machine', stream=True)
    assert cli.run_fit(human) == 12, (
        'the human report selector must return the human runner status'
    )
    assert cli.run_fit(machine) == 34, (
        'the machine report selector must return the machine runner status'
    )
    assert (human.dry_reads, machine.dry_reads) == (1, 1), (
        'each fit invocation must inspect the parser-populated dry-run selection'
    )

    def reject_fit(_args: object) -> int:
        raise ValueError('bad input')

    monkeypatch.setattr(cli, 'run_fit', reject_fit)
    monkeypatch.setattr(cli.edi, 'error_report', lambda _verbosity: 'record=error\n')
    assert cli.main(['fit', 'project', '--verbosity', 'compact']) == 1, (
        'a public fit input error must return the documented nonzero status'
    )
    captured = capsys.readouterr()
    assert captured.out == 'record=error\n', (
        'a fit input error must preserve the machine-readable stdout error record'
    )
    assert captured.err == 'edi fit: bad input\n', (
        'a fit input error must send its human explanation only to stderr'
    )
