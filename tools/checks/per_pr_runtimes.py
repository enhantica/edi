#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The measured per-tier runtime audit.

``tests/per-pr-runtimes.tsv`` holds one recorded wall-clock second count per collected test;
the per-tier bounds and the committed breach baseline (``tests/threshold-breaches.md``, a
RATCHET) are what the record enforces. retired the measured runtime split (``heavy``) this
record used to feed: selection now lives in the three named groups
(``tests/test-groups.json``), all equal on test selection, and this audit additionally
REFUSES any marker-based deselection returning to a live config surface.

Two subcommands:

``--check``
    The gate. Asserts the manifest is well-formed, declares a threshold, and covers **every**
    currently collected test, so no test can be silently absent from the audit (an absent test
    would otherwise default to "fast" without anyone having measured it).

``--update FILE --fixture-costs FILE``
    Bank the ADDED nodes' runtimes from one focused serial ``pytest -vv --durations=0`` log (no
    re-measurement when the collected set is unchanged — neither the log nor the artifact is
    read; when the set changes, measure ONCE, only what was added). Every banked row and
    declared hole is kept, rows whose node no longer exists are dropped, and an added node that
    breaches its tier bound without a baseline entry is refused BEFORE anything is written.
    ``--remeasure NODEID`` (repeatable) lets a deliberately re-run node — one whose test was
    optimised — take the log's value, so a fixed breach can leave the ratchet baseline. **The
    artifact is REQUIRED whenever something is measured**: it carries the COMPLETED-NODE SET,
    and without it absence is ambiguous.

    ⛔ NO CODE PATH GIVES AN UNMEASURED NODE A NUMBER. A measured node is recorded ``0.000`` only
    when the artifact PROVES it completed — it then ran below pytest's reporting floor, which is
    what "fast" has to mean here. A node the run never reached is recorded as a declared hole, and
    an entry point that cannot prove completion REFUSES BEFORE WRITING ANYTHING rather than
    defaulting.

``--added-nodes``
    Print the collected nodes with no banked row or hole (what a focused measurement must run);
    empty output means the collection is unchanged and nothing needs measuring.

There is NO aggregate suite budget and NO manifest expiry: banked evidence does not age out.

Why the manifest rather than decorators: the tests that most need tiering live in a hidden suite
whose sources the implementing lane may run but never read or edit, so the assignment has to live
beside the suite instead of inside it. That constraint produced the better design — a decorator
records a *judgement*, this records the *measurement* the judgement is made from, and the gate can
check the two agree.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'tests' / 'per-pr-runtimes.tsv'

_THRESHOLD_RE = re.compile(r'^#\s*threshold_seconds\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$')
# `# tier_threshold_seconds.<tier> = <n>` — one line per tier, validated against
# TIER_THRESHOLDS so the manifest states the contract it is actually governed by.
_TIER_THRESHOLD_RE = re.compile(
    r'^#\s*tier_threshold_seconds\.([a-z/]+)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$'
)
# `12.34s call     tests/x.py::test_y` — pytest's --durations line. `setup`/`call`/`teardown` are
# summed per node: a module-scoped fixture's cost is charged to the test that triggers it, and a
# per-PR budget cares about the total the runner actually spends.
_DURATION_RE = re.compile(r'^([0-9]+\.[0-9]+)s\s+(setup|call|teardown)\s+(\S+)')

# Owner ruling 53/54 (extended to edi): PER-TIER thresholds replace the single global 30 s.
# The global one was inert - nothing here came within 17 s of it - and a bound nothing
# approaches catches nothing, the same "illusion of protection" ruling 52 rejected in a
# full-suite ceiling.
#
# ⛔ EACH BOUND IS JUSTIFIED FROM WHAT THE TIER IS FOR, NEVER CALIBRATED TO TODAY'S MEASUREMENTS.
# A threshold derived from the current distribution ratifies the current cost: it can only be
# breached by getting worse than today, so it can never say today is already too slow. These
# bounds would be identical on an empty repository, and they are the same four crysta carries -
# a shared standard, not a per-repo negotiation.
#
#   unit (py AND cpp) 0.1 s  A unit test exercises one behaviour in memory. The test-pyramid
#                            convention is milliseconds; 0.1 s is already generous. Anything
#                            slower is doing I/O, spawning, or real numerics - another tier's job.
#   integration       1.0 s  Crosses a real boundary (process, file, extension module) but must
#                            stay inside the interactive loop a developer will actually run.
#   system            5.0 s  Spawns a process and exercises an end-to-end contract, so it pays
#                            real startup; still bounded so the tier stays runnable per commit.
#
# edi has no `fitting` tier - it declares no fitting corpus - so that bound simply does not apply
# here. `unit/cpp` is listed separately from `unit/py` even though they share a bound, because
# folding them once already hid that the C++ tier carries almost every unit-tier breach in crysta.
TIER_THRESHOLDS = {
    'unit/py': 0.1,
    'unit/cpp': 0.1,
    'integration': 1.0,
    'system': 5.0,
}


def tier_of(nodeid: str) -> str:
    """Return the tier a node belongs to, by path; unknown paths take the loosest bound."""
    if nodeid.startswith('tests/unit/cpp/'):
        return 'unit/cpp'
    if nodeid.startswith('tests/unit/'):
        return 'unit/py'
    if nodeid.startswith('tests/integration/'):
        return 'integration'
    if nodeid.startswith('tests/system/'):
        return 'system'
    return 'system'


def threshold_for(nodeid: str) -> float:
    """Return the bound this node is held to."""
    return TIER_THRESHOLDS[tier_of(nodeid)]


def thresholds_text() -> str:
    """Render the per-tier bounds for the audit's own summary line."""
    return ' '.join(f'{tier}={bound}s' for tier, bound in TIER_THRESHOLDS.items())


DEFAULT_THRESHOLD_SECONDS = 30.0

# A structured header comment `# module-cost: <seconds>\t<path>` records a MODULE-scoped
# fixture cost — paid once per module by whichever test triggers it, so it cannot be
# expressed per test (excluding one test only moves the cost to the next sibling). It is a
# comment, not a data row, so every consumer that reads the manifest as per-test rows
# (this file's load_manifest included) is unaffected. Since the rows mark and deselect
# NOTHING — they are kept for visibility and the stale-module integrity refusal; selection
# lives in the named groups (tests/test-groups.json).
_MODULE_COST_RE = re.compile(r'^#\s*module-cost:\s*([0-9]+(?:\.[0-9]+)?)\t(\S+)\s*$')

# Review-3 B4: the only defensible slack when comparing an instrumented fixture cost against
# the duration log's setup phase is the LOG'S OWN DISPLAY RESOLUTION — pytest's --durations
# lines print seconds rounded to two decimals (the _DURATION_RE shape), so a displayed setup
# understates its true value by at most half an ulp of that display. A percentage of runtime
# has no physical justification and left a 5 % acceptance window at exactly the boundary.
DURATION_LOG_DISPLAY_RESOLUTION = 0.01
_CONTAINMENT_SLACK = DURATION_LOG_DISPLAY_RESOLUTION / 2


