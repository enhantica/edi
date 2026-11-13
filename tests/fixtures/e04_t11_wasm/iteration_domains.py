"""Authenticate historical counters; compare current work in its actual solver domain.

The solver counts the reported continuation separately from both probes. The old
ladder captures remain immutable numerical references, not current counter pins.
"""

import hashlib
import json
import math
import re
from pathlib import Path

from tests.fixtures.e04_t11_wasm.cli_domains import fields

HERE = Path(__file__).resolve().parent
HISTORY_FIELDS = {'rwp', 'reduced_chi_square', 'unevaluable_trials', 'elapsed_ms'}
WORK_FIELDS = (
    'multistart_probes_started',
    'multistart_probes_pruned',
    'multistart_probe_iterations',
    'multistart_survivor',
)


CAPTURE_FILES = {'native.json', 'native-report.txt', 'conditioning.json', 'conditioning-raw.json'}
CURRENT = {
    'conditions': {'descent': 'multistart_prune', 'stop_rules': 'chi_square_change shift_su'},
    'probe_horizon': 3,
}
EXACT_FIELDS = (
    'status',
    'converged',
    'mode',
    'n_points_loaded',
    'n_points_fitted',
    'n_free',
    'iterations',
    'descent',
    'stopping_rule',
    'multistart_prune',
    *WORK_FIELDS,
)


def declaration(value=None):
    value = json.loads((HERE / 'iteration-domains.json').read_text()) if value is None else value
    if not isinstance(value, dict) or value.keys() != {
        'schema',
        'authority',
        'historical',
        'current',
    }:
        raise ValueError('Iteration domain declaration requires its exact schema fields')
    if (
        value['schema'] != 'catalogue-iteration-domains/1'
        or value['authority'] != ['edi ADR-0023']
        or value['current'] != CURRENT
        or not isinstance(value['historical'], dict)
        or value['historical'].keys() != {'lbco', 'ncaf'}
    ):
        raise ValueError('Iteration domain declaration changed its schema or current authority')
    if type(value['current']['probe_horizon']) is not int:
        raise ValueError('Iteration probe horizon requires its declared integer type')
    for owner in value['historical'].values():
        if not isinstance(owner, dict) or owner.keys() != {'project_sha256', 'descent', 'files'}:
            raise ValueError('Historical iteration declaration requires its closed owner schema')
        if (
            owner['descent'] != 'ladder'
            or not isinstance(owner['files'], dict)
            or owner['files'].keys() != CAPTURE_FILES
        ):
            raise ValueError('Historical iteration declaration requires all four custody channels')
        for digest in (owner['project_sha256'], *owner['files'].values()):
            if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ValueError(
                    'Historical iteration custody requires canonical SHA256 identities'
                )
    return value


def integer(value, *, positive=False):
    if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]*', value):
        raise ValueError('Iteration work requires canonical ASCII integer fields')
    result = int(value)
    if positive and not result:
        raise ValueError('Iteration work requires a positive completed count')
    return result


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Iteration history requires finite numeric operands')
    return result


def history(report, maximum):
    record = fields(report)
    count = integer(record.get('iterations'), positive=True)
    if count > maximum:
        raise ValueError('Iteration count exceeds its declared budget')
    rows = {}
    for key, value in record.items():
        if not key.startswith('iter.'):
            continue
        match = re.fullmatch(r'iter\.([1-9][0-9]*)\.(\w+)', key)
        if match is None:
            raise ValueError('Iteration history has a malformed row identity')
        ordinal, field = match.groups()
        rows.setdefault(int(ordinal), {})[field] = value
    if list(rows) != list(range(1, count + 1)) or any(
        row.keys() != HISTORY_FIELDS for row in rows.values()
    ):
        raise ValueError(
            'Iteration history must contain every ordered continuation row exactly once'
        )
    for row in rows.values():
        for field in ('rwp', 'reduced_chi_square', 'elapsed_ms'):
            if number(row[field]) < 0:
                raise ValueError('Iteration history operands must be nonnegative')
        integer(row['unevaluable_trials'])
    return record, rows


def historical(root, case, fixture, raw):
    domains = declaration()
    owner = domains['historical'][case]
    directory = root / 'tests/fixtures/e04_t11_wasm/catalogue_scientific'
    for suffix, digest in owner['files'].items():
        path = directory / (case + '-' + suffix)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Historical iteration custody changed')
    report, _ = history((directory / (case + '-native-report.txt')).read_text(), 1000)
    scalars = dict(row for row in fixture['scientific']['analysis/analysis.edi'] if len(row) == 2)
    count = integer(report['iterations'], positive=True)
    if (
        fixture['native_start_and_finish']['iterations'] != count
        or raw['iterations'] != count
        or scalars['_fit_result.iterations'] != str(count)
        or report['descent'] != owner['descent']
        or scalars['_fit_result.descent'] != owner['descent']
    ):
        raise ValueError('Historical count and descent differ across authenticated captures')
    if fixture['project_sha256'] != owner['project_sha256']:
        raise ValueError('Historical iteration input identity changed')
    return domains['current']


def compare_callbacks(callbacks, rows, fixture):
    if not isinstance(callbacks, list) or len(callbacks) != len(rows):
        raise ValueError('Current callbacks must cover every reported continuation iteration')
    for ordinal, callback in enumerate(callbacks, 1):
        if not isinstance(callback, dict) or callback.keys() != {
            'iteration',
            'rwp',
            'reduced_chi_square',
        }:
            raise ValueError('Current callback requires its complete typed record')
        if type(callback.get('iteration')) is not int or callback['iteration'] != ordinal:
            raise ValueError('Current callback ordinals must be complete and strictly ordered')
        for field in ('rwp', 'reduced_chi_square'):
            value = callback[field]
            if (
                type(value) not in {int, float}
                or not math.isfinite(value)
                or not math.isclose(
                    value,
                    number(rows[ordinal][field]),
                    rel_tol=fixture['relative_tolerance'],
                    abs_tol=fixture['absolute_tolerance'],
                )
            ):
                raise ValueError('Current callback operands differ from the FULL report history')


