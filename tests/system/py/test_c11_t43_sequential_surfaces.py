""": the edi CLI and Python API reach crysta's sequential writer."""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = Path(
    os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
)
CASE = CORPUS_ROOT / 'cosio-d20-scan-3f'
EXPECTED_FILES = ['all594687.dat', 'all594791.dat', 'all594842.dat']
EXPECTED_TEMPERATURES = [52.345, 299.394, 497.379]
FORBIDDEN_BARE_METRICS = {'success', 'iterations', 'reduced_chi_square'}


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames is not None, f' requires a CSV header in {path}'
        return list(reader.fieldnames), list(reader)


def _tree_digest(root: Path) -> str:
    """Hash every path and byte so any mode-specific dry-run artifact is observable."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, 'big'))
        digest.update(relative)
        if path.is_symlink():
            payload = str(path.readlink()).encode()
            digest.update(b'L' + len(payload).to_bytes(8, 'big') + payload)
        elif path.is_file():
            payload = path.read_bytes()
            digest.update(b'F' + len(payload).to_bytes(8, 'big') + payload)
        else:
            digest.update(b'D')
    return digest.hexdigest()


def _bound_to_one_iteration(project_dir: Path) -> None:
    analysis = project_dir / 'analysis' / 'analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 1000' in text, (
        ' dry-run control requires the corpus iteration declaration'
    )
    analysis.write_text(
        text.replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'),
        encoding='utf-8',
    )


def _write_partial_results(project_dir: Path) -> None:
    reference = CASE / 'diffraction-lib' / 'project' / 'analysis' / 'results.csv'
    header, descending = _rows(reference)
    csv_path = project_dir / 'analysis' / 'results.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerow(descending[-1])


@pytest.mark.parametrize('state', ['fresh', 'partial'])
def test_cli_dry_is_byte_identical_across_every_pre_persistence_writer(
    tmp_path: Path, state: str
) -> None:
    """A whole-tree digest closes current and future mode-specific artifact writers."""
    project_dir = tmp_path / state
    shutil.copytree(CASE / 'project', project_dir)
    _bound_to_one_iteration(project_dir)
    if state == 'partial':
        _write_partial_results(project_dir)
    before = _tree_digest(project_dir)

    completed = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(project_dir),
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            'off',
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1'},
    )
    assert completed.returncode == 0, (
        ' dry sequential fit must still compute successfully; '
        f'state={state}, stderr={completed.stderr[-500:]!r}'
    )
    assert _tree_digest(project_dir) == before, (
        ' --dry promises a byte-identical project tree across every refinement path '
        f'that can write before the shared persistence decision; state={state}'
    )


def test_cli_fit_and_python_resume_share_crysta_results_writer(tmp_path: Path) -> None:
    assert CASE.is_dir(), (
        f' requires the declared crysta corpus case at {CASE}; the edi gate never '
        'substitutes locally generated scan data'
    )
    project_dir = tmp_path / 'project'
    shutil.copytree(CASE / 'project', project_dir)

    command = [
        sys.executable,
        '-m',
        'edi',
        'fit',
        str(project_dir),
        '--report',
        'machine',
        '--verbosity',
        'off',
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1'},
    )
    assert completed.returncode == 0, (
        ' requires `python -m edi fit` to run the sequential project successfully; '
        f'rc={completed.returncode}, stdout tail={completed.stdout[-500:]!r}, '
        f'stderr tail={completed.stderr[-500:]!r}'
    )

    csv_path = project_dir / 'analysis' / 'results.csv'
    header, rows = _rows(csv_path)
    reference_header, _ = _rows(CASE / 'diffraction-lib' / 'project' / 'analysis' / 'results.csv')
    assert set(header) == set(reference_header), (
        " requires the edi CLI surface to emit diffraction-lib's exact column set; "
        f'missing={sorted(set(reference_header) - set(header))!r}, '
        f'extra={sorted(set(header) - set(reference_header))!r}'
    )
    assert not (FORBIDDEN_BARE_METRICS & set(header)), (
        ' requires bare success/iterations/reduced_chi_square columns to remain absent '
        'through the edi CLI surface'
    )
    assert [Path(row['file_path']).name for row in rows] == EXPECTED_FILES, (
        ' requires the edi CLI surface to preserve default ascending scan order and '
        'one row per file'
    )
    assert [float(row['diffrn.ambient_temperature']) for row in rows] == EXPECTED_TEMPERATURES, (
        ' requires the edi CLI surface to preserve the three data-file temperatures'
    )
    assert all(row['fit_result.success'] == 'True' for row in rows), (
        ' requires the edi CLI surface to expose one successful fit result per file'
    )

    before_resume = csv_path.read_bytes()
    project = edi.Project.load(project_dir)
    outcome = project.analysis.fit()
    assert outcome is not None, (
        ' requires edi Python Analysis.fit() to return a result on completed-scan resume'
    )
    assert csv_path.read_bytes() == before_resume, (
        ' requires the edi Python surface to resume the CLI-completed scan with zero '
        'additional rows and no second writer output'
    )