# The manifest STAMPS its measurement time as provenance only. The 30-day drift bound — refuse a
# manifest older than the bound so the whole suite was re-measured periodically — is RETIRED by
# the owner cadence ruling of 2026-08-28: an unchanged collection is never re-measured (two
# complete quiet-box runs disagreed by 24 s, so a re-measure encodes host variance, not drift); a
# test that got slower is caught where it changes, by the focused measurement of the nodes that
# changed, and a deliberately optimised test is re-measured by name (--remeasure).
_MEASURED_UTC_RE = re.compile(r'^#\s*measured_utc\s*=\s*(\S+)\s*$', re.MULTILINE)


def _now_utc() -> str:
    return datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def _check_measured_stamp(path: Path, text: str) -> None:
    """Require a well-formed `# measured_utc` header (provenance, never an expiry)."""
    match = _MEASURED_UTC_RE.search(text)
    if match is None:
        msg = f'{path}: no `# measured_utc = <ISO-8601>` header — the record must date itself'
        raise ManifestError(msg)
    try:
        datetime.datetime.strptime(match.group(1), '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=datetime.UTC
        )
    except ValueError as exc:
        msg = f'{path}: measured_utc {match.group(1)!r} is not a UTC ISO-8601 stamp'
        raise ManifestError(msg) from exc


class ManifestError(RuntimeError):
    """The manifest is missing, malformed, or does not cover the collected suite."""


def inventory_counts(
    nodeids: Iterable[str], unmeasured: Iterable[str] = frozenset()
) -> dict[str, int]:
    """Count the inventory the manifest declares: python vs C++, measured vs declared-unmeasured.

    A C++ doctest identity is `<path>.cpp::<case name>`; a Python node carries `.py::`. Splitting
    on that is the whole rule, and it is stated here rather than inferred at each call site.
    """
    ids = set(nodeids) | set(unmeasured)
    python = sum(1 for nodeid in ids if '.py::' in nodeid)
    return {
        'python': python,
        'cpp': len(ids) - python,
        'measured': len(ids) - len(set(unmeasured)),
        'unmeasured': len(set(unmeasured)),
    }


def _check_declared_inventory(
    path: Path, text: str, runtimes: dict[str, float], unmeasured: set[str]
) -> None:
    """Refuse when the declared inventory header disagrees with the rows beneath it.

    The header was hand-maintained until and had drifted; worse, nothing emitted it, so a
    regeneration would have silently DELETED a declaration a gate depends on. A declared number
    nothing keeps true is the defect this cycle kept finding.
    """
    declared = {}
    for key in ('python', 'cpp', 'measured', 'unmeasured'):
        match = re.search(rf'^#\s*inventory_{key}\s*=\s*(\d+)\s*$', text, re.MULTILINE)
        if match:
            declared[key] = int(match.group(1))
    if not declared:
        return
    actual = inventory_counts(runtimes, unmeasured)
    if declared != actual:
        msg = (
            f'{path}: the declared inventory {declared} does not match the rows {actual} — '
            f'the header must state what the file actually contains'
        )
        raise ManifestError(msg)


# ⛔ OWNER RULING 17: tier labels come from LOCAL LINUX runs — never macOS, never CI. A runtime
# measured anywhere else cannot carry a tier decision, so the manifest DECLARES where its numbers
# came from and the loader REFUSES a manifest that does not say, or that says something else.
# These two lines were STATIC HEADER TEXT here for the whole cycle, generated by nothing and
# checked by nothing — a label nobody keeps true, which is the class this cycle kept finding.
# crysta closed it there; this closes it here, symmetrically.
MEASUREMENT_PLATFORM = 'linux'
MEASUREMENT_SOURCE = 'local'
_PROVENANCE_EXPECTED = {
    'measurement_platform': MEASUREMENT_PLATFORM,
    'measurement_source': MEASUREMENT_SOURCE,
}


def _check_declared_provenance(path: Path, text: str) -> None:
    """Refuse a manifest that does not declare ruling-17 local-Linux provenance."""
    for field, expected in _PROVENANCE_EXPECTED.items():
        match = re.search(rf'^#\s*{field}\s*=\s*(\S+)\s*$', text, re.MULTILINE)
        if match is None:
            msg = (
                f'{path}: no `# {field} = {expected}` header — owner ruling 17 requires a '
                f'tiering input to state that it was measured on a local Linux run'
            )
            raise ManifestError(msg)
        if match.group(1) != expected:
            msg = (
                f'{path}: declares {field} = {match.group(1)!r}, but a tier decision '
                f'may only rest on {expected!r} (owner ruling 17: never macOS, never CI)'
            )
            raise ManifestError(msg)


UNMEASURED_TOKEN = 'UNMEASURED'  # noqa: S105 — a manifest token, not a credential
# ⛔ A hole must NAME ITS REASON: `UNMEASURED:<reason>`. A bare `UNMEASURED` is indistinguishable
# from "forgotten", which is exactly how 18 of them survived a whole cycle.
UNMEASURED_PREFIX = f'{UNMEASURED_TOKEN}:'


def _is_unmeasured(field: str) -> bool:
    """Whether a manifest's first field marks the row a declared hole."""
    return field == UNMEASURED_TOKEN or field.startswith(UNMEASURED_PREFIX)


def _hole_reason(path: Path, lineno: int, field: str) -> str:
    """The reason a hole declares, refusing the BARE form.

    ⛔ Accepting `UNMEASURED:<reason>` was only half the fix. The bare token stayed admissible,
    so nothing stopped a reasonless hole being written — a new form added and the old one left,
    the same shape as the vestigial `threshold` parameter and the un-retired single-file loader.
    Ruling 64's point only holds if bare is REFUSED: a hole with no reason is indistinguishable
    from a forgotten one, and 18 of them survived a whole cycle by being exactly that.
    """
    if field == UNMEASURED_TOKEN:
        msg = (
            f'{path}:{lineno}: bare `{UNMEASURED_TOKEN}` is refused — a declared hole must name '
            f'its reason as `{UNMEASURED_PREFIX}<reason>` (owner ruling 64), because a hole with '
            f'no reason cannot be told apart from one that was forgotten'
        )
        raise ManifestError(msg)
    reason = field[len(UNMEASURED_PREFIX) :].strip()
    if not reason:
        msg = (
            f'{path}:{lineno}: `{UNMEASURED_PREFIX}` with an empty reason is refused — name why '
            f'this node is unmeasured (owner ruling 64)'
        )
        raise ManifestError(msg)
    return reason


def _measured_in(text: str) -> set[str]:
    """The node ids the given manifest text carries with a numeric duration."""
    return set(_measured_values_in(text))


def _measured_values_in(text: str) -> dict[str, float]:
    """The measured `{nodeid: seconds}` rows the given manifest text carries.

    A FOREIGN (non-python) identity's measured value must survive a regeneration — the
    python producer cannot re-measure it, and holing it discarded a real measurement (the
    three C++ solo values were re-holed by the first regeneration after they landed).
    """
    found: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) == 2 and not _is_unmeasured(parts[0]):
            try:
                found[parts[1]] = float(parts[0])
            except ValueError:
                continue
    return found


