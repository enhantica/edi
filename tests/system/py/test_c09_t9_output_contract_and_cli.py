# ruff: noqa: PIE810, PLC0415, PLC1901, PLR0911, PLR0914, PLR0915, PT007
# Ported verbatim from the retired hidden fitting-test file ( phase C): the
# body keeps its hidden-tier-authored shape — reshaping it for the visible tier's
# lint would churn what the port must preserve.
"""Hidden  gates for edi's CLI, callbacks, and crysta conformance."""

from __future__ import annotations

import itertools
import os
import re
import subprocess
import sys
import threading
import weakref
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest

from conftest import calculator_load_warning, crysta_reference_prefix

ROOT = Path(__file__).resolve().parents[3]


def _corpus_project(case_id: str) -> Path:
    from conftest import corpus_case_dir

    return corpus_case_dir(case_id) / 'project'


def _single_project() -> Path:
    """The cheapest edi-loadable single-path corpus vehicle (P1.2b F-cheap)."""
    return _corpus_project('cosio-d20-s1')


def _joint_cheap_project() -> Path:
    """The cheapest joint corpus vehicle — the fixed two-bank case (P1.2b F-cheap)."""
    return _corpus_project('ncaf-wish-3bank-s5')


def _conformance_case() -> Path:
    """The ruled conformance vehicle (ruling 3): the 3-bank corpus case."""
    from conftest import corpus_case_dir

    return corpus_case_dir('ncaf-wish-3bank-s5')


CRYSTA_PREFIX = crysta_reference_prefix()
REL_EPSILON = 5e-9
ABS_EPSILON = 5e-10
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')
ELAPSED = re.compile(r'[+-]?\d+\.\d{3}')
# Schema 8 is the declared  rename-only bump: `reduced_chi_square` and
# `param.<label>.uncertainty` replace their schema-7 spellings without moving a value. The order
# is transcribed from the pinned crysta CLI's own compact record at the committed pin.
SHARED_COMPACT_KEYS = (
    'schema',
    'record',
    'status',
    'mode',
    'converged',
    'n_points_loaded',
    'n_points_fitted',
    'n_free',
    'iterations',
    'reduced_chi_square',
    'rwp',
    'descent',
    'fast_descent',
    'linear_snap',
    'guarded_linear_snap',
    'linear_snap_attempts',
    'linear_snap_rejections',
    'linear_snap_guard_residual_evaluations',
    'multistart_prune',
    'multistart_probes_started',
    'multistart_probes_pruned',
    'multistart_probe_iterations',
    'multistart_survivor',
    'unevaluable_trials',
    'terminal_unevaluable_trials',
    'nonfinite_trials',
    'terminal_nonfinite_trials',
    'bound_active_columns',
    'zero_jacobian_columns',
    'elapsed_ms',
)
EXACT_KEYS = {
    'schema',
    'record',
    'status',
    'mode',
    'converged',
    'n_points_loaded',
    'n_points_fitted',
    'n_points',
    'n_free',
    'iterations',
    'descent',
    'unevaluable_trials',
    'terminal_unevaluable_trials',
    'cutoff_policy',
    'fast_descent',
    'linear_snap',
    'guarded_linear_snap',
    'linear_snap_attempts',
    'linear_snap_rejections',
    'linear_snap_guard_residual_evaluations',
    'multistart_prune',
    'multistart_probes_started',
    'multistart_probes_pruned',
    'multistart_probe_iterations',
    'multistart_survivor',
    'nonfinite_trials',
    'terminal_nonfinite_trials',
    'bound_active_columns',
    'zero_jacobian_columns',
}
SEEDED_TOLERANCE_FIELDS = {'reduced_chi_square', 'rwp', 'value', 'uncertainty'}
PROVISIONAL_TOLERANCE_FIELDS = {'chi_square'}


def _environment() -> dict[str, str]:
    #  §P1.8 (one policy, zero pins): corpus-case fits run UNPINNED — the measured
    # policy for the fitting tier. The retired per-test `2` pin predated the bounded cheap
    # vehicles; conformance holds at the tolerance without it (the like-for-like comparison
    # is tolerance-classed, and the corpus proves thread-count-stable results there).
    return os.environ.copy()


