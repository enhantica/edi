"""Manifest-declared FullProf loader behavior for future corpus verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

import edi
import pytest
from edi import verification

from conftest import corpus_case_dir
from tests.model_calculation import calculate_on_grid


def test_corpus_fullprof_loader_follows_manifest_hash_not_directory_order(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / 'fitting'
    case = corpus / 'synthetic-tof'
    fullprof = case / 'fullprof'
    fullprof.mkdir(parents=True)
    canonical = b'TOF Iobs Icalc Diff\n1000 0 3.25 0\n2000 0 7.5 0\n'
    (fullprof / 'a-decoy.prf').write_bytes(b'TOF Iobs Icalc Diff\n1000 0 99 0\n2000 0 101 0\n')
    (fullprof / 'z-canonical.prf').write_bytes(canonical)
    digest = hashlib.sha256(canonical).hexdigest()
    (corpus / 'manifest.yml').write_text(
        'schema: 1\n'
        'cases:\n'
        '  - id: synthetic-tof\n'
        '    files:\n'
        '      - fullprof/a-decoy.prf\n'
        '      - fullprof/z-canonical.prf\n'
        '    fullprof:\n'
        '      path: fullprof\n'
        "      fp2k_version: '8.40'\n"
        "      rerun_command: 'not run by tests'\n"
        f'      prf_sha256: {digest}\n'
        '    sides: both\n',
        encoding='utf-8',
    )

    tof, reference = verification.load_corpus_fullprof_profile(case)
    assert tof == pytest.approx([1000.0, 2000.0])
    assert reference == pytest.approx([3.25, 7.5])


def test_e02_fitted_corpus_project_agrees_with_independent_fullprof_profile() -> None:
    """The verification gate carries a live physics signal, not only loader shape."""
    case = corpus_case_dir('si-sepd-s5')
    axis, fullprof = verification.load_corpus_fullprof_profile(case)
    project = edi.Project.load(case / 'project')

    outcome = project.fit()
    assert outcome.status == edi.FitStatus.DONE
    assert outcome.converged

    candidate = calculate_on_grid(edi, project, axis)
    assert verification.assert_patterns_agree([
        ('edi-crysta fitted corpus project vs FullProf 8.40', fullprof, candidate),
    ])
