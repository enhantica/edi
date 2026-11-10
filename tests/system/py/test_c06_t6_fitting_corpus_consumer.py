from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from conftest import corpus_case_dir, crysta_reference_prefix, crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / 'tests'
RECORDED_SHA = ROOT / 'build/crysta-src/CRYSTA_SOURCE_SHA'
WORKED_REGRESSION_PIN = 19.87006107
EDI_SIDES = {'both', 'edi-only'}
EMPTY_SUBJECT_ID = 'no-edi-side-case-at-pin'


def _runner() -> Path:
    candidates: list[Path] = []
    for path in sorted(TESTS.rglob('test_*.py')):
        if path.resolve() == Path(__file__).resolve() or TESTS / 'unit' in path.parents:
            continue
        text = path.read_text(encoding='utf-8')
        if (
            'manifest.yml' in text
            and 'pytest' in text
            and 'test_fitting_case_matches_expected_through_edi' in text
        ):
            candidates.append(path)
    assert len(candidates) == 1, (
        'edi must have one visible fitting runner derived from the crysta manifest; '
        f'found {[str(path.relative_to(ROOT)) for path in candidates]}'
    )
    return candidates[0]


def _override_name(runner: Path) -> str:
    text = runner.read_text(encoding='utf-8')
    names = {
        token
        for token in re.findall(r"['\"]([A-Z][A-Z0-9_]+)['\"]", text)
        if ('CORPUS' in token or 'FITTING' in token) and ('ROOT' in token or 'DIR' in token)
    }
    assert len(names) == 1, f'runner must expose one explicit corpus-root override, found {names}'
    return next(iter(names))