def _run(
    command: list[str],
    *,
    check: bool = True,
    environment: Mapping[str, str] | None = None,
    timeout: int | None = 600,
) -> subprocess.CompletedProcess[str]:
    run_environment = _environment()
    if environment is not None:
        run_environment.update(environment)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=run_environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check:
        assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed


def _run_edi(
    *arguments: str,
    check: bool = True,
    timeout: int | None = 600,
) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, '-m', 'edi', *arguments], check=check, timeout=timeout)


def _crysta_cli() -> Path:
    """The INSTALLED comparison CLI ( workers gate): an immutable core-build artifact.

    Built once by the serial `core-build` step into the prefix — a test worker never builds
    in (or shares) the mutable crysta build tree.
    """
    suffix = '.exe' if os.name == 'nt' else ''
    executable = CRYSTA_PREFIX / 'bin' / f'crysta{suffix}'
    assert executable.is_file(), (
        'the installed comparison CLI is missing - run `pixi run core-build` first'
    )
    return executable


def _parse_record(text: str) -> tuple[list[str], dict[str, str]]:
    assert text.endswith('\n'), 'machine records are newline-terminated'
    keys: list[str] = []
    values: dict[str, str] = {}
    for line in text.splitlines():
        assert '\t' not in line, f'tabular output is outside schema 1: {line!r}'
        assert '=' in line, f'every machine-record line must be key=value: {line!r}'
        key, value = line.split('=', maxsplit=1)
        assert key and value, f'empty machine-record key/value: {line!r}'
        assert key not in values, f'duplicate machine-record key: {key}'
        keys.append(key)
        values[key] = value
    assert keys[:2] == ['schema', 'record']
    # ADR-0057's schema-8 key rename is live after 's staged post-merge pin bump.
    assert values['schema'] == '8', (
        "the _parse_record requirement must hold: values['schema'] == '8'"
    )
    return keys, values


def _assert_number(value: str) -> None:
    assert NUMBER.fullmatch(value), value
    assert ',' not in value
    float(value)


def _assert_fit_record(
    text: str,
    *,
    verbosity: str,
    crysta_surface: bool,
) -> tuple[list[str], dict[str, str]]:
    keys, values = _parse_record(text)
    base = list(SHARED_COMPACT_KEYS)
    if crysta_surface:
        base.insert(base.index('descent'), 'cutoff_policy')
    assert keys[: len(base)] == base
    assert values['record'] == 'fit'
    assert values['status'] in {'done', 'max_iter', 'no_step', 'cancelled'}
    assert values['mode'] in {'single', 'joint'}
    assert values['converged'] in {'true', 'false'}
    for key in (
        'n_points_loaded',
        'n_points_fitted',
        'n_free',
        'iterations',
        'linear_snap_attempts',
        'linear_snap_rejections',
        'linear_snap_guard_residual_evaluations',
        'multistart_probes_started',
        'multistart_probes_pruned',
        'multistart_probe_iterations',
        'unevaluable_trials',
        'terminal_unevaluable_trials',
        'nonfinite_trials',
        'terminal_nonfinite_trials',
    ):
        assert values[key].isdigit(), (key, values[key])
    for key in ('fast_descent', 'linear_snap', 'guarded_linear_snap', 'multistart_prune'):
        assert values[key] in {'true', 'false'}, (key, values[key])
    _assert_number(values['reduced_chi_square'])
    _assert_number(values['rwp'])
    assert ELAPSED.fullmatch(values['elapsed_ms'])
    if crysta_surface:
        assert values['cutoff_policy'] in {'off', 'on', 'ramp-fixed'}

    trailing = keys[len(base) :]
    if verbosity == 'compact':
        assert not trailing
        return keys, values

    assert verbosity == 'full'
    index = 0
    if values['mode'] == 'joint':
        while index < len(trailing) and trailing[index].startswith('bank.'):
            match = re.fullmatch(r'bank\.(.+)\.n_points', trailing[index])
            assert match is not None, trailing[index]
            bank = match.group(1)
            expected = [
                f'bank.{bank}.n_points',
                f'bank.{bank}.rwp',
                f'bank.{bank}.chi_square',
            ]
            assert trailing[index : index + 3] == expected
            assert values[expected[0]].isdigit()
            _assert_number(values[expected[1]])
            _assert_number(values[expected[2]])
            index += 3

    for iteration in range(1, int(values['iterations']) + 1):
        expected = [
            f'iter.{iteration}.rwp',
            f'iter.{iteration}.reduced_chi_square',
            f'iter.{iteration}.unevaluable_trials',
            f'iter.{iteration}.elapsed_ms',
        ]
        assert trailing[index : index + 4] == expected
        _assert_number(values[expected[0]])
        _assert_number(values[expected[1]])
        assert values[expected[2]].isdigit()
        assert ELAPSED.fullmatch(values[expected[3]])
        index += 4

    labels: list[str] = []
    while index < len(trailing) and trailing[index].startswith('param.'):
        match = re.fullmatch(r'param\.(.+)\.value', trailing[index])
        assert match is not None, trailing[index]
        label = match.group(1)
        expected = [f'param.{label}.value', f'param.{label}.uncertainty']
        assert trailing[index : index + 2] == expected
        _assert_number(values[expected[0]])
        _assert_number(values[expected[1]])
        labels.append(label)
        index += 2
    assert labels == sorted(labels)

    extensions = trailing[index:]
    assert extensions == sorted(extensions)
    assert all(re.fullmatch(r'x-[a-z0-9]+(?:\.[a-z0-9_]+)+', key) for key in extensions)
    return keys, values


