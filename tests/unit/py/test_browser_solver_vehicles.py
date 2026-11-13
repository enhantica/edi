"""Frozen-data protocol controls; real twin fits remain mandatory qualification."""

import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.e04_t11_wasm import iteration_domains, solver_vehicles, written
from tests.fixtures.e04_t11_wasm.cli_domains import fields
from tests.system.py import test_e04_t11_wasm_fit as wasm_fit

ROOT = Path(__file__).resolve().parents[3]


def report_text(record):
    return '\n'.join(key + '=' + value for key, value in record.items())


@pytest.fixture(scope='module')
def historical():
    fixture, old, source, names, banks = written.inputs(ROOT, 'ncaf')
    candidates = written.raw_candidates(fixture, old, names, banks, source)
    selected = {column: next(iter(paths)) for column, paths in candidates.items()}
    record = fields(
        (
            ROOT / 'tests/fixtures/e04_t11_wasm/catalogue_scientific/ncaf-native-report.txt'
        ).read_text()
    )
    record['stopping_rule'] = 'chi_square_change'
    callbacks = [
        {
            'iteration': ordinal,
            'rwp': float(record[f'iter.{ordinal}.rwp']),
            'reduced_chi_square': float(record[f'iter.{ordinal}.reduced_chi_square']),
        }
        for ordinal in range(1, old['iterations'] + 1)
    ]
    raw = {
        **fixture['native_start_and_finish'],
        'values': {path: old['values'][column] for column, path in selected.items()},
        'uncertainty': {
            path: math.sqrt(old['covariance'][column * len(selected) + column])
            for column, path in selected.items()
        },
        'status': 'FitStatus.DONE',
        'converged': True,
        'iteration_domain': {
            'conditions': {**solver_vehicles.HISTORICAL, 'max_iterations': 1000},
            'callbacks': callbacks,
        },
    }
    loaded = {
        'fitting_mode': 'joint',
        'su_rule': 'iucr_99',
        'free_count': len(selected),
        'max_iterations': 1000,
        'chi_square_tolerance': 1e-4,
        **solver_vehicles.HISTORICAL,
    }
    return SimpleNamespace(
        fixture=fixture,
        old=old,
        source=source,
        names=names,
        banks=banks,
        candidates=candidates,
        selected=selected,
        raw=raw,
        record=record,
        loaded=loaded,
    )


@pytest.fixture(scope='module')
def current(historical):
    control = historical
    expected = json.loads((control.source.parent / 'expected.json').read_text())
    raw = copy.deepcopy(control.raw)
    record = dict(control.record)
    count = int(expected['quantities']['iterations']['value'])
    final = expected['quantities']['reduced_chi_square']['value']
    raw['iterations'] = count
    raw['final_reduced_chi_square'] = final
    raw['iteration_domain']['conditions'] = {
        **control.fixture['_iteration_domain']['conditions'],
        'max_iterations': 1000,
    }
    raw['iteration_domain']['callbacks'] = raw['iteration_domain']['callbacks'][:count]
    record = {key: value for key, value in record.items() if not key.startswith('iter.')}
    record.update({
        'iterations': str(count),
        'reduced_chi_square': str(final),
        'descent': 'multistart_prune',
        'multistart_prune': 'true',
        'multistart_probes_started': '2',
        'multistart_probes_pruned': '1',
        'multistart_probe_iterations': '6',
        'multistart_survivor': 'ladder',
    })
    for row in raw['iteration_domain']['callbacks']:
        for field in ('rwp', 'reduced_chi_square'):
            record[f'iter.{row["iteration"]}.{field}'] = str(row[field])
        record[f'iter.{row["iteration"]}.unevaluable_trials'] = '0'
        record[f'iter.{row["iteration"]}.elapsed_ms'] = str(row['iteration'])
    for column, path in control.selected.items():
        for suffix, key in (('value', 'values'), ('uncertainty', 'uncertainty')):
            record[f'param.{control.old["labels"][column]}.{suffix}'] = str(raw[key][path])
    loaded = {**control.loaded, **control.fixture['_iteration_domain']['conditions']}
    return SimpleNamespace(raw=raw, record=record, loaded=loaded, expected=expected)


