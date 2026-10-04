#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Measure the ADDED nodes — once — and bank them into tests/per-pr-runtimes.tsv. Owner ruling
# 2026-08-28: an unchanged collection is NEVER re-measured (this script exits 0 having measured
# nothing), and a changed one is measured ONCE, only what was added. Explicit node ids passed as
# arguments are re-measured on request — the way a deliberately optimised test gets its banked
# number refreshed so a fixed breach can leave the ratchet baseline. There is no full-suite
# re-measure and no manifest expiry any more: the 30-day drift bound that forced a periodic ~2
# min re-run is retired with the ruling.
#
# SERIAL on purpose, and ENFORCED rather than merely intended: a per-test number is only
# attributable when nothing else is competing for the core, and the tier decision is per test.
# An ambient `PYTEST_ADDOPTS=-n auto`, or xdist arriving as a transitive dependency, would
# parallelise the measurement silently and every number in the manifest would be an
# attribution of contention rather than of a test.
#
# ⛔ There is NO global threshold and NO aggregate budget. Rulings 53/54 replaced the single
# global bound with PER-TIER bounds that live as code constants; the 2026-08-28 ruling retired
# the aggregate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# ⛔ ONE MEASUREMENT AT A TIME. Two overlapping runs are the worst possible measurement: each
# is the other's contention, so both record inflated per-test numbers, and the second to finish
# overwrites the manifest with them. Neither run can tell that it happened. `flock` makes the
# overlap impossible rather than detectable after the fact; a non-blocking acquire means the
# second invocation REFUSES immediately and says why, instead of silently queueing behind a
# ~20-minute run its caller does not know about.
# `.lock.d`, not `.lock`: the OLD flock implementation left a regular FILE at the bare path,
# and `mkdir` can never succeed against one — a checkout carrying that legacy file would wait
# out the whole deadline and then refuse, forever. Measured on this box, in both repos. A
# distinct directory-shaped path makes the migration inert instead of fatal.
MEASURE_LOCK="${MEASURE_LOCK:-$ROOT/build/.per-pr-measure.lock.d}"
mkdir -p "$(dirname "$MEASURE_LOCK")"
# NOT `exec flock ... || { ... }`: `exec` REPLACES this shell, so the `||` branch is unreachable
# and a refused lock would exit with flock's status having printed nothing at all — a silent
# refusal, which is the failure mode this whole cycle is about. The lock is held on a file
# descriptor for the script's lifetime instead, so the refusal can speak.
# `mkdir`, not `flock`: flock is util-linux and macOS ships none, so the old
# `if command -v flock; then ... fi` took NO LOCK AT ALL there — no else branch, no message.
# Identical defect to crysta's, fixed there first and missed here until the edi sweep.
if ! mkdir "$MEASURE_LOCK" 2>/dev/null; then
  echo "REFUSING: another per-PR measurement already holds $MEASURE_LOCK." >&2
  echo "Overlapping measurements contend, so both record inflated per-test numbers and the" >&2
  echo "last to finish overwrites the manifest with them." >&2
  echo "If no measurement is running, an earlier one was killed: remove $MEASURE_LOCK." >&2
  exit 1
fi
trap 'rmdir "$MEASURE_LOCK" 2>/dev/null || true' EXIT

# Kept, not a temp file: the manifest is a committed record, so the run it came from has to
# stay inspectable afterwards — a reviewer asking "where does 364 s come from?" needs the log.
LOG="${LOG:-$ROOT/build/per-pr-durations.txt}"
mkdir -p "$(dirname "$LOG")"

# The fixture-cost instrument rides the same measured run — module-scoped fixture costs are
# per MODULE, invisible to per-test durations, and tools/checks/fixture_costs.py records
# them so the manifest can express them (as a FRESH PER-RUN artifact, never a persistent
# path a stale run could have left behind). The unique name generation- binds the file to
# this invocation; its EXISTENCE afterwards proves pytest reached sessionfinish in THIS run
# (the plugin writes it even when no module cost was observed), and a missing/leftover
# artifact fails closed instead of producing a fresh-looking manifest from stale or missing
# costs.
COSTS="$ROOT/build/per-pr-fixture-costs.$$-$(date +%s).json"
rm -f "$ROOT"/build/per-pr-fixture-costs*.json

# What must be measured: the collected nodes with no banked row or hole (from the ONE
# authority, the updater's own diff), plus any node ids named on the command line.
mapfile -t TARGETS < <(python tools/checks/per_pr_runtimes.py --added-nodes)
REMEASURE=("$@")
if [ "${#TARGETS[@]}" -eq 0 ] && [ "${#REMEASURE[@]}" -eq 0 ]; then
    # No additions does not prove the collection is unchanged: it may contain removals only.
    # The updater compares both sets and drops stale rows without reading either evidence file;
    # a truly unchanged collection still exits through its no-evidence-read path.
    python tools/checks/per_pr_runtimes.py --update "$LOG" --fixture-costs "$COSTS"
    exit 0
fi
TARGETS+=("${REMEASURE[@]}")
echo "measuring ${#TARGETS[@]} node(s) serially, once (${#REMEASURE[@]} re-measured on request)…"
# The suite's exit status is CAPTURED, not discarded: a red node's duration is the cost of
# ERRORING, and the updater records it as a declared UNMEASURED hole (P1.28), never as a number.
# `-vv --durations=0`: every duration is printed, floor included. PYTEST_ADDOPTS is cleared, not
# appended to: it is the one channel that can inject `-n auto` from outside this script.
env -u PYTEST_ADDOPTS -u PYTEST_XDIST_AUTO_NUM_WORKERS \
    EDI_FIXTURE_COST_LOG="$COSTS" PYTHONPATH="$ROOT/tools/checks${PYTHONPATH:+:$PYTHONPATH}" \
    python -m pytest -vv "${TARGETS[@]}" -p no:cacheprovider -p no:xdist -p fixture_costs \
    --durations=0 -o addopts= >"$LOG" 2>&1 && SUITE_RC=0 || SUITE_RC=$?
tail -1 "$LOG"
if [ "$SUITE_RC" -ne 0 ]; then
    echo "NOTE: the run exited $SUITE_RC. Failing and unreached nodes will be recorded as" >&2
    echo "UNMEASURED, not as 0.000 - a failing node's duration is the cost of erroring." >&2
fi

if [ ! -f "$COSTS" ]; then
    echo "REFUSING: fixture-cost artifact $COSTS was not produced — pytest did not reach" >&2
    echo "sessionfinish in this run; a manifest written now would carry current durations" >&2
    echo "with missing module costs (the ~338 s defect this measurement exists to close)." >&2
    exit 1
fi

REMEASURE_FLAGS=()
for node in "${REMEASURE[@]}"; do REMEASURE_FLAGS+=(--remeasure "$node"); done
python tools/checks/per_pr_runtimes.py --update "$LOG" \
    --fixture-costs "$COSTS" "${REMEASURE_FLAGS[@]}"
echo "durations log kept at $LOG; fixture costs at $COSTS"
