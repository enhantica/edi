# SPDX-License-Identifier: BSD-3-Clause
"""Bank and check the pattern chart's and the structure view's latencies.

  latency_bank.py --check --table <table.json> --bank <bank.json>
      compare one measurement table with the bank: a ratcheted median above its banked value plus
      the margin is a regression; one below the banked value minus the margin passes and is
      reported as a re-bank due (the ratchet fails only on slowdowns: decision 2026-10-03)
  latency_bank.py --check --measurements <directory> --bank <bank.json>
      the same, for the median of the directory's ten tables (the value a bank row would hold)
  latency_bank.py --measurements <directory> --bank <bank.json> [--out <file>] [--decision <text>]
      write the machine's bank rows from exactly ten tables of one machine and one commit
  latency_bank.py --run --bank <bank.json> [--out <file>] [--decision <text>]
      run every latency probe that is built ten times, then write the rows as above
  latency_bank.py --collect <log> --table <table.json>
      write one table from one run of the drawn cases (tools/ci/app-test-3d.sh): their A1 and A2
      records, with the machine, the commit and the graphics renderer
  latency_bank.py --run-app [--tables <dir>] --bank <bank.json> [--out <file>] [--decision <text>]
      run the drawn cases ten times and collect a table from each; compare the tables' medians
      with the bank; then, unless they lie within it, write the rows as above
  latency_bank.py --accept <table.json>... --bank <bank.json> [--out <file>] --decision <text>
      set one machine's banked native medians to the medians a check measured (the median over
      the tables given), keeping each row's margin and its banked runs; only under a named
      decision, and never for app rows, which are banked from GPU hardware only (above)

With --out the bank is read and the result is written to <file>: the bank itself is not touched.
CI banks that way, so a run never compares a head with rows the same run wrote; the rows reach the
bank by a commit, and a later run is the first to be compared with them. Neither --out nor the
bank may lie inside the directory of tables, and only its run-NN.json tables are read: a repeat run
never reads an earlier run's output as a measurement.

Every bank row names the committed revision it measured. --run and --run-app measure the checkout's
HEAD and refuse a checkout whose tracked files differ from it (the bank file excepted). Each timed
executable names the commit it was built from itself. A latency probe carries
"edi-build-commit:<sha>" in its bytes: --run reads it from the file it is about to run, refuses one
built from another commit, and hands it to that probe to record (EDI_TEST_COMMIT). The app test
runner prints "edi_app_tests: built at <sha>" first: a drawn run's table takes it, and --run-app
refuses a runner built from another commit. A table naming no revision (an archived log without
that line, a build made with uncommitted changes, or "unrecorded") is reported and never banked.

A machine's rows come in two families, replaced separately: the core probes' (S, V) and the
app's. Banking one family keeps the other's rows. The app's rows are banked from GPU hardware
only: a table drawn by a software renderer (Mesa's llvmpipe on the development VM), or one whose
drawn cases do not allow banking, is refused, and checked it is reported and never compared (M7).

No latency value is an acceptance limit (owner, 2026-10-02): the bank only guards against a later
change making the chart or the structure view slower (edi ADR-0020 §5, ADR-0017 §16). The tables
are written by the latency probes and collected from the drawn cases' printed records (the hidden
Qt Quick Test tier's); this tool never measures anything itself. Every refusal exits 1 naming its
cause.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
# The probes, in order; a run measures every one that is built, and one table holds all their rows.
PROBES = (
    ROOT / 'build' / 'ci' / 'core' / 'e04_t9_latency_probe',
    ROOT / 'build' / 'ci' / 'core' / 'e04_t10_latency_probe',
)
SCHEMA = 1
RUNS = 10
FLOOR_MS = 1.0
HAND_PREFIX = 'hand:'
# The ratcheted metrics by scenario: medians only. A p95's margin would be too wide to catch
# anything (table M3), so the p95 is reported and never compared. The structure view's V1
# presentation and V2 update overhead, medians too; V2's latency and calculation are reported
# and not compared. The app's A1 frame and A2 update medians, from GPU hardware only.
RATCHETED = {
    'S1': ('latency', 'overhead'),
    'S2': ('latency', 'overhead'),
    'S3': ('presentation',),
    'V1': ('presentation',),
    'V2': ('overhead',),
    'A1': ('frame',),
    'A2': ('update',),
}
APP_SCENARIOS = ('A1', 'A2')
# The drawn cases: their runner, and what each record must carry (at least 50 samples after 5
# discarded) and may carry for the report (M4: A1's mesh detail and atom and bond counts, A2's
# calculation share).
DRAWN = ROOT / 'tools' / 'ci' / 'app-test-3d.sh'
MIN_SAMPLES = 50
MIN_WARMUPS = 5
REPORTED = {'A1': ('detail', 'atoms', 'bonds'), 'A2': ('calculation',)}
RECORD = re.compile(r'qml: (\{.*\})\s*$')
# Review 4 F1: a measured revision is a full commit sha; the app test runner prints the one it was
# built from (app/tests/app_tests_main.cpp), `<sha>-dirty` for a build with uncommitted changes.
SHA = re.compile(r'[0-9a-f]{40}')
BUILT_AT = re.compile(r'^edi_app_tests: built at (\S+)$', re.MULTILINE)
# Review 5 F1: the marker a latency probe carries in its bytes (cmake/build_commit.cmake, MARKER).
MARKER = re.compile(rb'edi-build-commit:([0-9a-f]{40}(?:-dirty)?|unknown)\n')
# Review 4 F2: the tables a run writes, and the only files a directory of measurements is read for.
TABLES = 'run-*.json'
# Software rasterisers, by their renderer string (lower case): their frames are never banked.
SOFTWARE_RENDERERS = ('llvmpipe', 'softpipe', 'swrast', 'lavapipe', 'swiftshader', 'basic render')


class RefusedError(Exception):
    """A precondition failed, or the check found a regression or a re-bank obligation."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


