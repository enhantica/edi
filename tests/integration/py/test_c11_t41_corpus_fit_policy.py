"""Corpus-source refusal probes for integration/system fit policy."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import edi
import pytest

OBSERVABLE_ENTRYPOINT_ERRORS = (TypeError, ValueError, RuntimeError, OSError, AssertionError)


@pytest.mark.parametrize(
    'operation',
    [
        lambda: getattr(edi.Project, 'f' + 'it')(None),
        lambda: subprocess.run(
            [sys.executable, '-m', 'edi', 'f' + 'it', 'does-not-resolve-from-the-corpus'],
            check=False,
            capture_output=True,
            text=True,
        ),
    ],
    ids=('python', 'cli'),
)
def test_c11_t41_integration_fit_without_a_corpus_project_is_refused_before_validation(
    operation: Callable[[], object],
) -> None:
    with pytest.raises(OBSERVABLE_ENTRYPOINT_ERRORS) as caught:
        operation()
    assert type(caught.value).__name__ == 'FitPolicyViolation'
    assert 'corpus' in str(caught.value).lower()


def test_c11_t41_declared_corpus_origin_reaches_product_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The outer policy must not hide validation once corpus authority admits the call."""
    root = tmp_path / 'fitting'
    case = root / 'declared-fit-policy-control'
    project_path = case / 'project'
    source = Path(__file__).resolve().parents[2] / 'fixtures/e02_t2_ncaf_5bank/project'
    shutil.copytree(source, project_path)
    manifest = root / 'manifest.yml'
    declared = 'cases:\n  - id: declared-fit-policy-control\n'
    manifest.write_text(declared, encoding='utf-8')
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(root))

    project = edi.Project.load(project_path)

    with pytest.raises(TypeError) as admitted:
        project.fit(c11_t41_invalid_argument=True)
    assert type(admitted.value).__name__ != 'FitPolicyViolation'

    manifest.unlink()
    with pytest.raises(OBSERVABLE_ENTRYPOINT_ERRORS) as no_authority:
        project.fit(c11_t41_invalid_argument=True)
    assert type(no_authority.value).__name__ == 'FitPolicyViolation'
    assert 'corpus' in str(no_authority.value).lower()

    manifest.write_text(declared, encoding='utf-8')
    with pytest.raises(TypeError) as authority_restored:
        project.fit(c11_t41_invalid_argument=True)
    assert type(authority_restored.value).__name__ != 'FitPolicyViolation'

    manifest.write_text('cases: []\n', encoding='utf-8')
    with pytest.raises((TypeError, ValueError, RuntimeError, OSError, AssertionError)) as refused:
        project.fit(c11_t41_invalid_argument=True)
    assert type(refused.value).__name__ == 'FitPolicyViolation'

    manifest.write_text(declared, encoding='utf-8')
    with pytest.raises(TypeError) as restored:
        project.fit(c11_t41_invalid_argument=True)
    assert type(restored.value).__name__ != 'FitPolicyViolation'


# --- I20 admission discrimination (review-21 F3) -----------------------------------------------
#
# review-19 narrowed I20 so a STAGED project is admitted only when its data AND its analysis come
# from one corpus case. That narrowing shipped with ad-hoc mutation results in a ledger row rather
# than a committed gate, which is what F3 refused: a bound nobody re-checks is not a bound. These
# assert the DISCRIMINATION directly on the predicate — every axis the reviewer named.


def _corpus_root() -> Path:
    # conftest is not importable at module scope from this tier.
    from conftest import corpus_case_dir  # noqa: PLC0415

    return corpus_case_dir('ncaf-wish-3bank-s5').parent


def _stage(
    destination: Path,
    case: Path,
    *,
    analysis: dict[str, bytes] | None,
    data_from: Path | None = None,
) -> Path:
    """A project whose data symlinks into `case` (or `data_from`) and whose analysis is written."""
    staged = destination / 'staged-project'
    staged.mkdir(parents=True)
    source = data_from or case
    for child in ('experiments', 'structures'):
        (staged / child).symlink_to(source / 'project' / child, target_is_directory=True)
    if analysis is not None:
        (staged / 'analysis').mkdir()
        for name, payload in analysis.items():
            (staged / 'analysis' / name).write_bytes(payload)
    return staged


def _variant(case: Path, name: str) -> dict[str, bytes]:
    directory = case / 'project' / 'analysis' if name == 'canonical' else case / name
    return {path.name: path.read_bytes() for path in sorted(directory.glob('*.edi'))}


def test_i20_admits_only_a_declared_project_not_any_path_inside_a_case() -> None:
    """A case declares ONE project; `<case>/fullprof` and friends are not it (review-21 F3)."""
    from tools.testing import fit_policy  # noqa: PLC0415 - import inside the corpus-dependent test

    case = _corpus_root() / 'ncaf-wish-3bank-s5'
    assert fit_policy._is_corpus(str(case / 'project')) is True
    for sibling in ('fullprof', 'goldens', 'bounded-analysis'):
        if (case / sibling).is_dir():
            assert fit_policy._is_corpus(str(case / sibling)) is False, sibling
    assert fit_policy._is_corpus(str(case)) is False


