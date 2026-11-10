# SPDX-License-Identifier: BSD-3-Clause
"""Fixture-cost instrumentation for the per-PR measurement.

A module-scoped fixture's cost is per *module*, but the runtime manifest is per *test* — so the
cost lands on whichever test in the module happens to run first, and marking that test ``heavy``
only moves the cost to the next non-heavy sibling (the measured defect: edi's per-PR tier at
661.3 s against the 305.8 s its per-test manifest predicted, a ~338 s gap from one fixture).

This plugin is the honest instrument for that cost: loaded only by ``tools/ci/per-pr-measure.sh``
(``-p fixture_costs`` with ``tools/checks`` on ``PYTHONPATH``), it times every fixture setup and
accumulates the module-scoped ones per module, then writes ``{module_nodeid: seconds}`` to the
JSON file named by ``EDI_FIXTURE_COST_LOG``. ``per_pr_runtimes.py --update`` folds that file into
``module:`` rows in the manifest, and ``tests/conftest.py`` marks every test of a module heavy
when the module's recorded fixture cost meets the threshold — the granularity at which the cost
is actually paid. Ordinary runs never load this plugin and are unaffected.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureDef, SubRequest

ENV_VAR = 'EDI_FIXTURE_COST_LOG'

_module_costs: dict[str, float] = {}

# ⛔ The EXPLICIT completed-node set. Without it the updater cannot tell "ran and finished below
# the reporting floor" from "never reached because the run stopped early", and it resolved that
# ambiguity by writing 0.0 — turning every unreached node into the fastest possible measured
# test. A node is complete only once its teardown reports, so this is recorded there.
_completed: set[str] = set()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Record a node as COMPLETE when its teardown phase reports; that is the whole run."""
    if report.when == 'teardown':
        _completed.add(report.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(
    fixturedef: FixtureDef,
    request: SubRequest,
) -> Generator[None, None, None]:
    """Time each fixture setup; accumulate module-scoped cost per module."""
    start = time.perf_counter()
    yield
    if fixturedef.scope == 'module':
        # For a module-scoped fixture, ``request.node`` is the Module collector, whose
        # nodeid is the manifest's module spelling (e.g. ``tests/x/test_y.py``).
        nodeid = getattr(request.node, 'nodeid', '')
        if nodeid:
            elapsed = time.perf_counter() - start
            _module_costs[nodeid] = _module_costs.get(nodeid, 0.0) + elapsed


def pytest_sessionfinish(
    session: pytest.Session,  # noqa: ARG001
    exitstatus: int,  # noqa: ARG001
) -> None:
    """Write module costs AND the completed-node set to ``EDI_FIXTURE_COST_LOG``."""
    target = os.environ.get(ENV_VAR)
    if target:
        Path(target).write_text(
            json.dumps(
                {'module_costs': _module_costs, 'completed': sorted(_completed)},
                indent=1,
                sort_keys=True,
            ),
            encoding='utf-8',
        )
