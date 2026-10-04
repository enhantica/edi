"""I5: runtime attribution is serial and its manifest writer is exclusive."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASH = shutil.which('bash')
assert BASH is not None
RULING_17_PROVENANCE = {
    'measurement_platform': 'linux',
    'measurement_source': 'local',
}


def _write_executable(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding='utf-8')
    path.chmod(0o755)


def _sandbox(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    scratch = tmp_path / 'edi-measurement'
    runner = scratch / 'tools/ci/per-pr-measure.sh'
    runner.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/per-pr-measure.sh', runner)
    (scratch / 'tools/checks').mkdir(parents=True)
    (scratch / 'tests').mkdir()
    (scratch / 'build').mkdir()

    fake = r"""#!/usr/bin/env python3
import json
import os
import shlex
import sys
import time
from pathlib import Path

trace = Path(os.environ['C11_TRACE'])
run_id = os.environ.get('C11_RUN_ID', 'one')
args = sys.argv[1:]


def append(line):
    with trace.open('a', encoding='utf-8') as handle:
        handle.write(line + '\n')


def has_pair(left, right):
    return any(a == left and b == right for a, b in zip(args, args[1:]))


is_pytest = Path(sys.argv[0]).name == 'pytest' or args[:2] == ['-m', 'pytest']
if is_pytest:
    pytest_args = args[2:] if args[:2] == ['-m', 'pytest'] else args
    args = pytest_args
    env_parallel = '-n' in shlex.split(os.environ.get('PYTEST_ADDOPTS', ''))
    config_parallel = os.environ.get('C11_CONFIG_PARALLEL') == '1' and not has_pair(
        '-o', 'addopts='
    )
    plugin_parallel = os.environ.get('C11_AUTO_XDIST') == '1' and not has_pair(
        '-p', 'no:xdist'
    )
    explicit_parallel = any(
        arg == '-n' or arg.startswith(('-n=', '--numprocesses')) for arg in args
    )
    parallel = (
        os.environ.get('C11_FORCE_PARALLEL') == '1'
        or env_parallel
        or config_parallel
        or plugin_parallel
        or explicit_parallel
    )
    mode = 'parallel' if parallel else 'serial'
    append(f'RUN\t{run_id}\t{mode}')
    fixture_costs = os.environ.get('EDI_FIXTURE_COST_LOG')
    if fixture_costs:
        Path(fixture_costs).write_text(json.dumps({}), encoding='utf-8')
    started = Path(os.environ['C11_STARTED'])
    started.mkdir(parents=True, exist_ok=True)
    (started / run_id).touch()
    if run_id == 'first':
        release = Path(os.environ['C11_RELEASE'])
        for _ in range(500):
            if release.exists():
                break
            time.sleep(0.01)
        else:
            raise SystemExit(92)
    if parallel:
        print('created: 2/2 workers')
        print('[gw0] [ 50%] tests/unit/py/test_one.py::test_one')
        print('[gw1] [100%] tests/integration/py/test_two.py::test_two')
    print('0.05s call tests/unit/py/test_one.py::test_one')
    print('0.10s call tests/integration/py/test_two.py::test_two')
    print('2 passed in 0.20s')
    raise SystemExit(0)

if '--added-nodes' in args:
    if os.environ.get('C11_NO_ADDED') != '1':
        print('tests/unit/py/test_one.py::test_one')
        print('tests/integration/py/test_two.py::test_two')
    raise SystemExit(0)

if '--update' in args:
    append(f'UPDATE\t{run_id}')
    Path('tests/per-pr-runtimes.tsv').write_text(
        f'# writer={run_id}\n0.100\ttests/unit/py/test_one.py::test_one\n',
        encoding='utf-8',
    )
    raise SystemExit(0)

