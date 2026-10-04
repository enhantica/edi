"""parser contract for edi's public ``calc`` verb."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import edi


def _calc_project() -> tuple[SimpleNamespace, list[str]]:
    calls: list[str] = []
    experiment = SimpleNamespace(
        name='bank',
        data=SimpleNamespace(
            intensity_calc=[3.0, 4.25],
            axis=lambda: [1.25, 2.5],
        ),
    )
    project = SimpleNamespace(
        analysis=SimpleNamespace(calculate=lambda: calls.append('calculate')),
        experiments=[experiment],
    )
    return project, calls


def test_calc_parser_exposes_the_project_dry_and_machine_record_contract() -> None:
    cli = importlib.import_module('edi.__main__')
    parser = cli.build_parser()
    parsed = parser.parse_args([
        'calc',
        'example-project',
        '--dry',
        '--report',
        'machine',
        '--verbosity',
        'compact',
    ])
    assert parsed.command == 'calc', ' requires calc to be a public edi subcommand'
    assert parsed.project == 'example-project', ' calc must take one project directory'
    assert parsed.dry is True, ' calc --dry must reach the parsed execution contract'
    assert parsed.report == 'machine', ' calc must expose the machine-record channel'
    assert parsed.verbosity == 'compact', ' calc must expose crysta-compatible verbosity'


def test_calc_runs_the_facade_writes_the_crysta_block_and_reports_its_values(
    tmp_path, monkeypatch, capsys
) -> None:
    cli = importlib.import_module('edi.__main__')
    project, calls = _calc_project()
    project_root = tmp_path / 'project'
    experiment_path = project_root / 'experiments' / 'bank.edi'
    experiment_path.parent.mkdir(parents=True)
    experiment_path.write_text(
        f'_audit.creation_date 2026-09-20\n{cli._CALC_MARKER}\nstale calculated content\n',
        encoding='utf-8',
    )
    seen_report: list[tuple[int, float, float, object]] = []

    def load(path: str):
        calls.append(f'load:{path}')
        return project

    def calc_report(total_points, checksum, elapsed_ms, verbosity):
        seen_report.append((total_points, checksum, elapsed_ms, verbosity))
        return 'schema=8\nrecord=calc\n'

    ticks = iter((10.0, 10.25))
    monkeypatch.setattr(cli.edi, 'Project', SimpleNamespace(load=load))
    monkeypatch.setattr(cli.edi, '_calc_report', calc_report)
    monkeypatch.setattr(cli.time, 'perf_counter', lambda: next(ticks))

    assert cli.main(['calc', str(project_root), '--report', 'machine']) == 0, (
        ' a successful calc must return success through the public CLI dispatcher'
    )
    assert calls == [f'load:{project_root}', 'calculate'], (
        ' calc must load once and execute exactly the shared analysis facade once'
    )
    assert seen_report == [(2, 7.25, 250.0, edi.VerbosityEnum.COMPACT)], (
        ' the machine record must receive the facade-produced point count, checksum, '
        'elapsed time and selected verbosity'
    )
    assert experiment_path.read_text(encoding='utf-8') == (
        '_audit.creation_date 2026-09-20\n'
        f'{cli._CALC_MARKER}\n'
        'loop_\n'
        '_data_calc.point_id\n'
        '_data_calc.x\n'
        '_data_calc.intensity_calc\n'
        '1 1.25 3\n'
        '2 2.5 4.25\n'
    ), (
        ' write mode must replace the stale calculated block with crysta-compatible '
        '_data_calc rows while preserving the project content before the shared marker'
    )
    assert capsys.readouterr() == ('schema=8\nrecord=calc\n', ''), (
        ' machine calc must emit only the engine record on stdout'
    )


def test_calc_dry_runs_the_facade_but_leaves_the_tree_byte_identical(
    tmp_path, monkeypatch, capsys
) -> None:
    cli = importlib.import_module('edi.__main__')
    project, calls = _calc_project()
    project_root = tmp_path / 'project'
    experiment_path = project_root / 'experiments' / 'bank.edi'
    experiment_path.parent.mkdir(parents=True)
    before = b'_audit.creation_date 2026-09-20\n'
    experiment_path.write_bytes(before)
    monkeypatch.setattr(
        cli.edi,
        'Project',
        SimpleNamespace(load=lambda _path: project),
    )
    ticks = iter((20.0, 20.5))
    monkeypatch.setattr(cli.time, 'perf_counter', lambda: next(ticks))

    assert (
        cli.main([
            'calc',
            str(project_root),
            '--dry',
            '--report',
            'human',
            '--verbosity',
            'compact',
        ])
        == 0
    ), ' a dry human calc must still complete successfully'
    assert calls == ['calculate'], (
        ' --dry must suppress persistence, not the shared analysis-facade calculation'
    )
    assert experiment_path.read_bytes() == before, (
        ' --dry must leave every project byte unchanged after calculating'
    )
    assert capsys.readouterr() == (
        (
            'Calculated 2 point(s) over 1 experiment(s); the _data_calc series was '
            'left unwritten (--dry).\n'
        ),
        '',
    ), ' human dry output must report both the calculation and suppressed write-back'
