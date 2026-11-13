"""Keep historical regression and current-default backend checks in their own conditions."""

import hashlib
import json
import math
import shutil
from pathlib import Path

import gemmi

from tests.fixtures.e04_t11_wasm import iteration_domains
from tests.fixtures.e04_t11_wasm.cli_domains import fields
from tests.fixtures.web_parallel import numeric
from tools.checks import cli_projects

HISTORICAL = {'descent': 'ladder', 'stop_rules': 'chi_square_change'}


# Existing accepted CLI references; hashes bind their complete quantities and provenance.
CURRENT_REFERENCES = {
    'docs/user/cli/pd-neut-cwl_lbco-hrpt/project': {
        'expected.json': 'b89875d83f247a48f60fa5cbe0056ef2917a7a366375d01402fa570862b022b5',
        'PROVENANCE.md': '90b455d5331bbd17a104732786f78e15b2cf62680cce4115246bd0a9d3276d4a',
        'quantities': '833b2d42dde4118eb3132e2ffb1ec76005163c66a8ccf199c8446ad5fe84f67b',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project': {
        'expected.json': '087d6d65e541fd4fdb27626bc49f5e58a239df68a9d4055d1413b2be8452fd59',
        'PROVENANCE.md': 'e337c12c9bf7160a139fe4236a04a22d2e7dca4aa59139eb5fe9636c32bb89ee',
        'quantities': '30ab78c5fbaf1b256407b7e279371fe0a4631bbe1af9c0446fed8de19fc414be',
    },
}


def reference_binding(fixture):
    """Select a closed existing reference owner, never a caller-supplied reference digest."""
    binding = CURRENT_REFERENCES.get(fixture.get('project'))
    if binding is None:
        raise ValueError('Current reference has no declared catalogue input owner')
    return binding


def current_references(fixture, source):
    """Authenticate complete current reference and provenance bytes before capture."""
    binding = reference_binding(fixture)
    observed = {
        name: hashlib.sha256((source.parent / name).read_bytes()).hexdigest()
        for name in ('expected.json', 'PROVENANCE.md')
    }
    if any(observed[name] != binding[name] for name in observed):
        raise ValueError('Current reference or provenance differs from its declared hash')
    return observed


def historical(fixture, raw, report):
    """Authenticate a real execution of the captured solver's stopping conditions."""
    trace = raw.get('iteration_domain', {})
    conditions = trace.get('conditions', {})
    if (
        conditions != {**HISTORICAL, 'max_iterations': 1000}
        or type(conditions.get('max_iterations')) is not int
    ):
        raise ValueError('Historical execution changed its declared solver conditions')
    record, rows = iteration_domains.history(report, 1000)
    expected = {
        'descent': HISTORICAL['descent'],
        'stopping_rule': HISTORICAL['stop_rules'],
        'multistart_prune': 'false',
        **dict.fromkeys(iteration_domains.WORK_FIELDS[:-1], '0'),
        'multistart_survivor': 'none',
    }
    if (
        any(record.get(key) != value for key, value in expected.items())
        or type(raw.get('iterations')) is not int
        or raw['iterations'] != len(rows)
    ):
        raise ValueError('Historical execution report differs from its real solver conditions')
    iteration_domains.compare_callbacks(trace.get('callbacks'), rows, fixture)


