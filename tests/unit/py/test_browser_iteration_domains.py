"""Independent counter-domain and work-trace counterfactuals; no new fit pins."""

import copy
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.e04_t11_wasm import iteration_domains as counters
from tests.fixtures.e04_t11_wasm import written
from tests.fixtures.e04_t11_wasm.cli_domains import fields
from tests.fixtures.e04_t11_wasm.reopen import assert_documents
from tests.fixtures.native_process import environment_bash
from tests.unit.py.test_browser_written_reference import raw_control

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def authenticated_inputs():
    # Parsing and authenticating the immutable source trees is shared setup, not a counter operand.
    return {case: written.inputs(ROOT, case) for case in ('lbco', 'ncaf')}


def control():
    fixture = {
        'relative_tolerance': 1e-9,
        'absolute_tolerance': 1e-11,
        '_iteration_domain': {
            'conditions': {
                'descent': 'multistart_prune',
                'stop_rules': 'chi_square_change shift_su',
            },
            'probe_horizon': 3,
        },
    }
    callbacks = [
        {'iteration': 1, 'rwp': 0.25, 'reduced_chi_square': 2.5},
        {'iteration': 2, 'rwp': 0.125, 'reduced_chi_square': 1.25},
    ]
    record = {
        'status': 'done',
        'converged': 'true',
        'mode': 'single',
        'n_points_loaded': '23',
        'n_points_fitted': '23',
        'n_free': '2',
        'rwp': '0.125',
        'reduced_chi_square': '1.25',
        'param.cell.value': '3.25',
        'param.cell.uncertainty': '0.2',
        'iterations': '2',
        'descent': 'multistart_prune',
        'stopping_rule': 'chi_square_change',
        'multistart_prune': 'true',
        'multistart_probes_started': '2',
        'multistart_probes_pruned': '1',
        'multistart_probe_iterations': '6',
        'multistart_survivor': 'ladder',
    }
    for row in callbacks:
        ordinal = row['iteration']
        for key in ('rwp', 'reduced_chi_square'):
            record[f'iter.{ordinal}.{key}'] = str(row[key])
        record[f'iter.{ordinal}.unevaluable_trials'] = '0'
        record[f'iter.{ordinal}.elapsed_ms'] = str(ordinal * 10)
    raw = {
        'iterations': 2,
        'rwp': 0.125,
        'final_reduced_chi_square': 1.25,
        'iteration_domain': {
            'conditions': {**fixture['_iteration_domain']['conditions'], 'max_iterations': 1000},
            'callbacks': callbacks,
        },
    }
    return fixture, raw, '\n'.join(key + '=' + value for key, value in record.items())


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
@pytest.mark.parametrize('field', ['iterations', 'descent', 'project'])
def test_historical_counters_remain_authenticated_in_their_original_domain(
    case, field, authenticated_inputs
):
    fixture, old, *_ = authenticated_inputs[case]
    assert fixture['_iteration_domain']['conditions']['descent'] == 'multistart_prune', (
        'Historical ladder counts stay separate from current continuation work'
    )
    changed = dict(fixture)
    if field == 'iterations':
        changed['native_start_and_finish'] = dict(fixture['native_start_and_finish'])
        changed['native_start_and_finish']['iterations'] += 1
    elif field == 'descent':
        changed['scientific'] = dict(fixture['scientific'])
        changed['scientific']['analysis/analysis.edi'] = copy.deepcopy(
            fixture['scientific']['analysis/analysis.edi']
        )
        for row in changed['scientific']['analysis/analysis.edi']:
            if row[0] == '_fit_result.descent':
                row[1] = 'fast_descent'
    else:
        changed['project_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='Historical'):
        counters.historical(ROOT, case, changed, old)


@pytest.mark.parametrize(
    'mutation',
    [
        'count',
        'extra',
        'missing',
        'duplicate',
        'reordered',
        'operand',
        'nan',
        'bool',
    ],
)
def test_current_callback_trace_rejects_missing_fabricated_and_reordered_work(mutation):
    fixture, raw, report = control()
    counters.current(fixture, raw, report)
    rows = raw['iteration_domain']['callbacks']
    if mutation == 'count':
        raw['iterations'] = 8
    elif mutation == 'extra':
        rows.append(copy.deepcopy(rows[-1]))
    elif mutation == 'missing':
        rows.pop()
    elif mutation == 'duplicate':
        rows[1]['iteration'] = 1
    elif mutation == 'reordered':
        rows.reverse()
    elif mutation == 'operand':
        rows[0]['rwp'] += 0.01
    elif mutation == 'nan':
        rows[0]['rwp'] = float('nan')
    else:
        rows[0]['iteration'] = True
    with pytest.raises(ValueError, match='Current'):
        counters.current(fixture, raw, report)


@pytest.mark.parametrize(
    'mutation',
    [
        'count',
        'missing',
        'duplicate',
        'reorder',
        'malformed',
        'extra',
    ],
)
def test_full_report_history_rejects_missing_duplicate_malformed_or_reordered_rows(mutation):
    fixture, raw, report = control()
    record = fields(report)
    if mutation == 'count':
        record['iterations'] = '3'
    elif mutation == 'missing':
        record.pop('iter.1.rwp')
    elif mutation == 'duplicate':
        report += '\niter.1.rwp=0.25'
    elif mutation == 'reorder':
        record = dict(reversed(list(record.items())))
    elif mutation == 'malformed':
        record['iter.01.rwp'] = '0.25'
    else:
        record['iter.3.rwp'] = '0.1'
    if mutation != 'duplicate':
        report = '\n'.join(key + '=' + value for key, value in record.items())
    with pytest.raises(ValueError, match=r'Iteration|duplicated'):
        counters.current(fixture, raw, report)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('descent', 'ladder'),
        ('stopping_rule', 'none'),
        ('multistart_prune', 'false'),
        ('multistart_probes_started', '1'),
        ('multistart_probes_pruned', '0'),
        ('multistart_probe_iterations', '7'),
        ('multistart_survivor', 'none'),
    ],
)
def test_current_report_refuses_wrong_condition_or_probe_accounting(field, value):
    fixture, raw, report = control()
    record = fields(report)
    record[field] = value
    with pytest.raises(ValueError, match='Current'):
        counters.current(fixture, raw, '\n'.join(k + '=' + v for k, v in record.items()))


