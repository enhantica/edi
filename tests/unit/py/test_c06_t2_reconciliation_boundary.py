"""The fixture-cost containment boundary (, review-3 B4).

A recorded module fixture cost reconciles to a duration log only if the log's largest setup
phase can actually CONTAIN it. The sole admissible slack is the log's display resolution
(pytest's ``--durations`` prints two decimals, so a displayed setup understates its true
value by at most half an ulp of that display) — never a percentage of runtime, which left a
5 % acceptance window at exactly the boundary review-3 named. These cases sit on both sides
of that bound, include the review's own 96 s/100 s example, and prove the accepted path's
zero-floor can absorb only sub-resolution noise rather than hide a real mismatch.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_AUDIT = Path(__file__).resolve().parents[3] / 'tools' / 'checks' / 'per_pr_runtimes.py'
_spec = importlib.util.spec_from_file_location('edi_per_pr_runtimes_boundary', _AUDIT)
_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit)

MODULE = 'tests/x/test_mod.py'
TRIGGER = f'{MODULE}::test_first'
SLACK = _audit._CONTAINMENT_SLACK


def _reconcile(displayed_setup: float, cost: float) -> tuple[list[str], float]:
    runtimes = {TRIGGER: displayed_setup + 0.5}  # setup + own call time
    failures = _audit.separate_module_costs(runtimes, {MODULE: cost}, {TRIGGER: displayed_setup})
    return failures, runtimes[TRIGGER]


def test_c06_t2_cost_beyond_display_resolution_refuses():
    failures, runtime = _reconcile(96.00, 96.00 + SLACK + 0.001)
    assert len(failures) == 1 and 'cannot contain' in failures[0]
    assert runtime == 96.50  # untouched: an irreconcilable cost is never subtracted


def test_c06_t2_reviewers_five_percent_window_is_closed():
    # 96 s setup / 100 s cost passed the retired `cost * 0.95` window; it must refuse.
    failures, runtime = _reconcile(96.00, 100.00)
    assert len(failures) == 1 and 'cannot contain' in failures[0]
    assert runtime == 96.50


def test_c06_t2_cost_within_display_resolution_reconciles():
    failures, runtime = _reconcile(96.00, 96.00 + SLACK - 0.001)
    assert failures == []
    assert abs(runtime - (96.50 - (96.00 + SLACK - 0.001))) < 1e-9


def test_c06_t2_zero_floor_absorbs_at_most_sub_resolution_noise():
    # Total exactly the displayed setup, cost at the slack edge: the subtraction can dip
    # below zero only by the slack itself; the floor returns 0.0 and nothing larger is
    # ever hidden (the beyond-slack case above refuses before any subtraction).
    runtimes = {TRIGGER: 96.00}
    failures = _audit.separate_module_costs(runtimes, {MODULE: 96.00 + SLACK}, {TRIGGER: 96.00})
    assert failures == []
    assert runtimes[TRIGGER] == 0.0
