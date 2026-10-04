"""end-to-end parity with crysta's committed ``calc`` behaviour."""

from __future__ import annotations

import hashlib
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from conftest import crysta_reference_prefix, crysta_reference_source

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]


def _crysta_root() -> Path:
    candidates: list[Path] = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    matches = [path for path in candidates if (path / 'tests/fitting/manifest.yml').is_file()]
    assert matches, " requires crysta's committed fitting corpus as the calc oracle"
    return matches[0]


def _crysta_cli() -> Path:
    override = os.environ.get('E09_T58_CRYSTA_CLI')
    executable = Path(override) if override else crysta_reference_prefix() / 'bin/crysta'
    assert executable.is_file(), ' requires the built crysta CLI as its independent oracle'
    return executable


def _stage_project(destination: Path) -> Path:
    source = _crysta_root() / 'tests/fitting/lbco-hrpt-s2/project'
    assert source.is_dir(), ' oracle project lbco-hrpt-s2 must remain committed in crysta'
    shutil.copytree(source, destination)
    return destination


def _tree_bytes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, (
        ' calc invocation must succeed: '
        f'{command!r}\nstdout={completed.stdout}\nstderr={completed.stderr}'
    )
    return completed


def _without_elapsed(record: str) -> str:
    lines = record.splitlines()
    elapsed = [line for line in lines if line.startswith('elapsed_ms=')]
    assert len(elapsed) == 1, ' machine record must carry exactly one informational elapsed_ms row'
    return '\n'.join(line for line in lines if not line.startswith('elapsed_ms=')) + '\n'


def _crysta_calc(project: Path, *, dry: bool) -> subprocess.CompletedProcess[str]:
    command = [str(_crysta_cli()), str(project), 'calc']
    if dry:
        command.append('--dry')
    command.extend(('--verbosity', 'compact'))
    return _run(command)


def _edi_calc(project: Path, *, dry: bool) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        '-m',
        'edi',
        'calc',
        str(project),
        '--report',
        'machine',
        '--verbosity',
        'compact',
    ]
    if dry:
        command.append('--dry')
    return _run(command)


def test_calc_dry_is_byte_clean_and_machine_record_matches_crysta(tmp_path: Path) -> None:
    crysta_project = _stage_project(tmp_path / 'crysta-dry')
    edi_project = _stage_project(tmp_path / 'edi-dry')
    before = _tree_bytes(edi_project)
    reference = _crysta_calc(crysta_project, dry=True)
    candidate = _edi_calc(edi_project, dry=True)
    assert _tree_bytes(edi_project) == before, (
        ' --dry must leave every edi project file byte-identical'
    )
    assert _without_elapsed(candidate.stdout) == _without_elapsed(reference.stdout), (
        ' edi calc machine output must byte-match crysta after removing only elapsed_ms'
    )


def test_calc_write_matches_crysta_tree_and_emits_nonempty_data_calc(tmp_path: Path) -> None:
    crysta_project = _stage_project(tmp_path / 'crysta-write')
    edi_project = _stage_project(tmp_path / 'edi-write')
    before = _tree_bytes(edi_project)
    reference = _crysta_calc(crysta_project, dry=False)
    candidate = _edi_calc(edi_project, dry=False)
    after = _tree_bytes(edi_project)
    assert after != before, ' default calc must write rather than behave like --dry'
    assert after == _tree_bytes(crysta_project), (
        ' edi and crysta calc must write byte-identical project trees from the same input'
    )
    assert _without_elapsed(candidate.stdout) == _without_elapsed(reference.stdout), (
        ' write-mode machine output must byte-match crysta except elapsed_ms'
    )
    experiments = sorted((edi_project / 'experiments').glob('*.edi'))
    assert experiments, ' oracle project must contain at least one experiment file'
    for experiment in experiments:
        text = experiment.read_text(encoding='utf-8')
        assert '_data_calc.intensity_calc' in text, (
            f' calc must write the crysta _data_calc series into {experiment.name}'
        )
        generated = text.split('_data_calc.intensity_calc', 1)[1].strip().splitlines()
        assert generated, f' calc must write nonempty calculated rows to {experiment.name}'


def test_calc_calls_facade_once_and_lazy_read_keeps_reference_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """reads may calculate after the CLI's one facade call returns."""
    crysta_project = _stage_project(tmp_path / 'crysta-facade-control')
    edi_project = _stage_project(tmp_path / 'edi-facade-control')
    reference = _crysta_calc(crysta_project, dry=False)
    edi = importlib.import_module('edi')
    cli = importlib.import_module('edi.__main__')
    calls = 0

    def suppress_facade(self: object) -> None:  # noqa: ARG001 - bound-method witness
        nonlocal calls
        calls += 1

    monkeypatch.setattr(edi.Analysis, 'calculate', suppress_facade)
    try:
        code = cli.main([
            'calc',
            str(edi_project),
            '--report',
            'machine',
            '--verbosity',
            'compact',
        ])
    except (edi.IoError, ValueError):
        code = 1
    captured = capsys.readouterr()
    assert calls == 1, ' calc must execute exactly one project.analysis.calculate() facade call'
    tree_matches = _tree_bytes(edi_project) == _tree_bytes(crysta_project)
    record_matches = _without_elapsed(captured.out) == _without_elapsed(reference.stdout)
    assert code == 0 and tree_matches and record_matches, (
        ' the CLI still calls the facade exactly once, while later non-UI reads '
        'lazily calculate the same reference tree and machine record even if that call '
        f'was suppressed (exit={code}, tree_matches={tree_matches}, '
        f'record_matches={record_matches})'
    )