@pytest.mark.parametrize(('field', 'value'), [('stop_rules', 'shift_su'), ('max_iterations', 10)])
def test_current_pre_fit_conditions_cannot_be_retuned_to_match_a_pin(field, value):
    fixture, raw, report = control()
    raw['iteration_domain']['conditions'][field] = value
    with pytest.raises(ValueError, match='Current iteration conditions'):
        counters.current(fixture, raw, report)


@pytest.mark.parametrize(
    'field', ['iterations', 'descent', 'stopping_rule', *counters.WORK_FIELDS]
)
def test_two_actual_backend_reports_must_match_count_condition_and_separate_work(field):
    fixture, _, report = control()
    counters.compare_runtime(report, report, fixture)
    record = fields(report)
    record[field] = '3' if record[field].isdecimal() else 'wrong'
    with pytest.raises(ValueError, match=r'Iteration|Current'):
        counters.compare_runtime(
            '\n'.join(k + '=' + v for k, v in record.items()), report, fixture
        )


@pytest.mark.parametrize('field', ['iterations', 'descent'])
def test_save_cannot_substitute_a_historical_count_or_different_descent(tmp_path, field):
    _, raw, report = control()
    analysis = tmp_path / 'analysis/analysis.edi'
    analysis.parent.mkdir()
    good = '_fit_result.iterations 2\n_fit_result.descent multistart_prune\n'
    analysis.write_text(good)
    counters.saved(tmp_path, raw, report)
    changed = (
        good.replace('iterations 2', 'iterations 8')
        if field == 'iterations'
        else good.replace('multistart_prune', 'ladder')
    )
    analysis.write_text(changed)
    with pytest.raises(ValueError, match='Saved iteration'):
        counters.saved(tmp_path, raw, report)
    with pytest.raises(AssertionError, match='complete fit record'):
        assert_documents(
            {'analysis/analysis.edi': good.encode()},
            {'analysis/analysis.edi': changed.encode()},
            {},
        )


def test_native_written_path_is_exported_only_after_successful_shared_capture():
    script = (ROOT / 'tools/ci/wasm-check.sh').read_text()
    capture = 'bash "$ROOT/tools/ci/wasm-written-reference.sh" "$REFERENCE"'
    export = 'export EDI_WASM_WRITTEN_REFERENCE="$REFERENCE"'
    assert 'set -euo pipefail' in script and script.index(capture) < script.index(
        export
    ) < script.index('python -m pytest'), (
        'Catalogue work parity requires its explicitly owned successful native capture'
    )


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_historical_transcript_byte_tampering_cannot_reassign_its_domain(
    tmp_path, case, authenticated_inputs
):
    fixture, raw, *_ = authenticated_inputs[case]
    original = ROOT / 'tests/fixtures/e04_t11_wasm/catalogue_scientific'
    target = tmp_path / original.relative_to(ROOT)
    target.mkdir(parents=True)
    for path in original.glob(case + '-*'):
        (target / path.name).symlink_to(path)
    report = target / (case + '-native-report.txt')
    report.unlink()
    shutil.copyfile(original / report.name, report)
    report.write_text(report.read_text().replace('descent=ladder', 'descent=fast_descent'))
    with pytest.raises(ValueError, match='Historical iteration custody'):
        counters.historical(tmp_path, case, fixture, raw)


@pytest.mark.parametrize('token', ['0', '-1', '01', '1.0', '1e1', '\u0661', 'nan', '1001'])
def test_completed_count_spelling_and_budget_cannot_escape_full_history(token):
    _, _, report = control()
    record = fields(report)
    record['iterations'] = token
    with pytest.raises(ValueError, match='Iteration'):
        counters.history('\n'.join(key + '=' + value for key, value in record.items()), 1000)