def current(fixture, raw, report):
    """The callback trace is actual fit work; report rows are a second observation."""
    domain = fixture['_iteration_domain']
    observed = raw.get('iteration_domain', {})
    if not isinstance(observed, dict) or observed.keys() != {'conditions', 'callbacks'}:
        raise ValueError('Current iteration trace requires a typed record')
    expected = {**domain['conditions'], 'max_iterations': 1000}
    if (
        observed.get('conditions') != expected
        or type(observed['conditions']['max_iterations']) is not int
    ):
        raise ValueError('Current iteration conditions differ from the declared domain before fit')
    record, rows = history(report, expected['max_iterations'])
    required_runtime(record)
    count = integer(record['iterations'], positive=True)
    if type(raw.get('iterations')) is not int or raw['iterations'] != count:
        raise ValueError('Current terminal count must equal the FULL report history')
    for field, key in (('rwp', 'rwp'), ('reduced_chi_square', 'final_reduced_chi_square')):
        if not math.isclose(
            number(record[field]),
            raw[key],
            rel_tol=fixture['relative_tolerance'],
            abs_tol=fixture['absolute_tolerance'],
        ):
            raise ValueError('Current raw terminal operands differ from the FULL report')
    compare_callbacks(observed.get('callbacks'), rows, fixture)
    if (
        record.get('descent') != expected['descent']
        or record.get('stopping_rule') not in expected['stop_rules'].split()
        or record.get('multistart_prune') != 'true'
    ):
        raise ValueError('Current report must confirm the actual solver and stopping domain')
    return record


def required_runtime(record):
    if not {*EXACT_FIELDS, 'rwp', 'reduced_chi_square'} <= record.keys():
        raise ValueError('Current runtime report is missing a required field')
    if (
        record['status'] != 'done'
        or record['converged'] != 'true'
        or record['mode'] not in {'single', 'joint'}
        or record['descent'] != CURRENT['conditions']['descent']
        or record['stopping_rule'] not in CURRENT['conditions']['stop_rules'].split()
    ):
        raise ValueError('Current runtime report differs from the declared completed domain')
    if record['multistart_prune'] != 'true':
        raise ValueError('Current runtime must retain its actual multistart selection')
    started = integer(record[WORK_FIELDS[0]], positive=True)
    pruned = integer(record[WORK_FIELDS[1]])
    probes = integer(record[WORK_FIELDS[2]], positive=True)
    if (
        started != 2
        or pruned != 1
        or not started <= probes <= started * CURRENT['probe_horizon']
        or record[WORK_FIELDS[3]] not in {'ladder', 'fast_descent'}
    ):
        raise ValueError('Current probe work must remain separate from continuation history')
    loaded = integer(record['n_points_loaded'], positive=True)
    fitted = integer(record['n_points_fitted'], positive=True)
    free = integer(record['n_free'], positive=True)
    if not free < fitted <= loaded:
        raise ValueError('Current runtime point and free counts must retain their actual domain')
    for key in ('rwp', 'reduced_chi_square'):
        if number(record[key]) < 0:
            raise ValueError('Current runtime requires nonnegative physical operands')


def compare_runtime(report, reference, fixture):
    """Same input/conditions, two real backends: no scalar counter golden is minted."""
    actual, rows = history(report, 1000)
    expected, native_rows = history(reference, 1000)
    required_runtime(actual)
    required_runtime(expected)
    for key in EXACT_FIELDS:
        if actual[key] != expected[key]:
            raise ValueError('Current native and WASM iteration conditions or work differ: ' + key)
    parameters = {key for key in expected if key.startswith('param.')}
    if parameters != {key for key in actual if key.startswith('param.')}:
        raise ValueError('Current native and WASM fitted parameter inventories differ')
    for key in ('rwp', 'reduced_chi_square', *sorted(parameters)):
        if not math.isclose(
            number(actual[key]),
            number(expected[key]),
            rel_tol=fixture['relative_tolerance'],
            abs_tol=fixture['absolute_tolerance'],
        ):
            raise ValueError('Current native and WASM terminal physical operands differ')
    if rows.keys() != native_rows.keys():
        raise ValueError('Current native and WASM continuation inventories differ')
    for ordinal, row in rows.items():
        if row['unevaluable_trials'] != native_rows[ordinal]['unevaluable_trials']:
            raise ValueError('Current native and WASM rejected-trial work differs')
        for key in ('rwp', 'reduced_chi_square'):
            if not math.isclose(
                number(row[key]),
                number(native_rows[ordinal][key]),
                rel_tol=fixture['relative_tolerance'],
                abs_tol=fixture['absolute_tolerance'],
            ):
                raise ValueError('Current native and WASM continuation operands differ')


def saved(project, raw, report):
    """Ordinary Save carries the current result, and reopening must retain all bytes."""
    text = (project / 'analysis/analysis.edi').read_text()
    for tag, wanted in (
        ('iterations', str(raw['iterations'])),
        ('descent', fields(report)['descent']),
    ):
        matches = re.findall(r'^_fit_result\.' + tag + r'\s+(\S+)\s*$', text, re.MULTILINE)
        if matches != [wanted]:
            raise ValueError('Saved iteration count/descent differs from the actual current fit')