def qualify(control, *, current=None, raw=None, report=None, loaded=None):
    state = current or control
    function = written.qualify_current if current else written.qualify_historical
    return function(
        control.fixture,
        control.old,
        raw or state.raw,
        report or report_text(state.record),
        control.candidates,
        control.names,
        control.source,
        loaded=loaded or state.loaded,
    )


def test_historical_vehicle_keeps_all_original_raw_operands_and_does_not_mutate_domain(historical):
    marker = copy.deepcopy(historical.fixture['_iteration_domain'])
    assert len(qualify(historical)) == 193, (
        'The historical vehicle checks every original fitted value and SU at its original bounds'
    )
    assert historical.fixture['_iteration_domain'] == marker, (
        'Checking historical conditions cannot remove or alter the current-default domain'
    )
    solver_vehicles.qualify_historical_report(
        historical.fixture, historical.old, report_text(historical.record)
    )


@pytest.mark.parametrize('column', range(193))
@pytest.mark.parametrize('operand', ['value', 'uncertainty'])
def test_historical_wasm_report_rejects_each_changed_original_value_or_su(
    historical, column, operand
):
    record = dict(historical.record)
    key = f'param.{historical.old["labels"][column]}.{operand}'
    record[key] = str(float(record[key]) + max(abs(float(record[key])) * 1e-5, 1e-4))
    with pytest.raises(ValueError, match=r'.+'):
        solver_vehicles.qualify_historical_report(
            historical.fixture, historical.old, report_text(record)
        )


@pytest.mark.parametrize(
    ('key', 'value'),
    [
        ('iterations', '16'),
        ('reduced_chi_square', '10'),
        ('rwp', '0.1'),
        ('n_free', '192'),
        ('n_points_fitted', '1'),
        ('status', 'failed'),
        ('converged', 'false'),
        ('descent', 'multistart_prune'),
        ('stopping_rule', 'shift_su'),
        ('multistart_probe_iterations', '1'),
        ('multistart_survivor', 'ladder'),
    ],
)
def test_historical_wasm_cannot_borrow_current_conditions_or_shorten_population(
    historical, key, value
):
    record = {**historical.record, key: value}
    with pytest.raises(ValueError, match=r'.+'):
        solver_vehicles.qualify_historical_report(
            historical.fixture, historical.old, report_text(record)
        )


@pytest.mark.parametrize('phase', ['historical', 'current'])
@pytest.mark.parametrize(
    ('key', 'value'),
    [
        ('max_iterations', 1000.0),
        ('max_iterations', 10),
        ('free_count', 193.0),
        ('free_count', True),
        ('chi_square_tolerance', 0.01),
        ('chi_square_tolerance', True),
        ('su_rule', 'none'),
        ('fitting_mode', 'single'),
        ('unexpected', 1),
    ],
)
def test_loaded_snapshot_cannot_hide_retuning_type_aliases_or_missing_original_settings(
    historical, current, phase, key, value
):
    state = current if phase == 'current' else historical
    qualify(historical, current=current if phase == 'current' else None)
    loaded = {**state.loaded, key: value}
    with pytest.raises(ValueError, match=r'.+'):
        qualify(historical, current=current if phase == 'current' else None, loaded=loaded)


def test_current_raw_population_matches_every_full_report_field(historical, current):
    assert len(qualify(historical, current=current)) == 193, (
        'Current-default checks retain all semantic raw value and SU identities'
    )
    for field in ('values', 'uncertainty'):
        for path in current.raw[field]:
            raw = {**current.raw, field: {**current.raw[field]}}
            raw[field][path] += max(abs(raw[field][path]) * 1e-5, 1e-4)
            with pytest.raises(ValueError, match=r'.+'):
                solver_vehicles.current(
                    historical.fixture,
                    historical.old,
                    raw,
                    report_text(current.record),
                    historical.selected,
                    current.expected,
                )


@pytest.mark.parametrize('field', ['values', 'uncertainty'])
def test_current_wrapper_reaches_full_report_value_and_su_checks(historical, current, field):
    raw = copy.deepcopy(current.raw)
    raw[field][next(iter(raw[field]))] += 1
    with pytest.raises(ValueError, match=r'.+'):
        qualify(historical, current=current, raw=raw)