def test_i20_staged_analysis_must_equal_one_complete_declared_variant(tmp_path: Path) -> None:
    """Positive, foreign, invented, missing, extra, mixed-variant — every F3 axis."""
    from tools.testing import fit_policy  # noqa: PLC0415 - import inside the corpus-dependent test

    root = _corpus_root()
    case = root / 'ncaf-wish-3bank-s5'
    other = root / 'cosio-d20-s1'
    canonical = _variant(case, 'canonical')
    bounded = _variant(case, 'bounded-analysis')
    foreign = _variant(other, 'canonical')

    # positive: each COMPLETE declared variant is admitted
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'a', case, analysis=canonical))) is True
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'b', case, analysis=bounded))) is True

    # foreign: another case's analysis over this case's data
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'c', case, analysis=foreign))) is False

    # invented
    invented = {'analysis.edi': b'_minimizer.max_iterations 1\n'}
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'd', case, analysis=invented))) is False

    # missing: no analysis directory at all
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'e', case, analysis=None))) is False

    # extra: a complete declared variant PLUS one invented document
    assert (
        fit_policy._is_corpus(
            str(_stage(tmp_path / 'f', case, analysis={**bounded, 'invented.edi': b'_x.y 1\n'}))
        )
        is False
    )


def _synthetic_corpus(root: Path) -> Path:
    """A corpus whose case declares TWO MULTI-FILE analysis variants.

    The real corpus cannot express `subset` or `mixed-variant`: every declared variant of
    `ncaf-wish-3bank-s5` holds a single file with the same name, so any single-file staging is
    either one whole variant or foreign. Guarding those axes behind `if` and skipping them is the
    silent-skip pattern, so the distinction is CONSTRUCTED here instead of quietly dropped.
    """
    case = root / 'synth-case'
    (case / 'project' / 'experiments').mkdir(parents=True)
    (case / 'project' / 'structures').mkdir(parents=True)
    (case / 'project' / 'experiments' / 'e.edi').write_bytes(b'_expt.x 1\n')
    (case / 'project' / 'structures' / 's.edi').write_bytes(b'_struct.x 1\n')
    (case / 'project' / 'analysis').mkdir()
    (case / 'project' / 'analysis' / 'a.edi').write_bytes(b'CANON-A\n')
    (case / 'project' / 'analysis' / 'b.edi').write_bytes(b'CANON-B\n')
    (case / 'bounded-analysis').mkdir()
    (case / 'bounded-analysis' / 'a.edi').write_bytes(b'BOUND-A\n')
    (case / 'bounded-analysis' / 'c.edi').write_bytes(b'BOUND-C\n')
    (root / 'manifest.yml').write_text('schema: 1\ncases:\n  - id: synth-case\n', encoding='utf-8')
    return case


def test_i20_subset_and_mixed_variant_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The axes the real corpus cannot express: every byte declared, yet matching NO variant.

    This is the discrimination that separates "equals one declared variant" from the pooled
    "occurs somewhere among the declared documents" rule review-21 F3 refused. Both stagings
    below are built ENTIRELY from declared bytes, so a pooled check admits them.
    """
    from tools.testing import fit_policy  # noqa: PLC0415 - import inside the corpus-dependent test

    root = tmp_path / 'corpus'
    root.mkdir()
    case = _synthetic_corpus(root)
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(root))

    canonical = {'a.edi': b'CANON-A\n', 'b.edi': b'CANON-B\n'}
    bounded = {'a.edi': b'BOUND-A\n', 'c.edi': b'BOUND-C\n'}

    # positive control: each complete variant is admitted
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'p1', case, analysis=canonical))) is True
    assert fit_policy._is_corpus(str(_stage(tmp_path / 'p2', case, analysis=bounded))) is True

    # SUBSET — one document of a declared variant; every byte is declared
    assert (
        fit_policy._is_corpus(str(_stage(tmp_path / 's1', case, analysis={'a.edi': b'CANON-A\n'})))
        is False
    )

    # MIXED-VARIANT — one document from each variant; every byte is declared, matches neither
    assert (
        fit_policy._is_corpus(
            str(
                _stage(
                    tmp_path / 'm1', case, analysis={'a.edi': b'CANON-A\n', 'c.edi': b'BOUND-C\n'}
                )
            )
        )
        is False
    )

    # ARBITRARY-IN-CASE-PATH — a directory inside the case is not its declared project
    assert fit_policy._is_corpus(str(case / 'bounded-analysis')) is False
    assert fit_policy._is_corpus(str(case)) is False


def test_i20_staged_data_must_come_from_one_case(tmp_path: Path) -> None:
    """Data spanning two cases is refused however good the analysis is."""
    from tools.testing import fit_policy  # noqa: PLC0415 - import inside the corpus-dependent test

    root = _corpus_root()
    case = root / 'ncaf-wish-3bank-s5'
    other = root / 'cosio-d20-s1'
    staged = tmp_path / 'mixed'
    staged.mkdir()
    project = staged / 'staged-project'
    project.mkdir()
    (project / 'experiments').symlink_to(
        case / 'project' / 'experiments', target_is_directory=True
    )
    (project / 'structures').symlink_to(other / 'project' / 'structures', target_is_directory=True)
    (project / 'analysis').mkdir()
    for name, payload in _variant(case, 'canonical').items():
        (project / 'analysis' / name).write_bytes(payload)
    assert fit_policy._is_corpus(str(project)) is False


def test_i20_refuses_without_a_resolvable_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Losing the authority that proves membership is a refusal, never a licence."""
    from tools.testing import fit_policy  # noqa: PLC0415 - import inside the corpus-dependent test

    # Resolve the real project FIRST: once the override names no corpus, the resolver itself
    # refuses, and the point here is that the POLICY refuses a previously-admitted origin.
    project = _corpus_root() / 'ncaf-wish-3bank-s5' / 'project'
    assert fit_policy._is_corpus(str(project)) is True
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(Path('/nonexistent-corpus-root')))
    assert fit_policy._is_corpus(str(project)) is False
    assert fit_policy._is_corpus(None) is False