def read_json(path: Path, what: str) -> dict:
    """Return the JSON object in ``path``, which must carry this tool's schema."""
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        refuse(f'{what} {path} cannot be read: {error}')
    if not isinstance(loaded, dict) or loaded.get('schema') != SCHEMA:
        refuse(f'{what} {path} is not schema {SCHEMA}')
    return loaded


def finite(value: object, what: str) -> float:
    """Return ``value`` as a float; refuse anything that is not a finite number."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        refuse(f'{what} is not a finite number: {value!r}')
    return float(value)


def table_medians(table: dict) -> dict[tuple[str, str, str], float]:
    """Return the table's ratcheted medians by (dataset, scenario, metric)."""
    medians: dict[tuple[str, str, str], float] = {}
    for row in table.get('rows', []):
        dataset, scenario = row.get('dataset'), row.get('scenario')
        for metric in RATCHETED.get(scenario, ()):
            value = (row.get(metric) or {}).get('median_ms')
            if value is None:
                refuse(f'the table has no {metric}.median_ms for {dataset} {scenario}')
            what = f"the table's {metric}.median_ms for {dataset} {scenario}"
            medians[dataset, scenario, metric] = finite(value, what)
    if not medians:
        refuse('the table has no ratcheted row')
    return medians


def bank_rows(bank: dict, machine: str) -> dict[tuple[str, str], dict]:
    """Return ``machine``'s bank rows by (dataset, scenario); empty when it has none."""
    rows = (bank.get('machines', {}).get(machine) or {}).get('rows', [])
    return {(row.get('dataset'), row.get('scenario')): row for row in rows}


def is_app(scenario: object) -> bool:
    """Whether ``scenario`` is one of the app's (the A family), not the core probes'."""
    return scenario in APP_SCENARIOS


def software(renderer: str) -> bool:
    """Whether ``renderer`` names a software rasteriser."""
    name = renderer.lower()
    return any(marker in name for marker in SOFTWARE_RENDERERS)


def named(value: object) -> bool:
    """Whether ``value`` is a name: a non-blank string, as it arrived.

    Evidence is checked raw, never coerced first: ``str()`` would turn JSON null into "None" and a
    boolean, a number or a container into another valid-looking name.
    """
    return isinstance(value, str) and bool(value.strip())


def same(tables: list[dict], key: str) -> bool:
    """Whether every table carries the same raw ``key`` value, its JSON type included."""
    return len({json.dumps(table.get(key), sort_keys=True) for table in tables}) == 1