def _unmeasured_reasons(text: str) -> dict[str, str]:
    """The reason each declared hole carries in the given manifest text."""
    found = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#') or '\t' not in line:
            continue
        field, nodeid = line.split('\t', 1)
        if field.startswith(UNMEASURED_PREFIX):
            found[nodeid] = field[len(UNMEASURED_PREFIX) :].strip()
    return found


def _unmeasured_in(text: str) -> set[str]:
    """The node ids the given manifest text declares UNMEASURED."""
    found = set()
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) == 2 and _is_unmeasured(parts[0]):
            found.add(parts[1])
    return found


def load_manifest(path: Path = MANIFEST) -> tuple[float, dict[str, float]]:
    """Return ``(threshold_seconds, {nodeid: seconds})`` from the committed manifest."""
    if not path.exists():
        msg = f'{path} is missing — regenerate it with `pixi run per-pr-measure`'
        raise ManifestError(msg)

    text = path.read_text(encoding='utf-8')
    threshold: float | None = DEFAULT_THRESHOLD_SECONDS
    declared_tiers: dict[str, float] = {}
    runtimes: dict[str, float] = {}
    seen_at: dict[str, int] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith('#'):
            match = _THRESHOLD_RE.match(line)
            if match:
                threshold = float(match.group(1))
            tier_match = _TIER_THRESHOLD_RE.match(raw)
            if tier_match:
                declared_tiers[tier_match.group(1)] = float(tier_match.group(2))
            continue
        parts = line.split('\t')
        if len(parts) != 2:
            msg = f'{path}:{lineno}: expected "<seconds>\\t<nodeid>", got {line!r}'
            raise ManifestError(msg)
        seconds_text, nodeid = parts
        first_lineno = seen_at.get(nodeid)
        if first_lineno is not None:
            msg = (
                f'{path}:{lineno}: duplicate nodeid {nodeid!r} — already declared at '
                f'{path}:{first_lineno}. A repeated node silently keeps only ONE row, so the '
                f'other is never enforced; declare each node exactly once.'
            )
            raise ManifestError(msg)
        seen_at[nodeid] = lineno
        if _is_unmeasured(seconds_text):
            _hole_reason(path, lineno, seconds_text)
            # A DECLARED hole, not a parse error. The manifest header is explicit that this
            # token "must never silently place a Python node in the per-PR tier", so it is
            # kept out of `runtimes` entirely: an unmeasured node can never be read as
            # "fast enough", which is what a 0.0 stand-in would have quietly meant.
            continue
        try:
            runtimes[nodeid] = float(seconds_text)
        except ValueError as exc:
            msg = f'{path}:{lineno}: {seconds_text!r} is not a number'
            raise ManifestError(msg) from exc

    _check_declared_provenance(path, text)
    _check_measured_stamp(path, text)
    _check_declared_inventory(path, text, runtimes, _unmeasured_in(text))

    if declared_tiers != TIER_THRESHOLDS:
        msg = (
            f'{path}: the declared `# tier_threshold_seconds` table {declared_tiers} does not '
            f'match the code constants {TIER_THRESHOLDS} — the manifest must state the contract '
            f'it is actually governed by'
        )
        raise ManifestError(msg)
    if threshold is None:
        msg = f'{path}: no `# threshold_seconds = <n>` header — the threshold must be stated'
        raise ManifestError(msg)
    return declared_tiers, runtimes


def load_unmeasured(path: Path = MANIFEST) -> set[str]:
    """Return the node ids the manifest DECLARES unmeasured (explicit holes, not silent gaps).

    These are excluded from the per-PR serial total and from the ratchet: an unmeasured node
    is neither grandfathered nor a new breach, because nothing has been measured about it.
    They are reported by count so the hole stays visible.
    """
    if not path.exists():
        msg = f'{path} is missing — regenerate it with `pixi run per-pr-measure`'
        raise ManifestError(msg)
    declared: set[str] = set()
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) == 2 and _is_unmeasured(parts[0]):
            declared.add(parts[1])
    return declared


def load_module_costs(path: Path = MANIFEST) -> dict[str, float]:
    """Return ``{module_path: seconds}`` from the manifest's ``module:`` rows."""
    if not path.exists():
        msg = f'{path} is missing — regenerate it with `pixi run per-pr-measure`'
        raise ManifestError(msg)
    costs: dict[str, float] = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        match = _MODULE_COST_RE.match(raw.rstrip())
        if match:
            costs[match.group(2)] = float(match.group(1))
    return costs