print('unexpected fake-python invocation: ' + repr(args), file=sys.stderr)
raise SystemExit(97)
"""
    fake_bin = scratch / 'fake-bin'
    _write_executable(fake_bin / 'python', fake)
    _write_executable(fake_bin / 'pytest', fake)

    trace = scratch / 'trace.tsv'
    environment = os.environ.copy()
    environment.update({
        'PATH': f'{fake_bin}:{environment["PATH"]}',
        'LOG': str(scratch / 'build/durations.txt'),
        'C11_TRACE': str(trace),
        'C11_STARTED': str(scratch / 'started'),
        'C11_RELEASE': str(scratch / 'release'),
        'PYTEST_ADDOPTS': '',
        'C11_CONFIG_PARALLEL': '0',
        'C11_AUTO_XDIST': '0',
    })
    return scratch, environment, trace


def _run(scratch: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, 'tools/ci/per-pr-measure.sh'],
        cwd=scratch,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_i5_stale_only_collection_reaches_banker_without_rerunning(tmp_path: Path) -> None:
    scratch, environment, trace = _sandbox(tmp_path)
    completed = _run(scratch, environment | {'C11_NO_ADDED': '1'})

    assert completed.returncode == 0, (
        'the stale-only collection must reach the banker successfully; '
        f'output={completed.stdout}{completed.stderr}'
    )
    assert trace.read_text(encoding='utf-8').splitlines() == ['UPDATE\tone'], (
        'a stale-only collection must reach the updater without running pytest again'
    )


def _runtime_checker() -> ModuleType:
    path = ROOT / 'tools/checks/per_pr_runtimes.py'
    spec = importlib.util.spec_from_file_location('c11_t41_edi_runtime_checker', path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ('field', 'replacement'),
    [
        pytest.param('measurement_platform', None, id='missing-platform'),
        pytest.param('measurement_platform', 'macos', id='wrong-platform'),
        pytest.param('measurement_source', None, id='missing-source'),
        pytest.param('measurement_source', 'ci', id='wrong-source'),
    ],
)
def test_i5_ruling_17_provenance_is_validated(
    tmp_path: Path,
    field: str,
    replacement: str | None,
) -> None:
    checker = _runtime_checker()
    manifest = (ROOT / 'tests/per-pr-runtimes.tsv').read_text(encoding='utf-8')
    expected = RULING_17_PROVENANCE[field]
    declaration = f'# {field} = {expected}\n'
    assert manifest.count(declaration) == 1
    mutated = manifest.replace(
        declaration,
        '' if replacement is None else f'# {field} = {replacement}\n',
        1,
    )
    path = tmp_path / 'per-pr-runtimes.tsv'
    path.write_text(mutated, encoding='utf-8')

    with pytest.raises(checker.ManifestError, match=field):
        checker.load_manifest(path)


def test_i5_ruling_17_provenance_is_regenerated() -> None:
    checker = _runtime_checker()
    rendered = checker.render_manifest(
        {'tests/unit/py/test_one.py::test_one': 0.001},
        provenance=[],
    )

    for field, expected in RULING_17_PROVENANCE.items():
        assert rendered.count(f'# {field} = {expected}\n') == 1


def test_i5_measurement_neutralizes_parallel_pytest_defaults(tmp_path: Path) -> None:
    scratch, environment, trace = _sandbox(tmp_path)
    environment.update({
        'PYTEST_ADDOPTS': '-n 2',
        'C11_CONFIG_PARALLEL': '1',
        'C11_AUTO_XDIST': '1',
    })
    result = _run(scratch, environment)

    assert result.returncode == 0, result.stdout + result.stderr
    assert trace.read_text(encoding='utf-8').splitlines() == [
        'RUN\tone\tserial',
        'UPDATE\tone',
    ]


def test_i5_parallel_attribution_cannot_write_the_runtime_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = _runtime_checker()
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    sentinel = 'manifest must remain untouched\n'
    manifest.write_text(sentinel, encoding='utf-8')
    log = tmp_path / 'parallel-durations.txt'
    log.write_text(
        'created: 2/2 workers\n'
        '[gw0] [ 50%] tests/unit/py/test_one.py::test_one\n'
        '[gw1] [100%] tests/integration/py/test_two.py::test_two\n'
        '0.05s call tests/unit/py/test_one.py::test_one\n'
        '0.10s call tests/integration/py/test_two.py::test_two\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(checker, 'MANIFEST', manifest)
    monkeypatch.setattr(
        checker,
        'collect_nodeids',
        lambda: [
            'tests/unit/py/test_one.py::test_one',
            'tests/integration/py/test_two.py::test_two',
        ],
    )

    # Completion evidence is mandatory now (review-22 F1), so both calls supply it: the subject
    # here is parallel-vs-serial attribution, and it must be exercised through a VALID invocation
    # rather than accidentally passing because a different refusal fired first.
    costs = tmp_path / 'fixture-costs.json'
    costs.write_text(
        '{"module_costs": {}, "completed": ['
        '"tests/unit/py/test_one.py::test_one", '
        '"tests/integration/py/test_two.py::test_two"]}',
        encoding='utf-8',
    )

    assert checker.update(log, costs) != 0, 'a parallel durations log must be refused'
    assert manifest.read_text(encoding='utf-8') == sentinel

    serial = tmp_path / 'serial-durations.txt'
    serial.write_text(
        '0.05s call tests/unit/py/test_one.py::test_one\n'
        '0.10s call tests/integration/py/test_two.py::test_two\n',
        encoding='utf-8',
    )
    assert checker.update(serial, costs) == 0
    assert manifest.read_text(encoding='utf-8') != sentinel


def test_i5_overlapping_measurements_never_run_or_write_concurrently(tmp_path: Path) -> None:
    scratch, environment, trace = _sandbox(tmp_path)
    first_env = environment | {'C11_RUN_ID': 'first'}
    second_env = environment | {'C11_RUN_ID': 'second'}
    first = subprocess.Popen(
        [BASH, 'tools/ci/per-pr-measure.sh'],
        cwd=scratch,
        env=first_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    second: subprocess.Popen[str] | None = None
    started = scratch / 'started/first'
    lines_during_first: list[str] = []
    try:
        for _ in range(200):
            if started.exists():
                break
            time.sleep(0.01)
        if started.exists():
            second = subprocess.Popen(
                [BASH, 'tools/ci/per-pr-measure.sh'],
                cwd=scratch,
                env=second_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(100):
                lines_during_first = (
                    trace.read_text(encoding='utf-8').splitlines() if trace.exists() else []
                )
                if 'RUN\tsecond\tserial' in lines_during_first or second.poll() is not None:
                    break
                time.sleep(0.01)
    finally:
        (scratch / 'release').touch()

    first_out, first_err = first.communicate(timeout=10)
    assert started.exists(), 'the first measurement did not reach its pytest run'
    assert second is not None
    second_out, second_err = second.communicate(timeout=10)
    assert first.returncode == 0, first_out + first_err
    assert 'RUN\tsecond\tserial' not in lines_during_first, (
        'the second invocation entered pytest while the first measurement was active'
    )

    lines = trace.read_text(encoding='utf-8').splitlines()
    assert lines[0] == 'RUN\tfirst\tserial'
    assert lines[1] == 'UPDATE\tfirst'
    if second.returncode == 0:
        assert lines[2:] == ['RUN\tsecond\tserial', 'UPDATE\tsecond']
    else:
        assert second_out or second_err
        assert lines == ['RUN\tfirst\tserial', 'UPDATE\tfirst']


# --- interrupted-run safety (review-21 F1) -----------------------------------------------------
#
# An interrupted measurement still reaches sessionfinish, so the artifact is written and the
# manifest is regenerated. Before this gate, every node the run never REACHED was absent from the
# durations log and absent from the FAILED/ERROR rows, and was therefore written 0.000 — the
# fastest possible measured test. These assert the third state is holed, not zeroed.


def _resolve(
    collected: list[str],
    measured: dict[str, float],
    failing: set[str],
    completed: set[str] | None,
) -> tuple[dict[str, float], dict[str, str]]:
    checker = _runtime_checker()
    return checker.resolve_rows(collected, measured, failing, set(), set(), {}, completed)


def test_i5_unreached_nodes_are_holed_not_zeroed() -> None:
    """The F1 state: collected, no duration, no FAILED row, and never completed."""
    collected = ['t.py::reached_fast', 't.py::reached_slow', 't.py::never_reached']
    measured = {'t.py::reached_slow': 1.25}
    completed = {'t.py::reached_fast', 't.py::reached_slow'}

    runtimes, holes = _resolve(collected, measured, set(), completed)

    # the node the run never reached is a NAMED hole, never a measurement
    assert 't.py::never_reached' not in runtimes
    assert holes['t.py::never_reached'] == 'not-completed-in-this-run'
    # and the genuinely sub-floor node is still measured at the floor, not holed
    assert runtimes['t.py::reached_fast'] == 0.0
    assert runtimes['t.py::reached_slow'] == 1.25


def test_i5_no_completion_evidence_is_refused_at_every_entry_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⛔ THE INVARIANT: no code path gives an unmeasured node a number.

    This replaces a test that ASSERTED the vulnerable result — it pinned `resolve_rows(..., None)`
    returning 0.000 and called it a mutation, while it was a supported invocation, so the gate
    protected the defect instead of killing it (review-22 F1). Absence of evidence is now a
    REFUSAL at the callable, at `update()`, and at the CLI; each is asserted separately because
    three review rounds were each closed at one boundary and re-opened at another.
    """
    checker = _runtime_checker()

    # (1) the innermost callable
    with pytest.raises(checker.ManifestError, match='no completed-node set'):
        checker.resolve_rows(['t.py::a'], {}, set(), set(), set(), {}, None)

    # (2) update() — refuses BEFORE writing anything. : an UNCHANGED collection is a
    # no-op that reads no evidence at all (owner cadence ruling 2026-08-28), so the refusal is
    # asserted where something is actually measured — a collection with an unbanked node.
    log = tmp_path / 'durations.txt'
    log.write_text('1.0s call t.py::a\n', encoding='utf-8')
    monkeypatch.setattr(checker, 'MANIFEST', tmp_path / 'per-pr-runtimes.tsv')
    monkeypatch.setattr(checker, 'collect_nodeids', lambda: ['t.py::a'])
    assert checker.update(log, None) == 1
    assert not (tmp_path / 'per-pr-runtimes.tsv').exists(), (
        'a refused measurement without completion evidence must not create a manifest'
    )

    # (3) a legacy-shaped artifact carries no completion evidence
    legacy = tmp_path / 'legacy.json'
    legacy.write_text('{"tests/x.py": 1.5}', encoding='utf-8')
    assert checker.update(log, legacy) == 1

    # (4) a malformed artifact
    broken = tmp_path / 'broken.json'
    broken.write_text('{not json', encoding='utf-8')
    assert checker.update(log, broken) == 1