def machine_of(table: dict) -> str:
    """Return the machine a table names; refuse anything that is not a name."""
    machine = table.get('machine')
    if not named(machine):
        refuse(f'the table names no machine: {machine!r}')
    return machine


def app_renderer(table: dict) -> str:
    """Return the renderer that drew a table's app rows; refuse a table that names none."""
    renderer = table.get('renderer')
    if not named(renderer):
        refuse(f'the table has app rows and names no graphics renderer: {renderer!r}')
    return renderer


def check(table_path: Path | None, bank_path: Path, measurements: Path | None = None) -> str:
    """Compare a table, or ten tables' medians, with the bank; refuse on any finding."""
    if measurements is not None:
        table = median_table(read_tables(measurements))
    elif table_path is not None:
        table = read_json(table_path, 'the table')
    else:
        refuse('--check needs --table or --measurements')
    findings, notes = compare(table, read_json(bank_path, 'the bank'))
    if findings:
        refuse('\n'.join(findings))
    return '\n'.join(notes)


def compare(table: dict, bank: dict) -> tuple[list[str], list[str]]:
    """Return a table's findings against the bank, and the report's lines."""
    machine = machine_of(table)
    rows = bank_rows(bank, machine)
    medians = table_medians(table)
    notes = []
    if any(is_app(scenario) for _, scenario, _ in medians):
        # The app's rows are compared only when drawn on GPU hardware and banked for this machine.
        renderer = app_renderer(table)
        skipped = ''
        if software(renderer):
            skipped = (
                f'{renderer} is software rendering: the app rows are reported, never compared'
            )
        elif not any(is_app(scenario) for _, scenario in rows):
            skipped = (
                f'{machine} has no app bank rows: the app rows are reported, nothing compared'
            )
        if skipped:
            notes.append(f'latency-bank: {skipped}')
            medians = {key: value for key, value in medians.items() if not is_app(key[1])}
    if any(not is_app(key[1]) for key in medians) and not any(
        not is_app(scenario) for _, scenario in rows
    ):
        if not machine.startswith(HAND_PREFIX):
            what = machine or 'this machine'
            return [f'{what} has no bank rows: a CI machine is banked before it gates'], notes
        notes.append(f'latency-bank: {machine} has no bank rows: reported, nothing compared')
        medians = {key: value for key, value in medians.items() if is_app(key[1])}
    findings, due = [], []
    for (dataset, scenario, metric), value in sorted(medians.items()):
        banked = (rows.get((dataset, scenario)) or {}).get('metrics', {}).get(metric)
        if banked is None:
            findings.append(f'{dataset} {scenario} {metric}: no bank row on {machine}')
            continue
        what = f"the bank's {dataset} {scenario} {metric}"
        centre = finite(banked.get('banked_ms'), f'{what} banked_ms')
        margin = finite(banked.get('margin_ms'), f'{what} margin_ms')
        if margin < 0.0:
            refuse(f'{what} margin_ms is negative: {margin!r}')
        if value > centre + margin:
            findings.append(
                f'{dataset} {scenario} {metric}: regression: {value:.3f} ms is above the banked '
                f'{centre:.3f} ms plus the margin {margin:.3f} ms'
            )
        elif value < centre - margin:
            due.append(
                f'latency-bank: {dataset} {scenario} {metric}: re-bank due: {value:.3f} ms is '
                f'below the banked {centre:.3f} ms minus the margin {margin:.3f} ms'
            )
    notes.extend(due)
    if medians and not findings and not due:
        notes.append(
            f'latency-bank: every ratcheted median of {machine} lies within its banked margin'
        )
    return findings, notes


def gpu_renderer(tables: list[dict]) -> str:
    """Return the GPU renderer that drew ten tables' app rows; refuse any other.

    M5, M7: the app's rows are banked from GPU hardware only. Both labels must allow it: this
    tool's reading of the renderer, and the drawn cases' own.
    """
    renderers = [app_renderer(table) for table in tables]
    if len(set(renderers)) != 1:
        refuse('the tables do not share one renderer')
    renderer = renderers[0]
    if software(renderer):
        refuse(f'{renderer} is software rendering: the app rows are banked from GPU hardware only')
    if any(table.get('bank_allowed') is not True for table in tables):
        refuse('the drawn cases did not allow banking these app rows (bankAllowed)')
    return renderer