def collect_nodeids() -> list[str]:
    """Ask pytest which tests exist right now (the authority on coverage)."""
    result = subprocess.run(
        # No `-q` here: pyproject's addopts already carries one, and a second would select
        # pytest's `-qq` summary format (`file: count`) instead of the node ids this needs.
        [sys.executable, '-m', 'pytest', '--collect-only', '-p', 'no:cacheprovider'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Review-9 F1: a non-zero collection is refused OUTRIGHT even when some node ids
        # printed — a module erroring at collection would otherwise stale its recorded rows
        # and hand them to the transition accounting.
        msg = (
            f'pytest collection failed (rc={result.returncode}) — the audit refuses rather '
            f'than reasoning over a partial collection:\n{result.stdout}\n{result.stderr}'
        )
        raise ManifestError(msg)
    nodeids = [
        line.strip()
        for line in result.stdout.splitlines()
        if '::' in line and not line.startswith(('=', '-', ' '))
    ]
    if not nodeids:
        msg = (
            f'pytest collected no tests (rc={result.returncode}):\n'
            f'{result.stdout}\n{result.stderr}'
        )
        raise ManifestError(msg)
    return nodeids


def parse_durations(log: str) -> dict[str, float]:
    """Sum setup+call+teardown seconds per nodeid from a ``pytest --durations=0`` log."""
    totals: dict[str, float] = {}
    for line in log.splitlines():
        match = _DURATION_RE.match(line.strip())
        if match:
            totals[match.group(3)] = totals.get(match.group(3), 0.0) + float(match.group(1))
    # pytest reports milliseconds and the manifest banks three decimals: round the summed cost
    # to that grain so a bound comparison never turns on binary float residue (0.2 + 0.7 + 0.1
    # sums to 0.9999999999999999 and would slip under a 1.0 s bound).
    return {nodeid: round(seconds, 3) for nodeid, seconds in totals.items()}


def parse_setup_durations(log: str) -> dict[str, float]:
    """Sum only the ``setup`` phase seconds per nodeid (module-cost attribution)."""
    totals: dict[str, float] = {}
    for line in log.splitlines():
        match = _DURATION_RE.match(line.strip())
        if match and match.group(2) == 'setup':
            totals[match.group(3)] = totals.get(match.group(3), 0.0) + float(match.group(1))
    return totals


def separate_module_costs(
    runtimes: dict[str, float],
    module_costs: dict[str, float],
    setups: dict[str, float],
) -> list[str]:
    """Subtract each module's fixture cost from the one test row that absorbed it.

    pytest charges a module-scoped fixture's setup to whichever test triggers it, so that
    test's ``--durations`` total conflates its OWN cost with the module's shared cost — the
    same seconds the instrument records as the ``module:`` row. Recording both unseparated
    would double-represent the cost and misstate the triggering test's own runtime by two
    orders of magnitude. The trigger is identified from the same durations log (the module's
    largest ``setup`` phase, which must contain the instrumented cost); its row becomes the
    test's own cost. Mutates ``runtimes`` in place.

    Review-2 B4: reconciliation is a VERDICT, not best-effort — returns one description per
    retained cost that could NOT be reconciled to this log (no setup candidate; the largest
    setup too small to contain the cost; the trigger absent from the collected rows). The
    caller must refuse to write a manifest while this list is non-empty: a cost that cannot
    be tied to the same run's log is stale or foreign state wearing a fresh name.
    """
    failures: list[str] = []
    for module, cost in module_costs.items():
        candidates = {
            nodeid: seconds
            for nodeid, seconds in setups.items()
            if nodeid.startswith(module + '::')
        }
        if not candidates:
            failures.append(
                f'{module}: no setup phase in the duration log to carry its '
                f'{cost:.3f}s recorded fixture cost'
            )
            continue
        trigger = max(candidates, key=candidates.__getitem__)
        # Review-3 B4 — ACTUAL containment, with the only slack being the log's display
        # resolution: the displayed setup rounds the true setup to two decimals, so
        # true >= displayed - half-resolution; the setup can contain the cost only if
        # displayed >= cost - slack. A cost exceeding the largest displayed setup by more
        # than that slack is irreconcilable — never subtracted, never clamped away.
        if candidates[trigger] < cost - _CONTAINMENT_SLACK:
            failures.append(
                f'{module}: largest setup phase {candidates[trigger]:.3f}s cannot contain '
                f'the recorded {cost:.3f}s fixture cost (allowed slack '
                f'{_CONTAINMENT_SLACK:.3f}s, the duration log display resolution)'
            )
            continue
        if trigger not in runtimes:
            failures.append(f'{module}: setup trigger {trigger} is not among the collected tests')
            continue
        # Within an accepted path the subtraction can go below zero only by measurement
        # resolution (runtimes[trigger] >= displayed setup >= cost - slack), so the floor
        # absorbs at most half a display ulp — a real mismatch was already refused above.
        runtimes[trigger] = max(0.0, runtimes[trigger] - cost)
    return failures


def render_manifest(
    runtimes: dict[str, float],
    provenance: list[str],
    module_costs: dict[str, float] | None = None,
    unmeasured: dict[str, str] | None = None,
) -> str:
    lines = [
        '# Measured per-PR runtime audit — the record behind the',
        '# per-tier bounds and the committed breach RATCHET',
        '# (tests/threshold-breaches.md). It selects NOTHING: the retired `heavy` split is',
        '# gone and test selection lives in the three named groups (tests/test-groups.json),',
        '# all equal on selection; `tools/checks/per_pr_runtimes.py --check` gates coverage.',
        '# Rows are BANKED: an unchanged collection is never',
        '# re-measured; `pixi run per-pr-measure` measures ONLY the added nodes, once, and a',
        '# named node on request. No expiry, no budget. Seconds are setup+call+teardown, serial.',
        "# A test recorded as 0.000 ran below pytest's duration reporting floor (<0.005 s).",
        '#',
        f'# measurement_platform = {MEASUREMENT_PLATFORM}',
        f'# measurement_source = {MEASUREMENT_SOURCE}',
        f'# measured_utc = {_now_utc()}',
        '#',
        *[f'# {line}' for line in provenance],
        '#',
        '# Breaches are decided PER TIER against the table',
        '# below, which the loader validates against the code constants - a manifest must state',
        '# the contract it is actually governed by, not a number that governs nothing.',
        *[f'# tier_threshold_seconds.{tier} = {bound}' for tier, bound in TIER_THRESHOLDS.items()],
        '#',
        '# The inventory this file declares, GENERATED here and validated by the loader.',
        '# Counted over what this render is ABOUT TO WRITE - measured rows AND declared holes -',
        '# so the header cannot disagree with the rows beneath it. Holes now SURVIVE a',
        '# regeneration: they used to be rewritten as 0.000, which is a',
        '# measurement nobody took and which passes every tier threshold.',
        *[
            f'# inventory_{key} = {value}'
            for key, value in inventory_counts(runtimes, set(unmeasured or {})).items()
        ],
        '',
    ]
    holes = unmeasured or {}
    lines.extend(
        f'{UNMEASURED_PREFIX}{holes[nodeid]}\t{nodeid}'
        if nodeid in holes
        else f'{runtimes.get(nodeid, 0.0):.3f}\t{nodeid}'
        for nodeid in sorted(set(runtimes) | set(holes))
    )
    if module_costs:
        lines.extend([
            '',
            '# Module-scoped fixture costs, from tools/checks/fixture_costs.py:',
            '# paid ONCE per module by whichever test triggers them, so they cannot be',
            '# per-test rows (and are spelled as comments so per-test consumers are',
            '# unaffected; excluding one test only moves the cost to the next sibling).',
            '# These rows mark and deselect NOTHING - kept for visibility',
            '# and the stale-module integrity refusal.',
        ])
        lines.extend(
            f'# module-cost: {seconds:.3f}\t{module}'
            for module, seconds in sorted(module_costs.items())
        )
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# The threshold RATCHET.
#
# The per-tier bounds as first landed CLASSIFIED but did not FORCE: a breach only set the
# `heavy` split, and pull_request CI deselected those tests - so exceeding a bound bought
# a test freedom from PR feedback and nothing went red. That inverts ruling 53's purpose.
#
# The committed breach list is therefore a RATCHET BASELINE, not an allowlist:
#   * a breach ON the list is grandfathered - clearing it is, not this gate;
#   * a breach NOT on the list FAILS         - a slow test goes red at the commit that adds it;
#   * a listed node that no longer breaches FAILS - demanding removal, so a fixed test cannot
#     linger on the list as a licence to re-breach later. That third rule is what makes this a
#     ratchet rather than a ceiling.
#
# Editing the baseline stays possible and is the point: adding a line is a visible, reviewable
# act in a committed file. The goal is to make the decision EXPLICIT, not impossible.
BREACH_BASELINE = ROOT / 'tests' / 'threshold-breaches.md'

# `- 1.230 s - `<nodeid>`` (the em dash is what the committed list uses).
_BREACH_ROW_RE = re.compile(r'^-\s+([\d.]+)\s*s\s+\u2014\s+`([^`]+)`\s*$')
_RATCHET_PREVIEW = 20
# Column index of the breach count in the document's `| **total** | ... |` summary row.
_TOTAL_BREACH_COL = 3


def parse_breach_baseline(path: Path = BREACH_BASELINE) -> set[str]:
    """Parse the committed breach baseline, refusing if the file stopped being understood.

    The parsed row count is cross-checked against the total the document DECLARES in its own
    summary table. Without that check a format drift would silently yield an empty baseline,
    and an empty baseline makes every real breach read as `fixed` while every new breach reads
    as `new` - a guard that quietly stops guarding. This gate refuses instead.
    """
    if not path.is_file():
        msg = f'the threshold breach baseline is missing: {path}'
        raise ManifestError(msg)
    text = path.read_text(encoding='utf-8')
    baseline = {
        m.group(2) for line in text.splitlines() if (m := _BREACH_ROW_RE.match(line.strip()))
    }
    declared: int | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and '**total**' in stripped.lower():
            cells = [c.strip().strip('*').strip() for c in stripped.strip('|').split('|')]
            if len(cells) > _TOTAL_BREACH_COL and cells[_TOTAL_BREACH_COL].isdigit():
                declared = int(cells[_TOTAL_BREACH_COL])
            break
    if declared is None:
        msg = f'{path} declares no parseable **total** row, so its baseline cannot be trusted'
        raise ManifestError(msg)
    if declared != len(baseline):
        msg = (
            f'{path} declares {declared} breaches in its total row but {len(baseline)} row(s) '
            f'parsed - the file format and this parser have drifted apart'
        )
        raise ManifestError(msg)
    return baseline


def _ratchet_errors(runtimes: dict[str, float], baseline: set[str]) -> list[str]:
    """Compare measured breaches against the committed baseline."""
    breaching = {node for node, seconds in runtimes.items() if seconds >= threshold_for(node)}
    new = sorted(breaching - baseline)
    gone = sorted(baseline - breaching)
    if not new and not gone:
        return []

    def _new_line(node: str) -> str:
        return f'{runtimes[node]:.3f} s >= {threshold_for(node):.3f} s ({tier_of(node)}) - {node}'

    def _preview(lines: list[str]) -> str:
        shown = '\n      '.join(lines[:_RATCHET_PREVIEW])
        rest = len(lines) - _RATCHET_PREVIEW
        return shown + (
            f'\n      ... and {rest} more (not truncated silently)' if rest > 0 else ''
        )

    if new and gone:
        # Failure mode 1: the inventory is keyed by node id, so a RENAME reads as a new breach
        # and a fixed breach at once. Emitting two errors would send a reader to two wrong
        # places, so say it plainly, once.
        return [
            f'ratchet (ruling 58): the baseline is stale in BOTH directions at once - '
            f'{len(new)} new breach(es) and {len(gone)} listed node(s) that no longer breach.\n'
            '    THIS IS THE SIGNATURE OF A RENAME: a renamed test reads as a new breach\n'
            '    AND a fixed breach simultaneously, and it is ONE edit to the list, not\n'
            '    two. Check the two groups against each other before treating them as\n'
            '    separate problems.\n'
            '    breaching, not on the list:\n      '
            + _preview([_new_line(n) for n in new])
            + '\n    on the list, no longer breaching:\n      '
            + _preview(gone)
        ]
    if new:
        return [
            f'ratchet (ruling 58): {len(new)} test(s) breach a tier bound but are not on the '
            f'committed baseline {BREACH_BASELINE.name}:\n      '
            + _preview([_new_line(n) for n in new])
            + '\n    Optimise the test, or record the breach as an explicit, reviewable line in '
            'that file.\n    Do NOT raise the tier bound to make this go away.'
        ]
    return [
        f'ratchet (ruling 58): {len(gone)} baseline entr(y/ies) no longer breach. Remove them '
        f'from {BREACH_BASELINE.name} so the list cannot license a future re-breach:\n      '
        + _preview(gone)
    ]


def _integrity_errors(
    collected: list[str],
    runtimes: dict[str, float],
    module_costs: dict[str, float],
    declared_holes: set[str],
) -> list[str]:
    """Refuse on SILENT gaps in the inventory; declared holes are reported, not fatal."""
    # A DECLARED hole is visible by construction, so it is not a silent gap. `missing` must
    # keep meaning "collected but not mentioned at all", which is the failure the manifest
    # cannot survive; the holes are reported by count in the summary line instead.
    missing = sorted(set(collected) - set(runtimes) - declared_holes)
    # ⛔ `collect_nodeids()` asks PYTEST, which cannot see a C++ doctest identity. Those rows are
    # not stale — they are the cross-language half of the inventory, and calling them stale would
    # push a caller to delete the native tier to make the gate pass. They are measured from the
    # doctest binary (`--duration=true`) and carried; only PYTHON identities can go stale here.
    stale = sorted(nodeid for nodeid in set(runtimes) - set(collected) if '.py::' in nodeid)
    collected_modules = {nodeid.split('::', 1)[0] for nodeid in collected}
    stale_modules = sorted(set(module_costs) - collected_modules)

    errors: list[str] = []
    if stale_modules:
        errors.append(
            f'{len(stale_modules)} module-cost row(s) name modules that no longer exist:\n    '
            + '\n    '.join(stale_modules[:20])
        )
    if missing:
        errors.append(
            f'{len(missing)} collected test(s) have no recorded runtime, so their per-PR '
            f'tier would rest on nothing measured:\n    '
            + '\n    '.join(missing[:20])
            + ('\n    …' if len(missing) > 20 else '')
        )
    if stale:
        errors.append(
            f'{len(stale)} recorded runtime(s) name tests that no longer exist:\n    '
            + '\n    '.join(stale[:20])
            + ('\n    …' if len(stale) > 20 else '')
        )
    return errors


# The retired mechanism may not return. A selection derived from a measurement is
# invisible (`verify` was rc=0 while the merge mirror was red on the
# same tree), so any marker-based deselection reappearing in a LIVE config surface is
# refused here. Comment lines are exempt: documenting the retirement is not a deselection.
_MARKER_SURFACES = (
    'pixi.toml',
    'pyproject.toml',
    'tests/conftest.py',
    'tools/ci/local-ci.sh',
    '.github/workflows/ci.yml',
)
_RETIRED = 'heavy'
_MARKER_PATTERNS = tuple(f'{stem}{_RETIRED}' for stem in ('not ', 'mark.', 'm '))


def _marker_deselection_errors() -> list[str]:
    """Live (non-comment) lines re-introducing a deselection or assignment of the retired split."""
    errors: list[str] = []
    for relative in _MARKER_SURFACES:
        path = ROOT / relative
        if not path.is_file():
            continue
        for lineno, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if any(pattern in line for pattern in _MARKER_PATTERNS):
                errors.append(f'{relative}:{lineno}: {line[:100]}')
    return errors


def check() -> int:
    try:
        _tiers, runtimes = load_manifest()
        module_costs = load_module_costs()
        collected = collect_nodeids()
    except ManifestError as exc:
        print(f'per-PR runtime audit: FAIL\n  {exc}', file=sys.stderr)
        return 1

    declared_holes = load_unmeasured()
    errors = _integrity_errors(collected, runtimes, module_costs, declared_holes)

    if errors:
        joined = '\n  '.join(errors)
        print(
            f'per-PR runtime audit: FAIL\n  {joined}\n'
            '  Remediation: `pixi run per-pr-measure` re-measures and rewrites the manifest.',
            file=sys.stderr,
        )
        return 1

    try:
        ratchet = _ratchet_errors(runtimes, parse_breach_baseline())
    except ManifestError as exc:
        sys.stderr.write(f'per-PR runtime audit: FAIL\n  {exc}\n')
        return 1
    if ratchet:
        joined = '\n  '.join(ratchet)
        sys.stderr.write(f'per-PR runtime audit: FAIL\n  {joined}\n')
        return 1

    # Effective tier at MODULE granularity: a test is out of the per-PR tier when its own
    # runtime meets the threshold OR its module's recorded fixture cost does — the same
    # rule tests/conftest.py applies, so this budget is what the tier actually costs.
    returned = _marker_deselection_errors()
    if returned:
        joined = '\n    '.join(returned)
        print(
            f'per-tier runtime audit: FAIL\n  the retired measured runtime deselection has '
            f'RETURNED to a live config surface:\n    {joined}',
            file=sys.stderr,
        )
        return 1

    over = sorted(node for node, s in runtimes.items() if s >= threshold_for(node))
    print(
        f'per-tier runtime audit: OK — {len(collected)} tests recorded '
        f'({len(declared_holes)} DECLARED UNMEASURED, excluded from the ratchet), '
        f'per-tier thresholds {thresholds_text()}, '
        f'{len(over)} over-bound row(s) carried by the committed ratchet baseline '
        f'(declared exceptions included and reasoned there)'
    )
    return 0


def _reconciled_module_costs(
    fixture_costs: Path,
    measured: dict[str, float],
    runtimes: dict[str, float],
    log_path: Path,
) -> dict[str, float]:
    """Load, schema-validate, and reconcile the fixture-cost artifact; raise on any defect.

    Review-1/2 B4, fail-closed end to end: a missing or malformed artifact, a semantically
    malformed entry (non-finite or negative cost), a cost for a module absent from this
    run's duration log, and a retained cost that cannot be reconciled to a setup phase in
    the same log all raise ManifestError — the caller must not write a manifest in any of
    those states, because each one lets stale or broken fixture-cost state dress a
    fresh-looking manifest (the ~338 s defect this measurement exists to close).
    """
    if not fixture_costs.exists():
        msg = (
            f'fixture-cost artifact {fixture_costs} is missing — the measured run did not '
            f'produce it; refusing to write a manifest with absent module costs'
        )
        raise ManifestError(msg)
    try:
        raw = json.loads(fixture_costs.read_text(encoding='utf-8'))
        # Review-21 F1: the artifact now carries the COMPLETED-NODE SET beside the module costs.
        # The old flat shape is refused rather than tolerated — a run that produced it did not
        # record completion, so nothing downstream could tell "fast" from "never reached".
        if not (isinstance(raw, dict) and 'module_costs' in raw and 'completed' in raw):
            msg = (
                f'fixture-cost artifact {fixture_costs} predates the completed-node set '
                f'(review-21 F1); re-run the measurement so completion is recorded'
            )
            raise ManifestError(msg)
        items = sorted(raw['module_costs'].items())
    except (ValueError, AttributeError) as exc:
        msg = f'fixture-cost artifact {fixture_costs} is malformed: {exc}'
        raise ManifestError(msg) from exc
    # Review-2 B4: schema is validated ENTRY BY ENTRY before any filtering — a negative
    # or non-finite cost is a malformed measurement, and dropping it as dust would turn
    # a broken artifact into an empty-but-fresh-looking module-cost set.
    bad_entries = [
        f'{module!r}: {cost!r}'
        for module, cost in items
        if not isinstance(module, str)
        or isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(cost)
        or cost < 0
    ]
    if bad_entries:
        msg = (
            f'fixture-cost artifact {fixture_costs} has {len(bad_entries)} semantically '
            f'malformed entr(y/ies) — every cost must be a finite non-negative number '
            f'keyed by a module path:\n    ' + '\n    '.join(bad_entries[:10])
        )
        raise ManifestError(msg)
    # Keep observed costs above float dust; the threshold decides heaviness, not this.
    module_costs = {module: cost for module, cost in items if cost >= 0.01}
    # Reconcile against the same run's duration log: a module whose fixture this run
    # timed necessarily ran tests this run reported. A cost for a module absent from
    # the log is stale state from some other run — refuse it.
    measured_modules = {nodeid.split('::', 1)[0] for nodeid in measured}
    orphaned = sorted(set(module_costs) - measured_modules)
    if orphaned:
        msg = (
            f'fixture-cost artifact names {len(orphaned)} module(s) absent from the '
            f'duration log (first: {orphaned[0]!r}) — stale fixture-cost state; re-measure'
        )
        raise ManifestError(msg)
    log_text = log_path.read_text(encoding='utf-8')
    irreconcilable = separate_module_costs(runtimes, module_costs, parse_setup_durations(log_text))
    if irreconcilable:
        msg = (
            f'{len(irreconcilable)} recorded module cost(s) cannot be reconciled to this '
            f'duration log — refusing to write the manifest:\n    ' + '\n    '.join(irreconcilable)
        )
        raise ManifestError(msg)
    return module_costs


# A durations log produced by a PARALLEL run attributes contention, not cost: with workers
# competing for cores every number is inflated by an unknown, unrecorded amount, and the tier
# decision this manifest drives is per test. xdist announces itself in the run header and tags
# every line it forwards, so the log carries the evidence — refuse on it rather than record
# numbers whose meaning we cannot state.
# xdist writes its own parallelism into the log in two shapes, and BOTH are load-bearing:
#   * WORKER CREATION - the session header announcing how many workers were made;
#   * GATEWAY PREFIXES - every forwarded line tagged with the gateway that produced it, which
#     appears bare at line start (`gw0 [125] / gw1 [125]`) as well as bracketed (`[gw0]`).
# Matching the bracketed form alone misses the bare prefix, which is the commoner spelling in a
# durations log.
_PARALLEL_LOG_PATTERNS = (
    # ANYWHERE in the line, not just at its start: a durations line begins with the timing
    # (`0.10s call     [gw3] tests/x.py::y`), so a start-anchored pattern misses the very
    # shape this gate is about.
    re.compile(r'\[gw\d+\]'),
    re.compile(r'^\s*\[?gw\d+', re.MULTILINE),
    re.compile(r'created:\s*\d+\s*/\s*\d+\s*workers?', re.IGNORECASE),
    re.compile(r'\bworker\s+gw\d+', re.IGNORECASE),
    re.compile(r'\bgw\d+\s*\[', re.MULTILINE),
    # Worker-creation lines come in more than one spelling: xdist announces the count as
    # `created: 8/8 workers` in one place and `8 workers [123 items]` in another, and the
    # gateway objects appear as `WorkerController gw0`. A serial run never says "workers".
    re.compile(r'\b\d+\s+workers?\b', re.IGNORECASE),
    re.compile(r'WorkerController', re.IGNORECASE),
    re.compile(r'\bdist:\s*\w+', re.IGNORECASE),
)


# The measurement records its own conditions (see tools/ci/verify-wall-clock.py). When a log
# carries that record, the observed worker count is direct evidence about the run that produced
# it — better than any textual marker, because it is what the measurement OBSERVED rather than
# what its output happened to mention.
_OBSERVED_WORKERS_RE = re.compile(
    r'^measurement-condition\.runner_worker_max=(\d+)\s*$', re.MULTILINE
)


def _refuse_parallel_log(log_path: Path, text: str) -> None:
    """Refuse a durations log that a parallel run produced."""
    observed = _OBSERVED_WORKERS_RE.search(text)
    if observed is not None and int(observed.group(1)) > 1:
        msg = (
            f'{log_path} records runner_worker_max={observed.group(1)}: the measurement that '
            f'produced it OBSERVED parallelism, so its per-test numbers attribute contention '
            f'rather than cost and may not write the runtime manifest.'
        )
        raise ManifestError(msg)
    hits = sorted({p.pattern for p in _PARALLEL_LOG_PATTERNS if p.search(text)})
    if hits:
        msg = (
            f'{log_path} was produced by a PARALLEL pytest run (markers: {hits}). '
            f'A parallel durations log attributes contention rather than cost, so it may not '
            f'write the runtime manifest. Re-measure with `pixi run per-pr-measure`, which '
            f'neutralises parallel defaults.'
        )
        raise ManifestError(msg)


# Node ids pytest reported as failing/erroring in this run. P1.28: a failing node records the
# COST OF ERRORING, not the cost of running, so it must stay UNMEASURED until it is green.
_OUTCOME_RE = re.compile(r'^(?:FAILED|ERROR)\s+(\S+?)(?:\s+-.*)?$', re.MULTILINE)


def failing_nodeids(text: str) -> set[str]:
    """The node ids this durations log reports as failed or errored."""
    return {match.group(1) for match in _OUTCOME_RE.finditer(text)}


def _completed_nodes(fixture_costs: Path | None) -> set[str] | None:
    """The node ids the measured run PROVED it finished, from the fixture-cost artifact.

    Review-21 F1: without this the updater cannot distinguish a node that ran below pytest's
    reporting floor from one the run never reached, and it resolved that ambiguity by writing
    0.000 — the fastest possible measured test. `None` means "no artifact to check against",
    which keeps a caller that passes no artifact behaving exactly as before.
    """
    if fixture_costs is None:
        return None
    try:
        raw = json.loads(Path(fixture_costs).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    if not isinstance(raw, dict) or 'completed' not in raw:
        return set()
    return {str(nodeid) for nodeid in raw['completed']}


def resolve_rows(  # noqa: PLR0913, PLR0917 — the carry inputs are distinct evidence channels
    collected: list[str],
    measured: dict[str, float],
    failing: set[str],
    carried_unmeasured: set[str],
    carried_foreign: set[str],
    carried_reasons: dict[str, str] | None = None,
    completed: set[str] | None = None,
    carried_foreign_values: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, str]]:
    """Split the inventory into honest measured rows and explicit holes.

    ⛔ THE RULE THAT WAS MISSING: a node the run reported as FAILED/ERROR does not get its
    duration recorded. The previous `measured.get(nodeid, 0.0)` gave every unreported node 0.000,
    and 0.000 is below every tier threshold, so a FAILING test silently joined the per-PR tier as
    the fastest thing in the suite. A failing node's duration is the cost of ERRORING, not the
    cost of running (P1.28), so it stays a declared hole until it is green.

    A node that is absent but NOT failing is a different case and is measured, not holed: pytest
    hides sub-floor durations, so "not in the log" is how a very fast passing test looks.

    Holes are also CARRIED: a previously declared hole that this run did not measure stays a hole
    instead of being regenerated into a zero, and identities the collector cannot see at all (the
    native C++ tier — `collect_nodeids()` asks pytest) are retained rather than dropped, so a
    regeneration cannot silently shrink the cross-language inventory.
    """
    # ⛔ The invariant reaches the LAST callable too. `completed=None` used to mean "no evidence,
    # fall through to 0.0"; it now refuses. Nothing may hand this function an unmeasured node and
    # get a number back — not the CLI, not `update()`, not a direct caller.
    if completed is None:
        msg = (
            'resolve_rows() was given no completed-node set: absence cannot be told from '
            'sub-floor speed, so refusing rather than recording 0.000'
        )
        raise ManifestError(msg)
    carried_reasons = carried_reasons or {}
    runtimes: dict[str, float] = {}
    holes: dict[str, str] = {}
    for nodeid in collected:
        if nodeid in failing:
            # the cost of erroring is not the cost of running
            holes[nodeid] = 'failed-in-this-run'
        elif nodeid in measured:
            runtimes[nodeid] = measured[nodeid]
        elif completed is not None and nodeid not in completed:
            # ⛔ REVIEW-21 F1: absent AND not proved complete. The run stopped before reaching
            # this node, so there is no measurement to record and no failure to attribute. The
            # previous code fell through to the sub-floor branch below and wrote 0.000, which
            # turned every unreached node into the fastest possible measured test — exactly what
            # the shell's own diagnostic promises does NOT happen.
            holes[nodeid] = 'not-completed-in-this-run'
        else:
            # ⛔ ABSENT IS NOT ONE THING, and my first version of this treated it as one.
            # pytest hides every duration below its ~0.005 s reporting floor even under
            # `--durations=0`, so a node that PASSED very fast is absent from the log for a
            # completely different reason than one that failed. Marking both a hole would have
            # declared hundreds of genuinely fast tests unmeasured — a regression dressed as a
            # fix. A node that is neither reported nor failing was collected, ran, and finished
            # under the floor: that is a real measurement, recorded at the floor's resolution.
            runtimes[nodeid] = 0.0
    foreign_values = carried_foreign_values or {}
    for nodeid in carried_unmeasured | carried_foreign:
        if nodeid in runtimes:
            continue
        # A foreign identity that CARRIES A MEASUREMENT keeps it — the python producer
        # cannot re-measure native C++, and holing a measured value discards a real
        # measurement (the three C++ solo values were re-holed by the first regeneration
        # after they landed). Only an identity that was already a hole stays one.
        if nodeid not in carried_unmeasured and nodeid in foreign_values:
            runtimes[nodeid] = foreign_values[nodeid]
        else:
            holes[nodeid] = carried_reasons.get(nodeid, 'not-produced-by-this-run')
    return runtimes, holes


def _require_completion_evidence(fixture_costs: Path | None) -> None:
    """Refuse unless the artifact PROVES which nodes completed. Never warns, never defaults."""
    if fixture_costs is None:
        msg = (
            'no fixture-cost artifact supplied: --update requires --fixture-costs, because the '
            'artifact carries the completed-node set. Without it a node that is absent from the '
            'durations log cannot be told apart from one the run never reached, and recording it '
            'as 0.000 would make an unrun test the fastest measurement in the suite'
        )
        raise ManifestError(msg)
    try:
        raw = json.loads(Path(fixture_costs).read_text(encoding='utf-8'))
    except OSError as exc:
        msg = f'fixture-cost artifact {fixture_costs} is unreadable: {exc}'
        raise ManifestError(msg) from exc
    except ValueError as exc:
        msg = f'fixture-cost artifact {fixture_costs} is malformed: {exc}'
        raise ManifestError(msg) from exc
    if not isinstance(raw, dict) or 'completed' not in raw or 'module_costs' not in raw:
        msg = (
            f'fixture-cost artifact {fixture_costs} carries no completed-node set (legacy shape); '
            f're-run the measurement so completion is recorded'
        )
        raise ManifestError(msg)
    if not isinstance(raw['completed'], list):
        msg = f'fixture-cost artifact {fixture_costs}: `completed` must be a list'
        raise ManifestError(msg)


def _banked_module_costs(existing_text: str, collected: list[str]) -> dict[str, float]:
    """Return the module-cost rows an existing manifest carries for still-collected modules."""
    modules = {nodeid.split('::', 1)[0] for nodeid in collected}
    costs: dict[str, float] = {}
    for raw in existing_text.splitlines():
        match = _MODULE_COST_RE.match(raw.rstrip())
        if match and match.group(2) in modules:
            costs[match.group(2)] = float(match.group(1))
    return costs


def added_nodes() -> list[str]:
    """Return the collected nodes with no banked row or hole — what a focused run must measure."""
    existing = MANIFEST.read_text(encoding='utf-8') if MANIFEST.exists() else ''
    banked = _measured_in(existing) | _unmeasured_in(existing)
    return sorted(node for node in collect_nodeids() if node not in banked)


def _focused_rows(
    log_path: Path,
    fixture_costs: Path | None,
    targets: list[str],
) -> tuple[dict[str, float], dict[str, str], dict[str, float]]:
    """Resolve the targets' rows, holes and module costs from one focused measured run.

    The completion artifact is REQUIRED here (absence is ambiguous without it). The module costs
    the focused run observed are reconciled against its own log FIRST: each shared fixture cost
    is subtracted from the node of this run that triggered it, so the targets' rows are their own
    costs and the shared cost is recorded once, as its module row (the bound used to be applied
    to setup-plus-call totals, and the reconciled copy discarded). A target whose own cost
    breaches its tier bound without a baseline entry is then refused before any write. Banked
    rows were reconciled when they were measured and are not read here.
    """
    _require_completion_evidence(fixture_costs)
    if fixture_costs is None:  # unreachable: _require_completion_evidence refused None above
        raise ManifestError('no completion artifact')
    log_text = log_path.read_text(encoding='utf-8')
    _refuse_parallel_log(log_path, log_text)
    measured = parse_durations(log_text)
    own = dict(measured)  # this run's totals, each shared fixture cost taken off its trigger
    module_costs = _reconciled_module_costs(fixture_costs, measured, own, log_path)
    rows, holes = resolve_rows(
        targets,
        own,
        failing_nodeids(log_text),
        set(),
        set(),
        {},
        _completed_nodes(fixture_costs),
        {},
    )
    try:
        baseline = parse_breach_baseline()
    except ManifestError:
        baseline = set()
    breaching = [
        node for node in rows if rows[node] >= threshold_for(node) and node not in baseline
    ]
    if breaching:
        msg = (
            'new unlisted threshold breach(es) among the measured nodes; fix the test — a '
            'breach is never absorbed, and nothing was written:\n    '
            + '\n    '.join(
                f'{rows[n]:.3f} s >= {threshold_for(n):.3f} s ({tier_of(n)}) - {n}'
                for n in breaching
            )
        )
        raise ManifestError(msg)
    return rows, holes, module_costs


def _write_banked(
    kept: dict[str, float],
    holes: dict[str, str],
    module_costs: dict[str, float],
    source: str,
    collected: list[str],
) -> int:
    reported = sum(1 for value in kept.values() if value > 0.0)
    provenance = [
        f'Recorded from: {source}',
        f'Collected tests: {len(collected)}; with a reported duration: {reported}',
    ]
    if module_costs:
        provenance.append(f'Module-scoped fixture costs recorded: {len(module_costs)}')
    MANIFEST.write_text(render_manifest(kept, provenance, module_costs, holes), encoding='utf-8')
    print(
        f'wrote {MANIFEST} ({len(kept)} tests, per-tier thresholds {thresholds_text()}; {source})'
    )
    return 0


def _update(log_path: Path, fixture_costs: Path | None, remeasure: Iterable[str]) -> int:
    collected = collect_nodeids()
    existing = MANIFEST.read_text(encoding='utf-8') if MANIFEST.exists() else ''
    remeasure = sorted(set(remeasure))
    unknown = [node for node in remeasure if node not in collected]
    if unknown:
        msg = '--remeasure names nodes that are not collected:\n    ' + '\n    '.join(unknown)
        raise ManifestError(msg)
    banked_python = {n for n in _measured_in(existing) | _unmeasured_in(existing) if '.py::' in n}
    if existing and banked_python == set(collected) and not remeasure:
        print(
            f'collection unchanged ({len(collected)} tests): banked measurement kept, no '
            f'evidence read (owner cadence ruling 2026-08-28)'
        )
        return 0

    # Foreign (non-python) identities are carried whole — pytest cannot collect them.
    def _keep(node: str) -> bool:
        return (node in collected or '.py::' not in node) and node not in remeasure

    kept = {n: v for n, v in _measured_values_in(existing).items() if _keep(n)}
    holes = {n: r for n, r in _unmeasured_reasons(existing).items() if _keep(n)}
    removed = sum(1 for node in banked_python if node not in collected)
    targets = sorted(node for node in collected if node not in kept and node not in holes)
    module_costs = _banked_module_costs(existing, collected)
    if not targets:
        source = f'banked rows (nothing added; {removed} stale row(s) dropped)'
        return _write_banked(kept, holes, module_costs, source, collected)
    rows, new_holes, new_costs = _focused_rows(log_path, fixture_costs, targets)
    source = (
        f'{log_path.name} ({len(targets)} node(s) measured once, {len(kept)} banked, '
        f'{removed} stale row(s) dropped)'
    )
    kept.update(rows)
    holes.update(new_holes)
    module_costs.update(new_costs)
    return _write_banked(kept, holes, module_costs, source, collected)


def update(
    log_path: Path, fixture_costs: Path | None = None, remeasure: Iterable[str] = ()
) -> int:
    """Bank the ADDED nodes (and any `remeasure` node) from one focused measured run.

    Owner cadence ruling 2026-08-28: an unchanged collection is NEVER re-measured — neither the
    log nor the artifact is read; a changed collection is measured ONCE, only the added nodes.
    Every banked row and declared hole is kept, rows whose node no longer exists are dropped,
    and an added node breaching its tier bound without a baseline entry is refused BEFORE the
    manifest is touched. Whenever something IS measured the completion artifact is required —
    no code path gives an unmeasured node a number.
    """
    try:
        return _update(log_path, fixture_costs, remeasure)
    except ManifestError as exc:
        print(f'per-PR runtime audit: FAIL\n  {exc}', file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', type=Path, metavar='DURATIONS_LOG')
    parser.add_argument(
        '--fixture-costs',
        type=Path,
        metavar='FIXTURE_COSTS_JSON',
        help='REQUIRED with --update whenever a node is measured: carries the completed-node '
        'set that makes absence legible',
    )
    parser.add_argument(
        '--remeasure',
        action='append',
        default=[],
        metavar='NODEID',
        help="with --update: take this collected node's value from the log even though it is "
        'banked (a deliberately optimised test) — repeatable',
    )
    parser.add_argument(
        '--added-nodes',
        action='store_true',
        help='print the collected nodes with no banked row or hole, one per line (what a '
        'focused measurement must run; empty means the collection is unchanged)',
    )
    args = parser.parse_args(argv)
    if args.added_nodes:
        try:
            nodes = added_nodes()
        except ManifestError as exc:
            print(f'per-PR runtime audit: FAIL\n  {exc}', file=sys.stderr)
            return 1
        sys.stdout.write(''.join(f'{node}\n' for node in nodes))
        return 0
    if args.update is not None:
        return update(args.update, args.fixture_costs, args.remeasure)
    return check()


if __name__ == '__main__':
    raise SystemExit(main())