def current(fixture, old, raw, report, selected, expected):
    """Retain the whole raw population and the existing independent CLI references."""
    binding = reference_binding(fixture)
    digest = hashlib.sha256(
        json.dumps(expected, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    if digest != binding['quantities']:
        raise ValueError('Current reference quantities differ from their declared hash')
    iteration_domains.current(fixture, raw, report)
    record = fields(report)
    wanted = {}
    for column, path in selected.items():
        for name, public in (('value', 'values'), ('uncertainty', 'uncertainty')):
            wanted[f'param.{old["labels"][column]}.{name}'] = raw[public][path]
    if {key for key in record if key.startswith('param.')} != wanted.keys():
        raise ValueError('Current FULL report changed the complete raw parameter population')
    for key, value in wanted.items():
        actual = iteration_domains.number(record[key])
        su = key.endswith('.uncertainty')
        if not math.isclose(
            actual,
            value,
            rel_tol=numeric._UNCERTAINTY_RELATIVE if su else fixture['relative_tolerance'],
            abs_tol=numeric._UNCERTAINTY_ABSOLUTE if su else fixture['absolute_tolerance'],
        ):
            raise ValueError('Current FULL report differs from its raw fitted value or SU')
    initial = raw.get('initial_reduced_chi_square')
    if type(initial) not in {int, float} or not math.isclose(
        initial,
        fixture['native_start_and_finish']['initial_reduced_chi_square'],
        rel_tol=fixture['relative_tolerance'],
        abs_tol=fixture['absolute_tolerance'],
    ):
        raise ValueError('Current execution changed the original initial chi-square')
    if expected.get('schema') != 1 or not expected.get('quantities'):
        raise ValueError('Current execution requires the existing independent CLI references')
    for key, specification in expected['quantities'].items():
        if key not in record or cli_projects._deviations(key, specification, float(record[key])):
            raise ValueError('Current fit differs from its existing CLI reference: ' + key)


def qualify_historical_report(fixture, old, report):
    """Compare observable historical WASM operands directly to every frozen column."""
    record, rows = iteration_domains.history(report, 1000)
    n = len(old['labels'])
    wanted = {
        'status': 'done',
        'converged': 'true',
        'descent': HISTORICAL['descent'],
        'stopping_rule': HISTORICAL['stop_rules'],
        'multistart_prune': 'false',
        **dict.fromkeys(iteration_domains.WORK_FIELDS[:-1], '0'),
        'multistart_survivor': 'none',
        'n_free': str(n),
        'n_points_fitted': str(old['n_data']),
        'iterations': str(old['iterations']),
    }
    if (
        any(record.get(key) != value for key, value in wanted.items())
        or len(rows) != old['iterations']
    ):
        raise ValueError('Historical WASM report changed its original condition or population')
    if len(old['values']) != n or len(old['covariance']) != n * n:
        raise ValueError('Historical WASM comparison requires every original covariance column')
    parameters = {}
    for column, label in enumerate(old['labels']):
        diagonal = old['covariance'][column * n + column]
        if diagonal < 0:
            raise ValueError('Historical WASM covariance diagonal must be nonnegative')
        parameters[f'param.{label}.value'] = old['values'][column]
        parameters[f'param.{label}.uncertainty'] = math.sqrt(diagonal)
    if {key for key in record if key.startswith('param.')} != parameters.keys():
        raise ValueError('Historical WASM report lost an original value or SU column')
    parameters['reduced_chi_square'] = fixture['native_start_and_finish'][
        'final_reduced_chi_square'
    ]
    parameters['rwp'] = fixture['native_start_and_finish']['rwp']
    for key, expected in parameters.items():
        actual = iteration_domains.number(record[key])
        su = key.endswith('.uncertainty')
        if not math.isclose(
            actual,
            expected,
            rel_tol=numeric._UNCERTAINTY_RELATIVE if su else fixture['relative_tolerance'],
            abs_tol=numeric._UNCERTAINTY_ABSOLUTE if su else fixture['absolute_tolerance'],
        ):
            raise ValueError(
                'Historical WASM value or SU differs from its original anchor: ' + key
            )


def vehicle(source, destination):
    """Copy exact catalogue bytes, adding only the historically backed solver declarations."""
    source, destination = Path(source), Path(destination)
    original = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob('*')
        if path.is_file()
    }
    analysis = 'analysis/analysis.edi'
    if analysis not in original:
        raise ValueError('Historical vehicle needs the original analysis declarations')
    block = gemmi.cif.read_string(
        'data_historical_vehicle\n' + original[analysis].decode('utf-8')
    ).sole_block()
    selectors = {'_minimizer.descent', '_minimizer.stop_rules', '_minimizer.stop_rule'}
    for item in block:
        tags = (
            [item.pair[0]]
            if item.pair is not None
            else item.loop.tags
            if item.loop is not None
            else []
        )
        if any(tag.lower() in selectors for tag in tags):
            raise ValueError('Historical vehicle cannot override an explicit source solver')
    suffix = b'\n_minimizer.descent ladder\n_minimizer.stop_rules chi_square_change\n'
    shutil.copytree(source, destination)
    (destination / analysis).write_bytes(original[analysis] + suffix)
    actual = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob('*')
        if path.is_file()
    }
    if actual != {**original, analysis: original[analysis] + suffix}:
        raise ValueError('Historical vehicle changed an input outside its solver declarations')