@pytest.mark.parametrize('escape', ['delete', 'replace', 'value', 'bound', 'kind', 'schema'])
def test_current_reference_operand_is_the_complete_authenticated_existing_contract(
    historical, current, escape
):
    expected = copy.deepcopy(current.expected)
    key = next(key for key in expected['quantities'] if key.startswith('param.'))
    if escape == 'delete':
        expected['quantities'].pop(key)
    elif escape == 'replace':
        expected['quantities']['unowned'] = expected['quantities'].pop(key)
    elif escape == 'value':
        expected['quantities'][key]['value'] += 0.000001
    elif escape == 'bound':
        expected['quantities'][key]['tol_abs'] *= 1000
    elif escape == 'kind':
        expected['quantities'][key]['kind'] = 'regression-pin'
    else:
        expected['schema'] = True
    with pytest.raises(ValueError, match=r'.+'):
        solver_vehicles.current(
            historical.fixture,
            historical.old,
            current.raw,
            report_text(current.record),
            historical.selected,
            expected,
        )


@pytest.mark.parametrize('name', ['expected.json', 'PROVENANCE.md'])
def test_current_file_custody_refuses_source_bytes_changed_before_a_fresh_capture(
    historical, monkeypatch, name
):
    solver_vehicles.current_references(historical.fixture, historical.source)
    target = historical.source.parent / name
    real_read = Path.read_bytes

    def changed(path):
        original = real_read(path)
        return original + b'\nchanged\n' if path == target else original

    monkeypatch.setattr(Path, 'read_bytes', changed)
    with pytest.raises(ValueError, match=r'.+'):
        solver_vehicles.current_references(historical.fixture, historical.source)


@pytest.mark.parametrize(
    'declaration',
    [
        b'_minimizer.descent ladder',
        b'  _minimizer.descent ladder',
        b'\t_minimizer.stop_rules shift_su',
        b'_minimizer.stop_rule shift_su',
        b'_MINIMIZER.DESCENT ladder',
        b'loop_\n_minimizer.descent\nladder',
        b'loop_\n_MINIMIZER.STOP_RULE\nshift_su',
    ],
)
def test_historical_vehicle_never_overrides_any_explicit_solver_declaration(tmp_path, declaration):
    source = tmp_path / 'source'
    (source / 'analysis').mkdir(parents=True)
    (source / 'analysis/analysis.edi').write_bytes(
        b'_minimizer.max_iterations 1000\n' + declaration
    )
    with pytest.raises(ValueError, match=r'.+'):
        solver_vehicles.vehicle(source, tmp_path / 'destination')