@pytest.mark.parametrize(
    'field',
    [
        'rwp',
        'reduced_chi_square',
        'param.cell.value',
        'param.cell.uncertainty',
        'iter.1.rwp',
        'iter.1.reduced_chi_square',
        'iter.1.unevaluable_trials',
    ],
)
def test_same_count_never_hides_changed_physical_history_or_rejected_trial_work(field):
    fixture, _, report = control()
    record = fields(report)
    record[field] = '1' if field.endswith('trials') else str(float(record[field]) + 0.01)
    with pytest.raises(ValueError, match='Current'):
        counters.compare_runtime(
            '\n'.join(k + '=' + v for k, v in record.items()), report, fixture
        )


def test_raw_physical_checks_stay_active_in_the_explicit_current_counter_domain():
    fixture, old, raw, _, candidates, names, source = raw_control()
    domain_fixture, trace_raw, report = control()
    fixture['_iteration_domain'] = domain_fixture['_iteration_domain']
    # The old authored scalar is deliberately different, proving the domain split
    # without changing any physical operand or creating a numerical acceptance pin.
    raw['iterations'] = trace_raw['iterations']
    raw['iteration_domain'] = trace_raw['iteration_domain']
    record = fields(report)
    record['reduced_chi_square'] = str(raw['final_reduced_chi_square'])
    report = '\n'.join(k + '=' + v for k, v in record.items())
    written.qualify_raw(fixture, old, raw, report, candidates, names, source)
    for field in ('values', 'uncertainty'):
        changed = copy.deepcopy(raw)
        changed[field][next(iter(changed[field]))] += 0.01
        with pytest.raises(ValueError, match='raw value or SU'):
            written.qualify_raw(fixture, old, changed, report, candidates, names, source)


@pytest.mark.parametrize(
    'mutation',
    [
        'missing-digest',
        'replaced-digest',
        'wrong-digest',
        'missing-case',
        'schema',
        'current',
        'owner-extra',
    ],
)
def test_domain_declaration_refuses_missing_or_reassigned_custody_channels(mutation):
    value = copy.deepcopy(counters.declaration())
    owner = value['historical']['lbco']
    if mutation == 'missing-digest':
        owner['files'].pop('native-report.txt')
    elif mutation == 'replaced-digest':
        owner['files']['another.txt'] = owner['files'].pop('native-report.txt')
    elif mutation == 'wrong-digest':
        owner['files']['native-report.txt'] = 'not-sha256'
    elif mutation == 'missing-case':
        value['historical'].pop('ncaf')
    elif mutation == 'schema':
        value['schema'] = 'other'
    elif mutation == 'current':
        value['current']['conditions']['descent'] = 'ladder'
    else:
        owner['extra'] = 'unowned'
    with pytest.raises(ValueError, match=r'Iteration|Historical'):
        counters.declaration(value)


@pytest.mark.parametrize('missing', counters.EXACT_FIELDS)
def test_missing_required_fields_in_both_backends_never_count_as_agreement(missing):
    fixture, _, report = control()
    record = fields(report)
    record.pop(missing)
    report = '\n'.join(k + '=' + v for k, v in record.items())
    with pytest.raises(ValueError, match=r'Iteration|Current'):
        counters.compare_runtime(report, report, fixture)


@pytest.mark.parametrize(
    ('field', 'value'),
    [('n_points_fitted', '01'), ('n_free', '0'), ('n_points_loaded', '1'), ('mode', 'scan')],
)
def test_matching_malformed_point_counts_or_terminal_domains_are_refused(field, value):
    fixture, _, report = control()
    record = fields(report)
    record[field] = value
    report = '\n'.join(k + '=' + v for k, v in record.items())
    with pytest.raises(ValueError, match=r'Iteration|Current'):
        counters.compare_runtime(report, report, fixture)


@pytest.mark.parametrize('capture_exit', [0, 23])
def test_shared_capture_exports_only_the_successful_reference(tmp_path, capture_exit):
    script = (ROOT / 'tools/ci/wasm-check.sh').read_text()
    start = script.index('REFERENCE="$(mktemp -d')
    end = script.index('\nstatus=0', start)
    provider = tmp_path / 'tools/ci/wasm-written-reference.sh'
    provider.parent.mkdir(parents=True)
    provider.write_text('echo -n "$1" > "$OUT/captured-path"\nexit ' + str(capture_exit) + '\n')
    output = tmp_path / 'output'
    output.mkdir()
    env = {**os.environ, 'ROOT': str(tmp_path), 'OUT': str(output)}
    env.pop('EDI_WASM_WRITTEN_REFERENCE', None)
    run = subprocess.run(
        [
            environment_bash(),
            '-c',
            'set -euo pipefail\n' + script[start:end] + '\necho -n "$EDI_WASM_WRITTEN_REFERENCE"',
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert run.returncode == capture_exit, (
        'A failed shared capture must stop the actual shell before exporting a purported reference'
    )
    expected = (output / 'captured-path').read_text()
    assert Path(expected).is_dir() and expected.startswith(str(output)), (
        'The capture receives the freshly allocated owner directory before any consumer'
    )
    assert run.stdout == (expected if capture_exit == 0 else ''), (
        'Consumers inherit exactly the successful capture directory and no failed-capture handoff'
    )