def _field_class(key: str) -> str | None:
    if key in EXACT_KEYS or re.fullmatch(r'bank\..+\.n_points', key):
        return 'exact'
    if key.startswith('x-') or key == 'elapsed_ms' or re.fullmatch(r'iter\..+\.elapsed_ms', key):
        return 'informational'
    if key == 'checksum':
        return 'informational'
    match = re.fullmatch(r'(?:bank|iter|param)\..+\.([^.]+)', key)
    field = match.group(1) if match else key
    if field == 'unevaluable_trials':
        return 'exact'
    if key.startswith(('bank.', 'iter.')) and field in {
        'rwp',
        'reduced_chi_square',
        'chi_square',
    }:
        return 'tolerance-provisional'
    if field in SEEDED_TOLERANCE_FIELDS:
        return 'tolerance-seeded'
    if field in PROVISIONAL_TOLERANCE_FIELDS:
        return 'tolerance-provisional'
    return None


def _within_tolerance(actual: str, expected: str) -> bool:
    actual_value = float(actual)
    expected_value = float(expected)
    return abs(actual_value - expected_value) <= max(
        REL_EPSILON * abs(expected_value),
        ABS_EPSILON,
    )


def _conformance_differences(left: str, right: str) -> list[str]:
    """Compare records by the accepted table; bank/iter families stay labelled provisional."""
    _, left_values = _parse_record(left)
    _, right_values = _parse_record(right)
    differences: list[str] = []
    for key in sorted(set(left_values) | set(right_values)):
        classification = _field_class(key)
        if key not in left_values or key not in right_values:
            if key == 'cutoff_policy' or classification == 'informational':
                continue
            differences.append(f'{key}: missing from one surface')
            continue
        if classification == 'informational':
            continue
        if classification == 'exact':
            if left_values[key] != right_values[key]:
                differences.append(f'{key}: exact mismatch')
            continue
        if classification in {'tolerance-seeded', 'tolerance-provisional'}:
            if not _within_tolerance(right_values[key], left_values[key]):
                differences.append(f'{key}: tolerance mismatch ({classification})')
            continue
        differences.append(f'{key}: unclassified field')
    return differences


def _replace_line(record: str, key: str, value: str) -> str:
    lines = record.splitlines()
    replaced = [f'{key}={value}' if line.startswith(f'{key}=') else line for line in lines]
    assert replaced != lines, key
    return '\n'.join(replaced) + '\n'