def assemble(tables: list[dict], previous: dict[tuple[str, str], dict], decision: str) -> list:
    """Return one machine's bank rows from ten tables of one machine and one commit."""
    if len(tables) != RUNS:
        refuse(f'a bank row comes from exactly {RUNS} tables, not {len(tables)}')
    for key in ('machine', 'commit'):
        if not same(tables, key):
            refuse(f'the tables do not share one {key}')
    machine_of(tables[0])
    commit = tables[0].get('commit')
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        refuse(
            f'the tables name no measured revision (commit {commit!r}): a bank row comes from a '
            'run that recorded the committed revision it measured (--run, --run-app)'
        )
    medians = [table_medians(table) for table in tables]
    if any(set(one) != set(medians[0]) for one in medians):
        refuse('the tables do not hold the same rows')
    renderer = gpu_renderer(tables) if any(is_app(key[1]) for key in medians[0]) else ''
    run = os.environ.get('GITHUB_RUN_ID', 'hand')
    if 'GITHUB_RUN_ATTEMPT' in os.environ:
        run += '/' + os.environ['GITHUB_RUN_ATTEMPT']
    rows: dict[tuple[str, str], dict] = {}
    for dataset, scenario, metric in sorted(medians[0]):
        values = [one[dataset, scenario, metric] for one in medians]
        banked = statistics.median(values)
        earlier = (previous.get((dataset, scenario)) or {}).get('metrics', {}).get(metric)
        if (
            earlier is not None
            and banked > finite(earlier.get('banked_ms'), 'a banked value')
            and not decision
        ):
            refuse(
                f'{dataset} {scenario} {metric}: the banked value would rise from '
                f'{earlier["banked_ms"]:.3f} to {banked:.3f} ms; a value moves up only '
                'with a committed owner decision, named with --decision'
            )
        row = rows.setdefault(
            (dataset, scenario),
            {
                'dataset': dataset,
                'scenario': scenario,
                'commit': str(tables[0].get('commit', '')),
                'run': run,
                'metrics': {},
            },
        )
        if decision:
            row['decision'] = decision
        if is_app(scenario):
            row['renderer'] = renderer
        row['metrics'][metric] = {
            'banked_ms': banked,
            'margin_ms': max(FLOOR_MS, 2.0 * (max(values) - min(values))),
            'values_ms': values,
        }
    return list(rows.values())


