"""Regression pins preserve main's saved bytes when all input flags are fittable."""

import hashlib
import importlib
import json
import warnings
from pathlib import Path

import pytest

from tests.fixtures.fittability.saved_reference import fingerprints, fit_snapshot, snapshot, staged

ROOT = Path(__file__).resolve().parents[3]
API = 'edi'
REFERENCE = json.loads((ROOT / 'tests/fixtures/fittability/saved-main.json').read_text())


@pytest.mark.parametrize('case', tuple(REFERENCE['projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_saved_bytes_regression_pin(tmp_path, case, rule):
    api = importlib.import_module(API)
    if case == 'tests/fixtures/e04_t1/reference/unused-free':
        with warnings.catch_warnings(record=True) as notes:
            warnings.simplefilter('always')
            project = api.Project.load(staged(ROOT / case, tmp_path / 'input', rule))
        assert (
            sum(
                'unfittable_free_ignored' in str(note.message)
                and 'broad_lorentz_gamma_1' in str(note.message)
                and "this fit's data cannot determine it" in str(note.message)
                for note in notes
            )
            == 1
        ), 'The unused free input emits exactly one coded not-measured note'
        project.save_as(tmp_path / 'saved')
        actual = fingerprints(tmp_path / 'saved')
        saved = (tmp_path / 'saved/experiments/dream.edi').read_bytes()
        fixed = b'_peak.broad_lorentz_gamma_1 0.1\n'
        assert saved.count(fixed) == 1, (
            'The saved unsupported Lorentzian coefficient has exactly one fixed spelling'
        )
        # Restore only the historical flag in memory to compare every other saved byte to main.
        actual['experiments/dream.edi'] = hashlib.sha256(
            saved.replace(fixed, b'_peak.broad_lorentz_gamma_1 0.1()\n')
        ).hexdigest()
    else:
        actual = snapshot(api, ROOT / case, tmp_path, rule)
    assert actual == REFERENCE['projects'][case][rule], (
        'The fit-policy change preserves every saved path and byte under both s.u. rules; '
        'only clocks and the explicitly checked unsupported-free flag are normalized: '
        + case
        + ' / '
        + rule
    )


@pytest.mark.parametrize('case', tuple(REFERENCE['fit_projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_fitted_descriptor_bytes_regression_pin(tmp_path, case, rule):
    actual = fit_snapshot(importlib.import_module(API), ROOT / case, tmp_path, rule)
    assert actual == REFERENCE['fit_projects'][case][rule], (
        'A fitted constrained crystal radius keeps main saved bytes '
        'and its propagated s.u. under both rules'
    )
