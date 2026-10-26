"""Regression pins preserve main's saved bytes when all input flags are fittable."""

import importlib
import json
from pathlib import Path

import pytest

from tests.fixtures.fittability.saved_reference import fit_snapshot, snapshot

ROOT = Path(__file__).resolve().parents[3]
API = 'edi'
REFERENCE = json.loads((ROOT / 'tests/fixtures/fittability/saved-main.json').read_text())


@pytest.mark.parametrize('case', tuple(REFERENCE['projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_saved_bytes_regression_pin(tmp_path, case, rule):
    actual = snapshot(importlib.import_module(API), ROOT / case, tmp_path, rule)
    assert actual == REFERENCE['projects'][case][rule], (
        'The fit-policy change preserves every saved path and byte under both s.u. rules; '
        'only wall-clock fields are normalized: ' + case + ' / ' + rule
    )


@pytest.mark.parametrize('case', tuple(REFERENCE['fit_projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_fitted_descriptor_bytes_regression_pin(tmp_path, case, rule):
    actual = fit_snapshot(importlib.import_module(API), ROOT / case, tmp_path, rule)
    assert actual == REFERENCE['fit_projects'][case][rule], (
        'A fitted constrained crystal radius keeps main saved bytes '
        'and its propagated s.u. under both rules'
    )