def write_bank(
    tables: list[dict], bank_path: Path, decision: str, out_path: Path | None = None
) -> str:
    """Write the tables' machine into the bank, replacing only that machine's rows of their family.

    The family is the core probes' or the app's: banking one keeps the machine's rows of the other.
    With ``out_path`` the bank is only read, and the bank with the machine's new rows goes there.
    """
    bank = read_json(bank_path, 'the bank') if bank_path.exists() else {'schema': SCHEMA}
    if not tables:
        refuse('the tables name no machine')
    machine = machine_of(tables[0])
    previous = bank_rows(bank, machine)
    rows = assemble(tables, previous, decision)
    families = {is_app(row['scenario']) for row in rows}
    kept = [row for (_, scenario), row in previous.items() if is_app(scenario) not in families]
    merged = sorted(
        kept + rows, key=lambda row: (str(row.get('dataset')), str(row.get('scenario')))
    )
    bank.setdefault('machines', {})[machine] = {'rows': merged}
    target = out_path if out_path is not None else bank_path
    target.write_text(json.dumps(bank, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return f'latency-bank: banked {len(rows)} row(s) for {machine} in {target}'


def git(*args: str) -> str:
    """Return the output of one git command in this checkout; refuse its failure."""
    done = subprocess.run(
        ['git', '-C', str(ROOT), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        refuse(f'git {" ".join(args)} failed: {done.stderr.strip()}')
    return done.stdout.strip()


def measured_revision(bank: Path) -> str:
    """Return the committed revision a run measures: the checkout's HEAD, with no tracked change.

    A run that builds and measures a tree differing from its HEAD measured no revision; the bank
    file, the run's own output, is the one path allowed to differ. On CI the checkout must be
    GITHUB_SHA.
    """
    head = git('rev-parse', 'HEAD')
    output = bank.resolve()
    changed = [
        path
        for path in git('diff', '--name-only', 'HEAD', '--').splitlines()
        if (ROOT / path).resolve() != output
    ]
    if changed:
        refuse(
            f'the checkout differs from HEAD {head} in {len(changed)} tracked path(s) (first: '
            f'{changed[0]}): a measurement names the committed revision it ran'
        )
    ci = os.environ.get('GITHUB_SHA')
    if ci and ci != head:
        refuse(f'GITHUB_SHA {ci} is not the checkout HEAD {head}')
    return head


def executable_build(executable: Path) -> str:
    """Return the commit ``executable`` says it was built from: its marker, '' when it has none."""
    try:
        found = set(MARKER.findall(executable.read_bytes()))
    except OSError as error:
        refuse(f'{executable} cannot be read: {error}')
    if len(found) > 1:
        refuse(f'{executable} carries more than one build commit: {sorted(found)}')
    return found.pop().decode() if found else ''


def measure(directory: Path, revision: str) -> None:
    """Run every built latency probe ten times into ``directory``: one table per run, all rows.

    The probes measure ``revision``. Before each run the probe's own marker, read from the file
    that is about to run, must name it (an extension built elsewhere, or a probe left from an
    older build, can no longer answer for the timed binary); the probe is handed that commit
    (EDI_TEST_COMMIT) and must record it.
    """
    probes = [probe for probe in PROBES if probe.exists()]
    if not probes:
        names = ', '.join(probe.name for probe in PROBES)
        refuse(f'no latency probe is built ({names}): run `pixi run core-build` first')
    table = ROOT / 'latency-table.json'
    for index in range(RUNS):
        merged: dict | None = None
        for probe in probes:
            built = executable_build(probe)
            if built != revision:
                refuse(
                    f'{probe} was built from {built or "an unnamed commit"}, '
                    f'not from the measured HEAD {revision}: rebuild build/ci '
                    '(`pixi run core-build`)'
                )
            table.unlink(missing_ok=True)
            done = subprocess.run(
                [str(probe)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                env={**os.environ, 'EDI_TEST_COMMIT': built},
            )
            if done.returncode != 0 or not table.exists():
                refuse(f'{probe.name} failed on run {index + 1} (exit {done.returncode})')
            one = read_json(table, f'the table of {probe.name}')
            table.unlink()
            if str(one.get('commit', '')) != revision:
                refuse(f'{probe.name} recorded commit {one.get("commit")!r}, not {revision}')
            if merged is None:
                merged = one
                continue
            for key in ('machine', 'commit'):
                if str(one.get(key, '')) != str(merged.get(key, '')):
                    refuse(f'{probe.name} names another {key} on run {index + 1}')
            merged['rows'] = list(merged.get('rows', [])) + list(one.get('rows', []))
        out = directory / f'run-{index + 1:02d}.json'
        out.write_text(json.dumps(merged, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def read_tables(directory: Path) -> list[dict]:
    """Return the run tables in ``directory`` (``run-NN.json``, in name order), and nothing else.

    Review 4 F2: an output left there, a bank above all, is never read as a measurement.
    """
    tables = []
    for path in sorted(directory.glob(TABLES)):
        table = read_json(path, 'the table')
        if 'machines' in table or not isinstance(table.get('rows'), list):
            refuse(f'{path} is not a measurement table')
        tables.append(table)
    return tables


def outside(directory: Path, *outputs: Path | None) -> None:
    """Refuse an output inside a directory of measurements: a later run would find it there."""
    root = directory.resolve()
    for output in outputs:
        if output is not None and (output.resolve() == root or root in output.resolve().parents):
            refuse(
                f'{output} is inside the directory of measurements {directory}: write it elsewhere'
            )


def median_table(tables: list[dict]) -> dict:
    """Return one table holding the median of each ratcheted median over ``tables``."""
    if not tables:
        refuse('no table to take medians of')
    for key in ('machine', 'commit', 'renderer'):
        if not same(tables, key):
            refuse(f'the tables do not share one {key}')
    machine_of(tables[0])
    medians = [table_medians(table) for table in tables]
    if any(set(one) != set(medians[0]) for one in medians):
        refuse('the tables do not hold the same rows')
    if any(is_app(scenario) for _, scenario, _ in medians[0]):
        app_renderer(tables[0])
    rows: dict[tuple[str, str], dict] = {}
    for dataset, scenario, metric in sorted(medians[0]):
        row = rows.setdefault((dataset, scenario), {'dataset': dataset, 'scenario': scenario})
        value = statistics.median(one[dataset, scenario, metric] for one in medians)
        row[metric] = {'median_ms': value}
    table = {
        key: tables[0][key]
        for key in ('schema', 'machine', 'commit', 'renderer')
        if key in tables[0]
    }
    table['rows'] = list(rows.values())
    return table


def machine_key() -> str:
    """Return this machine's bank key, as the latency probes name it: the runner, else the host."""
    return os.environ.get('RUNNER_NAME') or HAND_PREFIX + os.environ.get('HOSTNAME', 'unknown')


def timing(record: dict, metric: str, what: str) -> dict:
    """Return a record's ``metric`` as a finite median and p95; refuse anything else."""
    value = record.get(metric)
    if not isinstance(value, dict):
        refuse(f'{what} has no {metric}')
    return {
        'median_ms': finite(value.get('median_ms'), f'{what} {metric}.median_ms'),
        'p95_ms': finite(value.get('p95_ms'), f'{what} {metric}.p95_ms'),
    }


def app_record(line: str) -> dict | None:
    """Return the app record a log line prints, if it prints one."""
    found = RECORD.search(line)
    if found is None:
        return None
    try:
        record = json.loads(found.group(1))
    except ValueError:
        return None
    return record if isinstance(record, dict) and is_app(record.get('scenario')) else None


def app_row(record: dict, what: str) -> tuple[dict, list[str]]:
    """Return a drawn record's table row, and the report fields it lacks (M4); refuse a bad one."""
    dataset, scenario = record.get('dataset'), record['scenario']
    if not isinstance(dataset, str) or not dataset:
        refuse(f'{what}: a {scenario} record names no dataset')
    name = f'{what}: the {dataset} {scenario} record'
    samples, warmups = record.get('samples'), record.get('warmups')
    if not isinstance(samples, int) or samples < MIN_SAMPLES:
        refuse(f'{name} has {samples!r} samples, not at least {MIN_SAMPLES}')
    if not isinstance(warmups, int) or warmups < MIN_WARMUPS:
        refuse(f'{name} discarded {warmups!r} warm-ups, not at least {MIN_WARMUPS}')
    metric = RATCHETED[scenario][0]
    row = {'dataset': dataset, 'scenario': scenario, metric: timing(record, metric, name)}
    missing = []
    for field in REPORTED[scenario]:
        if field not in record:
            missing.append(f'{dataset} {scenario} {field}')
        elif field == 'calculation':
            row[field] = timing(record, field, name)
        else:
            row[field] = record[field]
    return row, missing


def collect(log: str, what: str) -> tuple[dict, list[str]]:
    """Return the table of one drawn run's log, and the report fields its records lack (M4).

    The drawn cases print one JSON record per dataset and app metric (``qml: {...}`` lines); the
    table adds the machine, as the latency probes' tables carry it, and the commit the runner says
    it was built from (empty when the log has no such line).
    """
    rows: dict[tuple[str, str], dict] = {}
    records = [record for record in map(app_record, log.splitlines()) if record is not None]
    missing = []
    for record in records:
        row, gaps = app_row(record, what)
        key = (row['dataset'], row['scenario'])
        if key in rows:
            refuse(f'{what}: the {key[0]} {key[1]} record appears twice')
        rows[key] = row
        missing += gaps
    for scenario in APP_SCENARIOS:
        if not any(key[1] == scenario for key in rows):
            refuse(f'{what} holds no {scenario} record')
    for record in records:
        if not named(record.get('renderer')):
            refuse(
                f'{what}: the {record.get("dataset")} {record["scenario"]} record names no '
                f'graphics renderer: {record.get("renderer")!r}'
            )
    renderers = {record['renderer'] for record in records}
    if len(renderers) != 1:
        refuse(f'{what}: the records do not name one renderer: {sorted(renderers)}')
    counts = {(record['samples'], record['warmups']) for record in records}
    if len(counts) != 1:
        refuse(f'{what}: the records do not share one sample and warm-up count')
    renderer = renderers.pop()
    samples, warmups = counts.pop()
    # The commit is the runner's own statement of its build, never the environment's.
    builds = set(BUILT_AT.findall(log))
    if len(builds) > 1:
        refuse(f'{what}: the runs name more than one build: {sorted(builds)}')
    table = {
        'schema': SCHEMA,
        'machine': machine_key(),
        'commit': builds.pop() if builds else '',
        'samples': samples,
        'warmups': warmups,
        'renderer': renderer,
        'software': software(renderer),
        'bank_allowed': not software(renderer)
        and all(record.get('bankAllowed') is True for record in records),
        'rows': [rows[key] for key in sorted(rows)],
    }
    return table, missing


def measure_app(directory: Path, revision: str) -> list[str]:
    """Run the drawn cases ten times; keep each run's log and table; return the M4 gaps.

    The runner must have been built from ``revision``. The directory's earlier run files go first,
    so its tables are this run's ten.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for earlier in (*directory.glob(TABLES), *directory.glob('run-*.log')):
        earlier.unlink()
    missing: set[str] = set()
    for index in range(RUNS):
        done = subprocess.run(
            ['bash', str(DRAWN)], cwd=ROOT, check=False, capture_output=True, text=True
        )
        log = directory / f'run-{index + 1:02d}.log'
        log.write_text(done.stdout + done.stderr, encoding='utf-8')
        if done.returncode != 0:
            refuse(f'the drawn cases failed on run {index + 1} (exit {done.returncode}): {log}')
        table, gaps = collect(done.stdout, f'run {index + 1}')
        if table['commit'] != revision:
            refuse(
                f'the drawn runner was built from {table["commit"] or "an unnamed commit"}, not '
                f'from the measured HEAD {revision}: run `pixi run -e app app-build`'
            )
        missing.update(gaps)
        out = directory / f'run-{index + 1:02d}.json'
        out.write_text(json.dumps(table, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return sorted(missing)


def run_app_in(options: argparse.Namespace) -> str:
    """Run --run-app in the --tables directory, or in a scratch one when none is named."""
    if options.tables is not None:
        return run_app(options, options.tables)
    with tempfile.TemporaryDirectory() as scratch:
        return run_app(options, Path(scratch))


def run_app(options: argparse.Namespace, directory: Path) -> str:
    """Measure the drawn cases ten times, compare their medians with the bank, then bank them.

    The rows are written unless the comparison found every compared median within its margin: the
    first GPU run banks, a regression is refused, and a run faster than the margin owes the
    re-bank it writes.
    """
    outside(directory, options.out, options.bank)
    missing = measure_app(directory, measured_revision(options.bank))
    tables = read_tables(directory)
    bank = read_json(options.bank, 'the bank') if options.bank.exists() else {'schema': SCHEMA}
    findings, notes = compare(median_table(tables), bank)
    lines = [f'latency-bank: the drawn tables are in {directory}', *notes]
    if missing:
        lines.append('latency-bank: the drawn records do not report (M4): ' + ', '.join(missing))
    within = not findings and any(line.endswith('within its banked margin') for line in notes)
    if not within:
        try:
            lines.append(write_bank(tables, options.bank, options.decision, options.out))
        except RefusedError as refusal:
            findings.append(str(refusal))
    if findings:
        refuse('\n'.join(lines + findings))
    return '\n'.join(lines)


def accept(table_paths: list[Path], bank_path: Path, decision: str, out_path: Path | None) -> str:
    """Set one machine's banked medians to what a check measured; return the before/after report.

    The CI check measured the probes above the banked medians, and the owner accepted the check's
    values. Every ratcheted median the tables hold becomes the median over the tables; each row
    keeps the margin its banked runs gave and those runs, and records the value it replaced, the
    measured values and their commits. A row the tables do not hold is unchanged. Native medians
    only: a table holding an app row (A1, A2) is refused before anything is read from or written to
    the bank, since the app's rows are banked from GPU hardware by the writer that checks it
    (gpu_renderer).
    """
    if not decision:
        refuse('--accept sets banked values from a decision: name it with --decision')
    tables = [read_json(path, 'the table') for path in table_paths]
    if not tables:
        refuse('--accept needs at least one table')
    machine = machine_of(tables[0])
    if not same(tables, 'machine'):
        refuse('the tables do not name one machine')
    for table in tables:
        commit = table.get('commit')
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            refuse(f'a table names no measured revision (commit {table.get("commit")!r})')
    medians = [table_medians(table) for table in tables]
    app = sorted({scenario for one in medians for _, scenario, _ in one if is_app(scenario)})
    if app:
        refuse(
            f'--accept sets native medians only; the tables hold app rows ({", ".join(app)}), '
            'which are banked from GPU hardware by --run-app or --measurements'
        )
    if any(set(one) != set(medians[0]) for one in medians):
        refuse('the tables do not hold the same rows')
    bank = read_json(bank_path, 'the bank')
    rows = bank_rows(bank, machine)
    lines = [f'latency-bank: {machine}, under "{decision}":']
    for dataset, scenario, metric in sorted(medians[0]):
        row = rows.get((dataset, scenario))
        banked = (row or {}).get('metrics', {}).get(metric)
        if banked is None:
            refuse(f'{dataset} {scenario} {metric} has no bank row on {machine} to set')
        measured = [one[dataset, scenario, metric] for one in medians]
        before = finite(banked.get('banked_ms'), f"the bank's {dataset} {scenario} {metric}")
        banked['banked_ms'] = statistics.median(measured)
        banked['accepted'] = {
            'replaced_ms': before,
            'measured_ms': measured,
            'commits': [str(table['commit']) for table in tables],
        }
        row['decision'] = decision
        lines.append(
            f'  {dataset} {scenario} {metric}: {before:.3f} -> {banked["banked_ms"]:.3f} ms '
            f'(margin {banked["margin_ms"]:.3f} ms)'
        )
    target = out_path if out_path is not None else bank_path
    target.write_text(json.dumps(bank, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines.append(f'latency-bank: wrote {target}')
    return '\n'.join(lines)


def report_for(options: argparse.Namespace) -> str:
    """Run the mode ``options`` names and return its report."""
    if options.check:
        return check(options.table, options.bank, options.measurements)
    if options.accept:
        return accept(options.accept, options.bank, options.decision, options.out)
    if options.collect is not None:
        if options.table is None:
            refuse('--collect needs --table')
        try:
            log = options.collect.read_text(encoding='utf-8', errors='replace')
        except OSError as error:
            refuse(f'the log {options.collect} cannot be read: {error}')
        table, missing = collect(log, str(options.collect))
        options.table.write_text(
            json.dumps(table, indent=2, sort_keys=True) + '\n', encoding='utf-8'
        )
        built = table['commit'] or 'no build commit in the log'
        report = f'latency-bank: wrote {options.table} ({table["renderer"]}; built at {built})'
        if missing:
            report += '\nlatency-bank: the drawn records do not report (M4): ' + ', '.join(missing)
        return report
    if options.run_app:
        return run_app_in(options)
    if options.measurements is not None:
        outside(options.measurements, options.out, options.bank)
        return write_bank(
            read_tables(options.measurements), options.bank, options.decision, options.out
        )
    if options.run:
        revision = measured_revision(options.bank)
        with tempfile.TemporaryDirectory() as scratch:
            measure(Path(scratch), revision)
            return write_bank(
                read_tables(Path(scratch)), options.bank, options.decision, options.out
            )
    refuse('one of --check, --measurements, --run, --collect, --run-app or --accept is needed')


def main(argv: list[str]) -> int:
    """Run one of the three modes; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--run-app', action='store_true')
    parser.add_argument('--collect', type=Path)
    parser.add_argument('--tables', type=Path)
    parser.add_argument('--table', type=Path)
    parser.add_argument('--measurements', type=Path)
    parser.add_argument('--bank', type=Path, default=ROOT / 'tests' / 'latency-bank.json')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--decision', default='')
    parser.add_argument('--accept', type=Path, nargs='+')
    options = parser.parse_args(argv)
    try:
        report = report_for(options)
    except RefusedError as refusal:
        sys.stderr.write(f'latency-bank: REFUSED\n{refusal}\n')
        return 1
    sys.stdout.write(report + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