def _run_collection(runner: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            '--collect-only',
            '-q',
            '-p',
            'no:cacheprovider',
            '-o',
            'addopts=',
            str(runner.relative_to(ROOT)),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def _case(case_id: str, sides: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        'id': case_id,
        'files': ['project.edi', 'data.dat', 'expected.json', 'provenance.txt'],
        'sides': sides,
    }
    if sides != 'both':
        row['reason'] = 'synthetic collection-side mutation'
    return row


def _write_case(root: Path, case_id: str) -> None:
    case_dir = root / case_id
    case_dir.mkdir()
    (case_dir / 'project.edi').write_text('synthetic collection fixture\n', encoding='utf-8')
    (case_dir / 'data.dat').write_text('0 0\n', encoding='utf-8')
    (case_dir / 'provenance.txt').write_text(
        ' synthetic runner-collection fixture; not a correctness reference.\n',
        encoding='utf-8',
    )
    # This is explicitly a regression pin used only to exercise the non-trivial conversion seam.
    expected = {
        'schema': 1,
        'source': {
            'engine': 'synthetic-regression-pin',
            'artifact': 'data.dat',
            'provenance': 'provenance.txt',
        },
        'quantities': {
            'reduced_chi2': {
                'value': WORKED_REGRESSION_PIN,
                'kind': 'regression-pin',
                'tol_abs': 1e-8,
                'tol_rel': None,
            }
        },
    }
    (case_dir / 'expected.json').write_text(
        json.dumps(expected),
        encoding='utf-8',
    )


def _write_corpus(root: Path) -> dict[str, str]:
    ids = {
        'both': '-both-mutation',
        'crysta-only': '-crysta-only-mutation',
        'edi-only': '-edi-only-mutation',
    }
    root.mkdir(parents=True)
    for case_id in ids.values():
        _write_case(root, case_id)
    manifest = {'schema': 1, 'cases': [_case(case_id, side) for side, case_id in ids.items()]}
    (root / 'manifest.yml').write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
    (root / 'retired-tests.yml').write_text('schema: 1\nretired: []\n', encoding='utf-8')
    return ids


def test_c06_t6_edi_runner_collection_is_the_manifest_projection(tmp_path: Path) -> None:
    runner = _runner()
    override = _override_name(runner)
    corpus = tmp_path / 'fitting'
    ids = _write_corpus(corpus)
    env = os.environ.copy()
    env[override] = str(corpus)
    result = _run_collection(runner, env)
    assert result.returncode == 0, _output(result)
    collected = _output(result)
    assert ids['both'] in collected
    assert ids['edi-only'] in collected
    assert ids['crysta-only'] not in collected


# : split — each fail-closed probe carries its own single collection spawn
# (~0.7-0.9 s against the 1.0 s bound); the assertions per probe are unchanged and their
# union is the original claim.
def test_c06_t6_edi_runner_fails_closed_on_a_missing_manifest(tmp_path: Path) -> None:
    runner = _runner()
    override = _override_name(runner)
    missing = tmp_path / 'missing-manifest'
    missing.mkdir()
    override_env = os.environ.copy()
    override_env[override] = str(missing)
    missing_result = _run_collection(runner, override_env)
    assert missing_result.returncode != 0, 'the working-tree override must never skip'
    assert '1 skipped' not in _output(missing_result).lower()


def test_c06_t6_edi_runner_fails_closed_on_broken_totality(tmp_path: Path) -> None:
    runner = _runner()
    override = _override_name(runner)
    malformed = tmp_path / 'malformed-totality'
    _write_corpus(malformed)
    (malformed / 'unlisted-case').mkdir()
    override_env = os.environ.copy()
    override_env[override] = str(malformed)
    malformed_result = _run_collection(runner, override_env)
    assert malformed_result.returncode != 0, 'a manifest-bearing root must enforce full totality'
    assert _output(malformed_result).strip()


def test_c06_t6_edi_runner_collects_the_pinned_edi_side() -> None:
    runner = _runner()
    override = _override_name(runner)
    own_pin_env = os.environ.copy()
    own_pin_env.pop(override, None)
    pin_result = _run_collection(runner, own_pin_env)
    output = _output(pin_result).lower()
    # Exactly 0: the runner always collects at this branch (the transition guard plus one unit),
    # so 5 — pytest's "collected nothing" — is not a legal outcome here. Admitting it let a
    # collected-nothing run walk past this assertion and reach the id check below.
    assert pin_result.returncode == 0, output
    # The  named transition is now closed: the current crysta pin carries the corpus, so
    # native collection must exercise it rather than preserve the historical skip projection.
    recorded_sha = (crysta_reference_prefix() / '.crysta-sha').read_text().strip()
    assert re.fullmatch(r'[0-9a-f]{40}', recorded_sha), (
        'the corpus consumer must identify its recorded crysta source with a full commit sha'
    )
    assert 'corpus not present at recorded crysta source' not in output, (
        'the recorded crysta source must expose the corpus rather than silently skip collection'
    )
    # Vocabulary-agnostic ON PURPOSE: this branch collects against the recorded crysta source,
    # whose corpus is whatever crysta main carried for this run. Hardcoding a case id is wrong
    # across source advances. Assert instead that the recorded corpus's OWN manifest is what got
    # collected.
    recorded_manifest = crysta_reference_source() / 'tests/fitting/manifest.yml'
    cases = yaml.safe_load(recorded_manifest.read_text(encoding='utf-8'))['cases']
    assert cases, 'the recorded checkout must carry a corpus manifest'
    # The runner's subject is the EDI SIDE of the recorded corpus, never the whole of it: a
    # `crysta-only` case is not edi's to collect. `any(id in output)` was the wrong shape twice
    # over - it passed on a single incidental match, and once owner ruling 65 replaced the corpus
    # with eight `crysta-only` cases it had nothing true left to match at all. Assert the exact
    # correspondence, so an id that appears without being declared fails as loudly as one that
    # goes missing.
    edi_side = {
        str(case['id']).lower()
        for case in cases
        if str(case['sides']) in EDI_SIDES
        or any(
            str(variant.get('sides', case['sides'])) in EDI_SIDES
            for variant in case.get('variants') or []
        )
    }
    collected = {
        node.split('::')[0]
        for node in re.findall(
            r'test_fitting_case_matches_expected_through_edi\[([^\]]+)\]', output
        )
    }
    if edi_side:
        assert collected == edi_side, (
            f'collected {sorted(collected)} but the recorded source declares edi-side '
            f'{sorted(edi_side)}'
        )
        assert 'skip' not in output
    else:
        # An empty subject means edi exercises ZERO corpus cases through its own entry point.
        # That is a COVERAGE HOLE, not a pass, and it is not edi's to wave through: crysta's
        # manifest header defines `sides` as "which entry points exercise the case (crysta CLI /
        # edi API)", and edi's own suite loads five of these eight cases by name through the edi
        # API. So either the pinned manifest is wrong (a crysta-side change) or the emptiness is
        # a deliberate disposition - and until committed state says which, this REFUSES rather
        # than reporting green over nothing.
        record = json.loads(
            (TESTS / 'system/fixtures/c11_t41_ruling65/retired_coverage.json').read_text(
                encoding='utf-8'
            )
        )
        assert record.get('edi_side_subject_empty_at_pin'), (
            'the recorded corpus declares no edi-side case, so this runner has no subject at all. '
            'crysta `tests/fitting/manifest.yml` marks all 8 cases `sides: crysta-only` with a '
            'reason about P0.5 SELECTION, which does not speak to entry points - while edi loads '
            'ncaf-wish-3bank-s5, si-sepd-s2, cosio-d20-s1, lbco-hrpt-s2 and si-sepd-s5 through '
            'its own API. Resolve it in committed state, not here: either crysta declares those '
            'cases edi-side, or `retired_coverage.json` declares this emptiness deliberate under '
            'a ruling (key `edi_side_subject_empty_at_pin`, with its reason).'
        )
        # Declared - so hold the SHAPE too: a named unit, never pytest's `[notset]` placeholder
        # standing in for coverage as one silently skipped test.
        assert collected == {EMPTY_SUBJECT_ID}, (
            f'the recorded source declares no edi-side case, so the runner must collect the named '
            f'{EMPTY_SUBJECT_ID!r} unit; collected {sorted(collected)}'
        )
        assert 'notset' not in output, 'an empty parametrisation is a silent skip, not a subject'


def test_c06_t6_edi_runner_maps_the_nontrivial_value_without_an_inline_pin() -> None:
    runner = _runner()
    text = runner.read_text(encoding='utf-8')
    assert 'reduced_chi2' in text, 'the API accessor table must map the worked quantity'
    assert 'float(' in text, 'expected and actual values must be compared numerically'
    assert str(WORKED_REGRESSION_PIN) not in text, (
        'the runner must read the value from expected.json, not duplicate a correctness list'
    )


def test_c06_t6_case_resolver_uses_override_and_requires_the_requested_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = tmp_path / 'fitting'
    ids = _write_corpus(corpus)
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(corpus))

    assert corpus_case_dir(ids['both']) == corpus / ids['both']
    with pytest.raises(AssertionError, match="has no case 'missing-case'"):
        corpus_case_dir('missing-case')


def test_c06_t6_case_resolver_fails_closed_for_an_invalid_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / 'working-tree-override'
    override.mkdir()
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(override))

    with pytest.raises(AssertionError, match='names no fitting corpus'):
        corpus_case_dir('ncaf-wish-3bank-s5')