def test_historical_vehicle_preserves_every_other_input_byte_and_source(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'destination'
    (source / 'analysis').mkdir(parents=True)
    (source / 'analysis/analysis.edi').write_bytes(
        b'_minimizer.max_iterations 1000\r\n_minimizer.chi_square_tolerance 1e-4\r\n'
    )
    (source / 'untouched.dat').write_bytes(b'\x00payload\r\n')
    original = written.files(source)
    solver_vehicles.vehicle(source, target)
    assert written.files(source) == original, (
        'The historical vehicle cannot mutate its input owner'
    )
    assert (target / 'untouched.dat').read_bytes() == (source / 'untouched.dat').read_bytes(), (
        'Historical selection preserves all measured and opaque source bytes'
    )
    before = (source / 'analysis/analysis.edi').read_bytes()
    after = (target / 'analysis/analysis.edi').read_bytes()
    assert after.startswith(before), 'Historical selection retains every original analysis byte'
    tags = [line.split() for line in after[len(before) :].splitlines() if line.strip()]
    assert tags == [
        [b'_minimizer.descent', b'ladder'],
        [b'_minimizer.stop_rules', b'chi_square_change'],
    ], 'Exactly the two source-backed historical selectors may be appended'


class StopBeforeCurrentFitError(Exception):
    pass


class ReachedArrayValidationError(Exception):
    pass


@pytest.mark.parametrize('historical_bad', [False, True])
def test_capture_uses_two_fresh_projects_and_never_carries_historical_settings_into_default(
    historical, tmp_path, monkeypatch, historical_bad
):
    events, projects = [], []
    real_qualifier = written.qualify_historical

    class Analysis:
        def __init__(self):
            object.__setattr__(self, 'edits', [])
            object.__setattr__(self, 'descent', 'multistart_prune')
            object.__setattr__(self, 'stop_rules', 'chi_square_change shift_su')
            object.__setattr__(self, 'fitting_mode', 'joint')

        def __setattr__(self, key, value):
            self.edits.append((key, value))
            object.__setattr__(self, key, value)

    def load(source):
        assert source == historical.source, 'Each phase loads the exact authenticated source'
        if projects:
            assert 'historical-qualified' in events, (
                'Current loading cannot precede successful full historical qualification'
            )
        project = SimpleNamespace(
            analysis=Analysis(),
            su_rule='iucr_99',
            free_parameters=[None] * 193,
            _minimizer_max_iterations=1000,
            _minimizer_chi_square_tolerance=1e-4,
        )
        projects.append(project)
        events.append('load')
        return project

    def fit(project, loaded):
        if len(projects) == 2:
            assert project is not projects[0], (
                'The default run cannot reuse the fitted historical model'
            )
            assert project.analysis.edits == [], 'The current default receives no setter overrides'
            assert loaded['descent'] == 'multistart_prune', (
                'The fresh default keeps its actual descent'
            )
            events.append('current-start')
            raise StopBeforeCurrentFitError
        assert dict(project.analysis.edits) == solver_vehicles.HISTORICAL, (
            'Exactly the two historically backed selectors change before the historical fit'
        )
        assert len(project.analysis.edits) == 2, 'Historical setup cannot retune another setting'
        raw = copy.deepcopy(historical.raw)
        if historical_bad:
            raw['values'][next(iter(raw['values']))] += 1
        events.append('historical-fit')
        return raw, object()

    def qualified(*args, **kwargs):
        result = real_qualifier(*args, **kwargs)
        events.append('historical-qualified')
        return result

    monkeypatch.setattr(written.edi, 'Project', SimpleNamespace(load=load))
    monkeypatch.setattr(written, 'fit_with_trace', fit)
    monkeypatch.setattr(written, 'qualify_historical', qualified)
    monkeypatch.setattr(
        written.edi, 'machine_report', lambda *_args: report_text(historical.record)
    )
    destination = tmp_path / 'not-a-qualified-capture'
    expected = ValueError if historical_bad else StopBeforeCurrentFitError
    with pytest.raises(expected):
        written.capture(
            ROOT,
            'ncaf',
            destination,
            written.sha(written.edi._edi.__file__),
            written.edi.__build_commit__,
        )
    assert len(projects) == (1 if historical_bad else 2), (
        'A failed historical reference blocks the fresh current run completely'
    )
    assert not (destination / 'result.json').exists(), (
        'Control-flow spies stop before Save and can never produce qualification evidence'
    )


@pytest.fixture
def capsule(historical, current, tmp_path):
    """A literal metadata envelope deliberately stops before real array validation."""
    reference = tmp_path / 'protocol-envelope'
    (reference / 'historical').mkdir(parents=True)
    project = reference / 'project'
    (project / 'analysis').mkdir(parents=True)
    (project / 'analysis/analysis.edi').write_text(
        '_fit_result.iterations '
        + str(current.raw['iterations'])
        + '\n_fit_result.descent multistart_prune\n'
    )
    for directory, state in ((reference / 'historical', historical), (reference, current)):
        (directory / 'loaded.json').write_text(json.dumps(state.loaded))
        (directory / 'raw.json').write_text(json.dumps(state.raw))
        (directory / 'machine.txt').write_text(report_text(state.record))
    for name in ('raw-arrays.npz', 'written-arrays.npz', 'reopened-arrays.npz'):
        (reference / name).write_bytes(b'intentionally invalid: no mocked array qualification')
    producer = {
        'schema': 'ordinary-native-written/3',
        'case': 'ncaf',
        'project': historical.fixture['project'],
        'source_files': written.files(historical.source),
        'current_files': solver_vehicles.current_references(historical.fixture, historical.source),
        'fixture_files': {
            name: written.sha(
                ROOT / 'tests/fixtures/e04_t11_wasm/catalogue_scientific' / ('ncaf-' + name)
            )
            for name in ('native.json', 'conditioning.json', 'conditioning-raw.json')
        },
        'recorder_sha256': written.sha(written.__file__),
        'solver_checker_sha256': written.sha(solver_vehicles.__file__),
        'iteration_checker_sha256': written.sha(iteration_domains.__file__),
        'iteration_domains_sha256': written.sha(iteration_domains.HERE / 'iteration-domains.json'),
        'module_sha256': written.sha(written.edi._edi.__file__),
        'module_path': written.edi._edi.__file__,
        'build_commit': written.edi.__build_commit__,
        'python': 'literal-protocol-control',
        'recorder_path': written.__file__,
    }
    (reference / 'producer.json').write_text(json.dumps(producer))
    captured = [
        str(path.relative_to(reference))
        for path in reference.rglob('*')
        if path.is_file() and not path.is_relative_to(project) and path.name != 'producer.json'
    ]
    result = {
        'producer_sha256': written.sha(reference / 'producer.json'),
        'files': written.files(project),
        'captures': {name: written.sha(reference / name) for name in captured},
        'capture_flags': dict.fromkeys(
            ('raw', 'ordinary_save', 'reopen', 'arrays', 'source_unchanged'), True
        ),
    }
    (reference / 'result.json').write_text(json.dumps(result))
    return reference


def array_boundary(*_args):
    raise ReachedArrayValidationError


def test_admission_requires_both_real_qualifiers_before_ordinary_arrays(capsule, monkeypatch):
    events = []
    for name in ('qualify_historical', 'qualify_current'):
        real = getattr(written, name)

        def observing(*args, _name=name, _real=real, **kwargs):
            result = _real(*args, **kwargs)
            events.append(_name)
            return result

        monkeypatch.setattr(written, name, observing)
    monkeypatch.setattr(written, 'validate_arrays', array_boundary)
    with pytest.raises(ReachedArrayValidationError):
        written.admit(ROOT, 'ncaf', capsule)
    assert events == ['qualify_historical', 'qualify_current'], (
        'Success flags cannot replace historical and current-default numerical checks'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'missing-historical-loaded',
        'missing-historical-raw',
        'missing-historical-report',
        'historical-value',
        'historical-report-value',
        'historical-loaded-alias',
        'current-loaded-alias',
        'expected-hash',
        'provenance-hash',
        'solver-hash',
    ],
)
def test_capture_custody_cannot_skip_or_resign_a_failed_vehicle(capsule, monkeypatch, escape):
    monkeypatch.setattr(written, 'validate_arrays', array_boundary)
    with pytest.raises(ReachedArrayValidationError):
        written.admit(ROOT, 'ncaf', capsule)
    result_path, producer_path = capsule / 'result.json', capsule / 'producer.json'
    result = json.loads(result_path.read_text())
    producer = json.loads(producer_path.read_text())
    if escape.startswith('missing-historical'):
        name = {
            'missing-historical-loaded': 'historical/loaded.json',
            'missing-historical-raw': 'historical/raw.json',
            'missing-historical-report': 'historical/machine.txt',
        }[escape]
        result['captures'].pop(name)
    elif escape in {
        'historical-value',
        'historical-report-value',
        'historical-loaded-alias',
        'current-loaded-alias',
    }:
        name = alter_capture(capsule, escape)
        result['captures'][name] = written.sha(capsule / name)
    else:
        if escape == 'solver-hash':
            producer['solver_checker_sha256'] = '0' * 64
        else:
            name = 'expected.json' if escape == 'expected-hash' else 'PROVENANCE.md'
            producer['current_files'][name] = '0' * 64
        producer_path.write_text(json.dumps(producer))
        result['producer_sha256'] = written.sha(producer_path)
    result_path.write_text(json.dumps(result))
    with pytest.raises((ValueError, OSError)):
        written.admit(ROOT, 'ncaf', capsule)