def _loop_rows(path: Path, first_tag: str) -> list[list[str]]:
    lines = path.read_text(encoding='utf-8').splitlines()
    index = lines.index(first_tag)
    while index < len(lines) and lines[index].startswith('_'):
        index += 1
    rows: list[list[str]] = []
    while index < len(lines):
        line = lines[index].strip()
        if not line or line == 'loop_' or line.startswith('_') or line.startswith('data_'):
            break
        rows.append(line.split())
        index += 1
    return rows


def _grid_and_ranges(path: Path) -> tuple[list[float], list[tuple[float, float]]]:
    text = path.read_text(encoding='utf-8')
    axis = '_data.time_of_flight' if '_data.time_of_flight' in text else '_data.two_theta'
    grid = [float(row[0]) for row in _loop_rows(path, axis)]
    if '_excluded_region.id' in text:
        ranges = [
            (float(row[1]), float(row[2])) for row in _loop_rows(path, '_excluded_region.id')
        ]
    else:
        ranges = []
    return grid, ranges


def _outside_ranges(values: Iterable[float], ranges: list[tuple[float, float]]) -> int:
    return sum(not any(start <= value <= end for start, end in ranges) for value in values)


def _stage_bounded_conformance(destination: Path) -> tuple[Path, int]:
    """Stage the 3-bank case's committed bounded-analysis variant, in place (no data copied).

    Experiments/structures are symlinks into the corpus case; the analysis is the case's own
    committed `bounded-analysis/analysis.edi`, whose declared `_minimizer.max_iterations` is
    the ONE source of the bound for both CLIs.
    """
    case = _conformance_case()
    staged = destination / 'bounded-project'
    staged.mkdir()
    for child in ('experiments', 'structures'):
        (staged / child).symlink_to(case / 'project' / child, target_is_directory=True)
    project_edi = case / 'project' / 'project.edi'
    if project_edi.is_file():
        (staged / 'project.edi').symlink_to(project_edi)
    (staged / 'analysis').mkdir()
    bounded = (case / 'bounded-analysis' / 'analysis.edi').read_text(encoding='utf-8')
    (staged / 'analysis' / 'analysis.edi').write_text(bounded, encoding='utf-8')
    declared = re.search(r'^_minimizer\.max_iterations (\d+)$', bounded, re.MULTILINE)
    assert declared is not None, 'the bounded-analysis variant must declare its bound'
    return staged, int(declared.group(1))


