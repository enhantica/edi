"""end-to-end gate for consuming the corrected crysta centring model."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
from conftest import calculator_load_warning, corpus_case_dir  # noqa: E402

REFERENCE_REDUCED_CHI2 = 3.5987206687201705
ACCEPTED_REDUCED_CHI2_BAND = (3.2, 4.0)


def _record(text: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        key, value = line.split('=', maxsplit=1)
        assert key not in rows
        rows[key] = value
    return rows


def test_c09_t13_bare_silicon_fit_reaches_the_reference_quality_band(tmp_path) -> None:
    source = corpus_case_dir('si-sepd-s2') / 'project'
    # Read the declared warning before the saving CLI can change its input.
    expected_warning = calculator_load_warning(source)
    before = {
        p.relative_to(source): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob('*')
        if p.is_file()
    }
    # Both branches' checks use a private fit input; committed bytes stay frozen.
    project = tmp_path / 'project'
    shutil.copytree(source, project)
    completed = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(project),
            '--report',
            'machine',
            '--verbosity',
            'compact',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert {
        p.relative_to(source): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob('*')
        if p.is_file()
    } == before, ' the saving CLI witness must preserve every committed corpus input byte'
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == expected_warning, (
        ' fit stderr contains exactly the declared calculator warning and no other output'
    )
    record = _record(completed.stdout)
    assert record['schema'] == '8', "the  schema requirement must hold: record['schema'] == '8'"
    assert record['record'] == 'fit'
    assert record['status'] == 'done'
    assert record['mode'] == 'single'
    assert record['converged'] == 'true'
    assert int(record['n_points_loaded']) == 5600
    assert int(record['n_points_fitted']) == 5600
    assert int(record['n_free']) == 23
    assert int(record['iterations']) > 0

    reduced_chi_square = float(record['reduced_chi_square'])
    low, high = ACCEPTED_REDUCED_CHI2_BAND
    assert low <= REFERENCE_REDUCED_CHI2 <= high
    assert low <= reduced_chi_square <= high, (
        'the fitted reduced chi-square must remain inside the reference band'
    )