def alter_capture(reference, escape):
    if escape == 'historical-report-value':
        name = 'historical/machine.txt'
        path = reference / name
        record = fields(path.read_text())
        key = next(key for key in record if key.startswith('param.') and key.endswith('.value'))
        record[key] = str(float(record[key]) + 1)
        path.write_text(report_text(record))
        return name
    name = (
        'loaded.json'
        if escape == 'current-loaded-alias'
        else ('historical/raw.json' if escape == 'historical-value' else 'historical/loaded.json')
    )
    path = reference / name
    data = json.loads(path.read_text())
    if escape == 'historical-value':
        data['values'][next(iter(data['values']))] += 1
    else:
        data['max_iterations'] = 1000.0
    path.write_text(json.dumps(data))
    return name


@pytest.mark.parametrize('historical_bad', [False, True])
def test_wasm_orchestration_checks_historical_vehicle_before_current_default(
    historical, current, tmp_path, monkeypatch, historical_bad
):
    events = []
    reference = tmp_path / 'reference'
    (reference / 'ncaf').mkdir(parents=True)
    (reference / 'ncaf/machine.txt').write_text(report_text(current.record))
    executable = tmp_path / 'compiled-cli.js'
    monkeypatch.setenv('EDI_WASM_CLI_MULTITHREAD', str(executable))
    monkeypatch.setenv('EDI_WASM_WRITTEN_REFERENCE', str(reference))

    def admitted(root, case, path):
        assert (root, case, path) == (ROOT, 'ncaf', reference / 'ncaf'), (
            'WASM orchestration must request its declared native capture and case'
        )
        events.append('native-admission-requested')
        return historical.fixture

    def run(argv, **kwargs):
        assert argv[:3] == ['node', str(executable.resolve()), 'fit'], (
            'Both solver vehicles use the actual declared compiled WASM CLI entrypoint'
        )
        assert argv[4:] == ['--dry', '--verbosity', 'full'], (
            'Both solver vehicles retain dry execution and FULL raw report evidence'
        )
        assert kwargs['check'] is False and kwargs['capture_output'] is True, (
            'The host retains process failure and report evidence for both vehicles'
        )
        project = Path(argv[3])
        if project.name == 'historical':
            assert events == ['native-admission-requested'], (
                'Historical WASM execution precedes current-default execution'
            )
            before = (historical.source / 'analysis/analysis.edi').read_bytes()
            after = (project / 'analysis/analysis.edi').read_bytes()
            assert after == before + (
                b'\n_minimizer.descent ladder\n_minimizer.stop_rules chi_square_change\n'
            ), 'The historical WASM command receives only its two declared solver additions'
            events.append('historical-executed')
            record = dict(historical.record)
            if historical_bad:
                record['iterations'] = '16'
        else:
            assert events[-1] == 'historical-qualified', (
                'Failed historical WASM qualification prevents all current execution'
            )
            assert written.files(project) == written.files(historical.source), (
                'Current WASM execution receives the untouched original default input'
            )
            events.append('current-executed')
            record = current.record
        return SimpleNamespace(returncode=0, stdout=report_text(record), stderr='')

    real_historical = solver_vehicles.qualify_historical_report
    real_parity = iteration_domains.compare_runtime

    def qualified(*args):
        real_historical(*args)
        events.append('historical-qualified')

    def parity(*args):
        real_parity(*args)
        events.append('current-parity-checked')
        raise StopBeforeCurrentFitError

    monkeypatch.setattr(written, 'admit', admitted)
    monkeypatch.setattr(wasm_fit.subprocess, 'run', run)
    monkeypatch.setattr(solver_vehicles, 'qualify_historical_report', qualified)
    monkeypatch.setattr(iteration_domains, 'compare_runtime', parity)
    with pytest.raises(ValueError if historical_bad else StopBeforeCurrentFitError):
        wasm_fit.test_catalogue_wasm_continuation_matches_current_native_work(
            tmp_path / 'work', 'ncaf'
        )
    assert events == (
        ['native-admission-requested', 'historical-executed']
        if historical_bad
        else [
            'native-admission-requested',
            'historical-executed',
            'historical-qualified',
            'current-executed',
            'current-parity-checked',
        ]
    ), 'A refused historical vehicle cannot be replaced by current backend parity'