@pytest.fixture(scope='module')
def conformance_outputs(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    """The 4 bounded conformance runs (P1.2b row 1): 2 surfaces x 2 verbosities.

    Bounded on the ruled 3-bank vehicle — pre-convergence properties only; the converged
    oracle lives in the corpus case's FullProf-referenced `expected.json` (I16), asserted by
    the corpus runner on every pass, never re-fit here.
    """
    staged, declared_bound = _stage_bounded_conformance(tmp_path_factory.mktemp('c09_t9'))
    crysta_cli = _crysta_cli()
    outputs: dict[str, Any] = {'bound': declared_bound, 'project': staged}
    for verbosity in ('compact', 'full'):
        outputs['crysta', verbosity] = _run([
            str(crysta_cli),
            'fit',
            str(staged),
            '--dry',
            '--verbosity',
            verbosity,
        ])
        outputs['edi', verbosity] = _run_edi(
            'fit',
            str(staged),
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            verbosity,
        )
    return outputs


def test_c09_t9_conformance_differ_discriminates_field_classes() -> None:
    base = """\
schema=8
record=fit
status=done
mode=joint
converged=true
n_points_loaded=20475
n_points_fitted=18973
n_free=193
iterations=14
reduced_chi_square=9.497560854
rwp=0.07694468879
unevaluable_trials=0
terminal_unevaluable_trials=0
elapsed_ms=29.375
"""
    assert _conformance_differences(base, base) == []

    exact_bit_change = _replace_line(base, 'iterations', '15')
    assert _conformance_differences(base, exact_bit_change) == ['iterations: exact mismatch']

    boundary_contact_change = _replace_line(base, 'unevaluable_trials', '1')
    assert _conformance_differences(base, boundary_contact_change) == [
        'unevaluable_trials: exact mismatch'
    ]

    below_absolute_floor = _replace_line(base, 'rwp', '0.07694468889')
    assert _conformance_differences(base, below_absolute_floor) == []

    large_timing_change = _replace_line(base, 'elapsed_ms', '999999.000')
    assert _conformance_differences(base, large_timing_change) == []

    above_epsilon = _replace_line(base, 'reduced_chi_square', '9.497570854')
    assert _conformance_differences(base, above_epsilon) == [
        'reduced_chi_square: tolerance mismatch (tolerance-seeded)'
    ], 'the conformance differ must report only the seeded tolerance mismatch'

    provisional = base + 'bank.wish_1_10.n_points=3758\nbank.wish_1_10.rwp=0.154\n'
    provisional_change = _replace_line(provisional, 'bank.wish_1_10.rwp', '0.155')
    assert _conformance_differences(provisional, provisional_change) == [
        'bank.wish_1_10.rwp: tolerance mismatch (tolerance-provisional)'
    ]

    calc = 'schema=8\nrecord=calc\nn_points=18973\nchecksum=7.25\nelapsed_ms=1.000\n'
    calc_exact_bit_change = _replace_line(calc, 'n_points', '18972')
    assert _conformance_differences(calc, calc_exact_bit_change) == ['n_points: exact mismatch']
    checksum_change = _replace_line(calc, 'checksum', '999999.5')
    assert _conformance_differences(calc, checksum_change) == []


@pytest.mark.parametrize('verbosity', ['compact', 'full'])
def test_c09_t9_crysta_and_edi_machine_records_conform_like_for_like(
    conformance_outputs: dict[str, Any],
    verbosity: str,
) -> None:
    """Bounded like-for-like conformance (P1.2b row 1): what is observable WITHOUT convergence.

    Bank structure/order, the full parameter-label set, cross-surface equality of the bounded
    records, and the per-iteration record law at the DECLARED count. Absolute key-count pins
    are iteration-dependent and prove nothing re-frozen at a bound; the converged oracle lives
    in the corpus case (I16), not here.
    """
    project = conformance_outputs['project']
    declared_bound = conformance_outputs['bound']
    crysta_result = conformance_outputs['crysta', verbosity]
    edi_result = conformance_outputs['edi', verbosity]
    assert crysta_result.stderr == ''
    assert edi_result.stderr == ''
    crysta_keys, crysta_record = _assert_fit_record(
        crysta_result.stdout,
        verbosity=verbosity,
        crysta_surface=True,
    )
    edi_keys, edi_record = _assert_fit_record(
        edi_result.stdout,
        verbosity=verbosity,
        crysta_surface=False,
    )
    assert _conformance_differences(crysta_result.stdout, edi_result.stdout) == []
    assert 'cutoff_policy' in crysta_record
    assert 'cutoff_policy' not in edi_record

    # The record law at the declared bound — the ONE declared source both surfaces obey.
    for record in (crysta_record, edi_record):
        assert int(record['iterations']) == declared_bound
        assert record['status'] == 'max_iter'
        assert record['converged'] == 'false'

    # Point counts: cross-surface equal and re-derivable from the staged project's own files —
    # loaded minus fitted equals the points inside the declared excluded regions.
    loaded = fitted = 0
    for experiment in sorted((project / 'experiments').glob('*.edi')):
        grid, ranges = _grid_and_ranges(experiment)
        loaded += len(grid)
        fitted += _outside_ranges(grid, ranges)
    assert loaded > fitted, 'the conformance vehicle must have in-range excluded points'
    for record in (crysta_record, edi_record):
        assert int(record['n_points_loaded']) == loaded
        assert int(record['n_points_fitted']) == fitted

    # Key-set relation, never absolute pins: crysta carries exactly the extra cutoff_policy key.
    assert len(crysta_keys) == len(edi_keys) + 1
    assert set(crysta_keys) - set(edi_keys) == {'cutoff_policy'}

    if verbosity == 'full':
        # The full parameter-label set is identical across surfaces.
        crysta_labels = {key for key in crysta_keys if key.startswith('param.')}
        edi_labels = {key for key in edi_keys if key.startswith('param.')}
        assert crysta_labels == edi_labels
        assert crysta_labels, 'the full record must carry the parameter set'
        # Bank structure/order: emitted banks equal the public filename load order, which the
        # fixture keeps distinct from the analysis weight-row order.
        analysis_weight_banks = [
            row[0]
            for row in _loop_rows(project / 'analysis/analysis.edi', '_joint_fit.experiment_id')
        ]
        loaded_banks = [
            experiment.stem for experiment in sorted((project / 'experiments').glob('*.edi'))
        ]
        assert set(analysis_weight_banks) == set(loaded_banks)
        assert analysis_weight_banks != loaded_banks, (
            'the fixture must distinguish analysis weight-row order from the public filename '
            'load order'
        )
        for keys in (crysta_keys, edi_keys):
            emitted_banks = [
                key.removeprefix('bank.').removesuffix('.n_points')
                for key in keys
                if key.startswith('bank.') and key.endswith('.n_points')
            ]
            assert emitted_banks == loaded_banks


# : split — the five verbosity-surface spawns carried one node past the system bound;
# each slice keeps its spawns and assertions unchanged, and their union is the original claim.
def test_c09_t9_cli_defaults_to_compact_human() -> None:
    single_project = _single_project()
    expected_warning = calculator_load_warning(single_project)
    default = _run_edi('fit', str(single_project), '--dry', timeout=None)
    assert default.stderr == expected_warning, (
        ' default CLI stderr admits exactly the declared calculator warning'
    )
    assert default.stdout.strip()
    assert 'schema=' not in default.stdout
    assert 'parameter' not in default.stdout.casefold()

    explicit = _run_edi(
        'fit',
        str(single_project),
        '--dry',
        '--report',
        'human',
        '--verbosity',
        'compact',
        timeout=None,
    )
    assert explicit.stderr == expected_warning, (
        ' explicit compact CLI stderr admits exactly the declared calculator warning'
    )
    assert explicit.stdout.strip()
    assert 'schema=' not in explicit.stdout
    assert 'parameter' not in explicit.stdout.casefold()


def test_c09_t9_cli_full_verbosity_reports_parameters() -> None:
    expected_warning = calculator_load_warning(_single_project())
    full = _run_edi(
        'fit',
        str(_single_project()),
        '--dry',
        '--report',
        'human',
        '--verbosity',
        'full',
        timeout=None,
    )
    assert full.stderr == expected_warning, (
        ' full CLI stderr admits exactly the declared calculator warning'
    )
    assert 'parameter' in full.stdout.casefold()


def test_c09_t9_cli_verbosity_off_is_silent_for_both_reports() -> None:
    expected_warning = calculator_load_warning(_single_project())
    for report in ('human', 'machine'):
        off = _run_edi(
            'fit',
            str(_single_project()),
            '--dry',
            '--report',
            report,
            '--verbosity',
            'off',
            timeout=None,
        )
        assert off.stdout == ''
        assert off.stderr == expected_warning, (
            ' load diagnostics remain exact even when fit verbosity is off'
        )


def test_c09_t9_library_fit_is_silent_without_callback() -> None:
    expected_warning = calculator_load_warning(_single_project())
    script = f'import edi\nproject = edi.Project.load({str(_single_project())!r})\nproject.fit()\n'
    completed = _run([sys.executable, '-c', script], timeout=None)
    assert completed.stdout == '', ': a silent library fit must write nothing to stdout'
    assert completed.stderr == expected_warning, (
        '/: library fit emits no stderr beyond the exact load warning'
    )


def _invoke_fit_overload(name: str, callback: Any | None) -> Any:
    import edi

    project_root = _joint_cheap_project() if name.startswith('joint') else _single_project()
    project = edi.Project.load(project_root)
    callback_arguments = {} if callback is None else {'on_iteration': callback}
    if name == 'single-embedded':
        return project.fit(**callback_arguments)
    if name == 'joint-embedded':
        return project.fit_joint(**callback_arguments)
    if name in {'single-analysis', 'joint-analysis'}:
        return project.analysis.fit(**callback_arguments)
    raise AssertionError(f'unknown Python fit overload {name!r}')


class _IterationSubscriber:
    def __init__(self) -> None:
        self.records: list[Any] = []

    def __call__(self, record: Any) -> None:
        self.records.append(record)


@pytest.mark.parametrize(
    'overload',
    ('single-embedded', 'joint-embedded', 'single-analysis', 'joint-analysis'),
)
def test_c09_t9_python_fit_overloads_restore_callback_ownership(overload: str) -> None:
    without_callback = _invoke_fit_overload(overload, None)

    subscriber = _IterationSubscriber()
    baseline_refcount = sys.getrefcount(subscriber)
    with_callback = _invoke_fit_overload(overload, subscriber)

    assert sys.getrefcount(subscriber) == baseline_refcount, (
        f'{overload} retained or prematurely released Python callback ownership'
    )
    callback_records = subscriber.records
    assert len(callback_records) == with_callback.iterations
    assert [record.iteration for record in callback_records] == list(
        range(1, with_callback.iterations + 1)
    )
    assert _engine_result(without_callback) == _engine_result(with_callback)

    subscriber_reference = weakref.ref(subscriber)
    del subscriber
    assert subscriber_reference() is None, f'{overload} leaked the Python callback'


def _engine_result(outcome: Any) -> tuple[Mapping[str, float], Mapping[str, float], float, float]:
    return (
        outcome.values,
        outcome.uncertainty,
        float(outcome.rwp),
        float(outcome.reduced_chi_square),
    )


# --- properties restored under review-22 F2 ----------------------------------------------------
#
# These rode tests that ruling 65 retired with the 18-case vocabulary. Neither is
# corpus-bound: one rides the SURVIVING callback vehicle above, and the other exercises the CLI
# router's caught pre-fit path with the fit stubbed to raise, so it never reaches a public fit and
# needs no I20 exception. Naming a lost property is not a replacement for asserting it
# (packet binding boundary); these assert it.


def test_c09_t9_another_python_thread_runs_between_callbacks() -> None:
    """The engine RELEASES THE GIL across iterations — a second Python thread makes progress.

    Retired with the same test. Without this, a change that held the GIL for the whole fit would
    keep every other assertion green while making the callback stream unusable for progress
    reporting, which is what it exists for.
    """
    stop = threading.Event()
    ticks = itertools.count()
    counter = {'value': 0}

    def spin() -> None:
        while not stop.is_set():
            counter['value'] = next(ticks)

    observed_at_callback: list[int] = []

    def subscriber(_record: Any) -> None:
        observed_at_callback.append(counter['value'])

    worker = threading.Thread(target=spin, daemon=True)
    worker.start()
    try:
        outcome = _invoke_fit_overload('single-embedded', subscriber)
    finally:
        stop.set()
        worker.join(timeout=5)

    assert outcome.iterations >= 2, 'this vehicle must run enough iterations to observe progress'
    assert len(observed_at_callback) == outcome.iterations
    assert observed_at_callback[-1] > observed_at_callback[0], (
        'no other Python thread ran between the first and last callback: the engine held the GIL'
    )


def test_c09_t9_cli_router_splits_the_machine_record_from_the_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The REAL CLI router puts the machine record on stdout and the prose on stderr.

    Retired with `test_c09_t9_machine_error_record_stays_on_stdout`, which built an invalid project
    and fitted it — an invocation I20 refuses. The property is about the ROUTER, not the fit, so
    the fit operation is stubbed to raise and `edi.__main__.main()` is driven directly. No public
    fit is reached, so I20 is neither involved nor loosened.
    """
    from edi import __main__ as cli

    def _explode(_args: Any) -> int:
        raise ValueError('deliberate pre-fit failure')

    monkeypatch.setattr(cli, 'run_fit', _explode)

    exit_code = cli.main(['fit', 'does-not-matter', '--verbosity', 'full'])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out, 'the machine record must be written to stdout'
    record = dict(line.split('=', 1) for line in captured.out.strip().splitlines() if '=' in line)
    assert record.get('record') == 'error'
    assert record.get('status') == 'error'
    assert 'deliberate pre-fit failure' in captured.err
    assert 'deliberate pre-fit failure' not in captured.out, (
        'the prose diagnostic leaked into the machine record on stdout'
    )
