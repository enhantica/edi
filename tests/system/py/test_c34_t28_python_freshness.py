"""I23: held and saved freshness matches labelled pre-move observations."""

import json
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_baseline import generate_bytes as byte_reference
from tests.fixtures.c34_t28_baseline import generate_freshness as reference

ROOT = Path(__file__).resolve().parents[3]
BASELINE = json.loads((reference.HERE / 'freshness.json').read_text())


def test_python_freshness_inputs_and_route_inventory_stay_bound(tmp_path, monkeypatch):
    committed = reference.corpus_root(ROOT)
    # A prior fit may persist different values into the session scratch. It
    # cannot become the input oracle or the vehicle for these regression pins.
    scratch = tmp_path / 'mutated-corpus'
    scratch.mkdir()
    with monkeypatch.context() as isolated:
        isolated.setenv('EDI_CRYSTA_CORPUS_ROOT', str(scratch))
        assert reference.corpus_root(ROOT) == committed, (
            ' I23 persisted session scratch cannot replace committed freshness inputs'
        )
    assert BASELINE['source_commit'] == reference.BASE, (
        ' I23 Python freshness uses the named pre-move build'
    )
    assert set(BASELINE['routes']) == set(reference.ROUTES), (
        ' I23 every represented Python write route retains its baseline observation'
    )
    assert reference.hashes(reference.HERE / 'freshness-input') == BASELINE['input_sha256'], (
        ' I23 the controlled input bytes cannot drift beneath the observation'
    )
    single = reference.corpus_root(ROOT) / 'cosio-d20-s1/project'
    # Before: raw fit input hash. After : only the declared calculator
    # seed is reversed; every fit/undo input byte still meets the immutable pin.
    assert (
        byte_reference.legacy_input_hashes(single, 'corpus:cosio-d20-s1/project')
        == BASELINE['fit_sha256']
    ), ' I23 fit and undo inputs retain the complete committed corpus case'
    scan = reference.corpus_root(ROOT) / 'cosio-d20-scan-3f/project'
    assert reference.input_hashes(scan) == BASELINE['scan_sha256'], (
        ' I23 every sequential input, including each data frame, stays pinned'
    )


@pytest.mark.parametrize('route', [r for r in reference.ROUTES if r != 'sequential'])
def test_python_write_keeps_the_pre_move_freshness_regression_pin(tmp_path, route):
    observed = reference.observe(route, tmp_path / route, ROOT)
    assert observed == BASELINE['routes'][route], (
        ' I23 a Python write preserves the exact old geometry and pattern renewal: ' + route
    )