def test_i5_the_cli_refuses_update_without_the_artifact(tmp_path: Path) -> None:
    """End-to-end through the documented command, not only the library callable."""
    log = tmp_path / 'durations.txt'
    log.write_text('1.0s call t.py::a\n', encoding='utf-8')
    # : an unchanged collection reads no evidence, so force a measurement of a banked
    # node by name — the committed manifest's first python row — and the CLI must still refuse.
    banked = next(
        line.split('\t', 1)[1]
        for line in (ROOT / 'tests/per-pr-runtimes.tsv').read_text(encoding='utf-8').splitlines()
        if '\t' in line and not line.startswith('#') and '.py::' in line
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/checks/per_pr_runtimes.py'),
            '--update',
            str(log),
            '--remeasure',
            banked,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert completed.returncode == 1
    assert 'requires --fixture-costs' in completed.stderr


def test_i5_an_interrupted_artifact_holes_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PARTIAL artifact driven THROUGH `update()` writes named holes, never numeric runtimes.

    ⛔ The previous version of this test built a partial artifact, never used it, and called
    `resolve_rows()` directly while its docstring claimed end-to-end coverage (review-23 F1). That
    is the "different boundary left open" shape this finding keeps recurring by, so this one drives
    the documented entry point and INSPECTS THE MANIFEST IT WRITES.

    The artifact is VALID and merely incomplete: it has both required keys, so every refusal path
    is satisfied and the only thing under test is what `update()` records for a node the run never
    reached.
    """
    checker = _runtime_checker()
    manifest = tmp_path / 'per-pr-runtimes.tsv'
    manifest.write_text(
        '# inventory_python = 0\n# inventory_cpp = 0\n'
        '# inventory_measured = 0\n# inventory_unmeasured = 0\n',
        encoding='utf-8',
    )
    log = tmp_path / 'durations.txt'
    log.write_text('0.05s call tests/unit/py/test_reached.py::test_reached\n', encoding='utf-8')

    # `reached` completed and is in the log; `never` was collected and the run stopped before it.
    partial = tmp_path / 'partial.json'
    partial.write_text(
        '{"module_costs": {}, "completed": ["tests/unit/py/test_reached.py::test_reached"]}',
        encoding='utf-8',
    )
    monkeypatch.setattr(checker, 'MANIFEST', manifest)
    monkeypatch.setattr(
        checker,
        'collect_nodeids',
        lambda: [
            'tests/unit/py/test_reached.py::test_reached',
            'tests/unit/py/test_never.py::test_never',
        ],
    )

    assert checker.update(log, partial) == 0

    written = manifest.read_text(encoding='utf-8')
    rows = dict(
        reversed(line.split('\t', 1))
        for line in written.splitlines()
        if '\t' in line and not line.startswith('#')
    )
    assert rows['tests/unit/py/test_reached.py::test_reached'] == '0.050', (
        'the completed node must retain its independently measured focused runtime'
    )
    unreached = rows['tests/unit/py/test_never.py::test_never']
    assert unreached.startswith('UNMEASURED'), (
        f'the unreached node was written as {unreached!r}, not a declared hole'
    )
    assert 'not-completed-in-this-run' in unreached
    assert '0.000' not in unreached


def test_i5_a_partial_artifact_refuses_rather_than_zeroing() -> None:
    """An artifact with an EMPTY completed set holes everything; it never zeroes."""
    collected = ['t.py::a', 't.py::b']
    runtimes, holes = _resolve(collected, {}, set(), set())

    assert runtimes == {}
    assert holes == {
        't.py::a': 'not-completed-in-this-run',
        't.py::b': 'not-completed-in-this-run',
    }


def test_i5_a_pre_f1_artifact_shape_is_refused(tmp_path: Path) -> None:
    """The old flat artifact recorded no completion, so it is refused, not tolerated."""
    completed_nodes = _runtime_checker()._completed_nodes

    legacy = tmp_path / 'legacy.json'
    legacy.write_text('{"tests/x/test_y.py": 1.5}', encoding='utf-8')
    # no `completed` key -> an empty proven set, so every collected node holes
    assert completed_nodes(legacy) == set()

    current = tmp_path / 'current.json'
    current.write_text('{"module_costs": {}, "completed": ["t.py::a"]}', encoding='utf-8')
    assert completed_nodes(current) == {'t.py::a'}
