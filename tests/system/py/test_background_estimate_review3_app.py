"""Bounded real app worker, type/basis edit, delegated save and typed Undo entries."""

import copy
import json
import os
import re
import subprocess
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

import edi as engine
import gemmi
import numpy as np
import pytest

from tests.fixtures.background_estimate.readonly import materialize as manual_input
from tests.fixtures.background_estimate.review3 import (
    basis,
    estimate_control,
    materialize,
    rows,
    state,
)
from tests.fixtures.project_save.reference import declared_rule, saved_triplet
from tests.fixtures.saved_spelling.reference import NUMBER, decode

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'transition_line_segment_polynomial',
    'undo_line_segment_polynomial',
    'transition_line_segment_chebyshev',
    'undo_line_segment_chebyshev',
    'transition_polynomial_line_segment',
    'undo_polynomial_line_segment',
    'transition_polynomial_chebyshev',
    'undo_polynomial_chebyshev',
    'transition_chebyshev_line_segment',
    'undo_chebyshev_line_segment',
    'transition_chebyshev_polynomial',
    'undo_chebyshev_polynomial',
    'basis_polynomial_origin',
    'basis_chebyshev_x_min',
    'basis_chebyshev_x_max',
    'mixed_line_segment_single',
    'mixed_line_segment_joint',
    'mixed_polynomial_single',
    'mixed_polynomial_joint',
    'mixed_chebyshev_single',
    'mixed_chebyshev_joint',
    'delegated_polynomial',
    'delegated_chebyshev',
]


def iucr19_value(value, uncertainty):
    """Independent decimal construction from the declared IUCr rule (ADR-0092).

    Round s.u. up to two digits, retain 10-19 and a carried 10, otherwise one;
    round the value half away from zero to that last digit, preserving nonzero.
    """
    if uncertainty is None or not np.isfinite(uncertainty) or uncertainty <= 0:
        return value
    with localcontext() as context:
        context.prec = 350
        v, su = Decimal(str(value)), Decimal(str(uncertainty))
        quantum = Decimal(1).scaleb(su.adjusted() - 1)
        leading = (su / quantum).to_integral_value(rounding=ROUND_CEILING)
        if leading >= 20:
            quantum = Decimal(1).scaleb(su.adjusted())
        rounded = v.quantize(quantum, rounding=ROUND_HALF_UP)
        if v != 0 and rounded == 0:
            digits = 2 if leading < 20 or leading == 100 else 1
            quantum = Decimal(1).scaleb(v.copy_abs().adjusted() - digits + 1)
            rounded = v.quantize(quantum, rounding=ROUND_HALF_UP)
        return float(rounded)


def saved_background_parameters(experiment):
    points = experiment.background_type == 'line-segment'
    native_rows = experiment.background if points else experiment.background_terms
    return [
        (p.value, p.uncertainty, p.free)
        for row in native_rows
        for p in [row.intensity if points else row.coef]
    ]


def undo_save_projection(receipt):
    before = receipt['before_save']
    assert before['suRule'] in {'iucr_19', 'iucr_99'}, (
        'The actual project declares a supported rule'
    )
    assert receipt['su_rule'] == before['suRule'], 'Save cannot switch uncertainty rules'
    state = before['state']
    active = 'points' if state['type'] == 'line-segment' else 'terms'
    inactive = 'terms' if active == 'points' else 'points'
    assert state[inactive] == [], 'The restored typed state has only its declared row family'
    assert len(state[active]) == len(before['parameters']), (
        'Every pre-Save row has a parameter witness'
    )
    expected = []
    for row, p in zip(state[active], before['parameters'], strict=True):
        assert set(p) == {'id', 'value', 'free', 'hasUncertainty', 'uncertainty', 'refinable'}, (
            'Each pre-Save parameter witness has the complete explicit scalar/presence schema'
        )
        assert np.isfinite(p['value']), 'The ordinary pre-Save parameter value is finite'
        assert [p['id'], p['value'], p['free']] == [row[0], row[2], row[3]], (
            'The pre-Save witness belongs to the exact original row value and free flag'
        )
        assert p['refinable'] is True, (
            'This ordinary scalar fixture does not impersonate a constrained value'
        )
        assert isinstance(p['hasUncertainty'], bool), 'Optional uncertainty presence is explicit'
        assert np.isfinite(p['uncertainty']) and p['uncertainty'] >= 0, (
            'The SU witness is finite and valid'
        )
        assert p['hasUncertainty'] or p['uncertainty'] == 0, (
            'Absent frontend SU projects to zero only'
        )
        uncertainty = p['uncertainty'] if p['hasUncertainty'] else None
        expected.append(saved_triplet(p['value'], uncertainty, p['free'], before['suRule']))
    return active, expected


def written_background_triplet(token):
    if re.fullmatch(NUMBER, token):
        return float(token), None, False
    value, uncertainty = decode(token)
    return value, uncertainty, True


def require_undo_saved_state(receipt, native_rows, native_parameters):
    active, expected = undo_save_projection(receipt)
    before = receipt['before_save']['state']
    projected = copy.deepcopy(before)
    for row, (value, _su, _free) in zip(projected[active], expected, strict=True):
        row[2] = value
    assert receipt['state'] == projected, (
        'Only independently predicted parameter values may change; '
        'every descriptor and row stays exact'
    )
    assert [list(row) for row in native_rows] == projected[active], (
        'The actual reopened file retains the exact projected typed rows'
    )
    assert native_parameters == expected, (
        'The reopened optional SU/value/free state matches the independent reference'
    )
    assert len(receipt['parameters']) == len(expected), (
        'The adopted host retains every parameter witness'
    )
    for p, row, (value, su, free) in zip(
        receipt['parameters'], projected[active], expected, strict=True
    ):
        assert p == {
            'id': row[0],
            'value': value,
            'free': free,
            'hasUncertainty': su is not None,
            'uncertainty': 0 if su is None else su,
            'refinable': True,
        }, 'The adopted host agrees on value, explicit uncertainty presence and free state'
    block = gemmi.cif.read_string(receipt['file']).sole_block()
    assert block.name == 'd20', 'The actual file is the same restored experiment, not another bank'
    assert gemmi.cif.as_string(block.find_value('_background.type')) == before['type']
    assert gemmi.cif.as_string(block.find_value('_background_estimate.mode')) == before['mode']
    for field, tag in [('origin', 'origin'), ('low', 'x_min'), ('high', 'x_max')]:
        token = block.find_value('_background.' + tag)
        if before[field] is None:
            assert token is None, 'Absent optional background constants stay absent'
        else:
            assert float(token) == before[field], (
                'Descriptor constants retain exact round-trip values'
            )
    ids = [gemmi.cif.as_string(v) for v in block.find_values('_background.id')]
    coordinates = list(
        block.find_values('_background.position' if active == 'points' else '_background.order')
    )
    values = list(
        block.find_values('_background.intensity' if active == 'points' else '_background.coef')
    )
    assert ids == [r[0] for r in projected[active]], (
        'File row identities/order are complete and exact'
    )
    assert len(ids) == len(set(ids)), 'No saved background identity is duplicated'
    assert len(ids) == len(coordinates) == len(values), (
        'Every row retains its descriptor and value token'
    )
    for row, coordinate, token, (value, su, free) in zip(
        projected[active], coordinates, values, expected, strict=True
    ):
        assert float(coordinate) == row[1], (
            'Positions/orders are descriptors, never rounded parameters'
        )
        actual = written_background_triplet(token)
        assert actual[0] == value and actual[2] is free, (
            'The file value/free marker matches pre-Save projection'
        )
        assert actual[1] == (su if free else None), (
            'Bare/fitted/absent/engaged-zero SU tokens remain distinct'
        )


@pytest.mark.parametrize('case', CASES)
def test_app_estimate_lifecycle_crosses_each_publication_boundary(tmp_path, case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The lifecycle sweep requires the actual built production Qt host'
    selected = 'BackgroundReview3::test_' + case
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_review3.qml'),
            selected,
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    if case.startswith('undo_'):
        (tmp_path / 'undo-save-output.json').write_text(
            json.dumps({'output': output}, ensure_ascii=True)
        )
    assert result.returncode == 0 and f'PASS   : edi_app::{selected}()' in output, (
        'Auto refresh, fit publication, save and typed Undo must remain coherent: ' + output
    )
    assert 'BACKGROUND_REVIEW3' in output, (
        'The real app sweep must reach its final lifecycle receipt'
    )
    if case.startswith('basis_'):
        receipt = json.loads(re.findall(r'BACKGROUND_REVIEW3_BASIS (\{[^\n]+\})', output)[0])
        project = engine.Project.load(materialize(tmp_path / 'control', receipt['kind']))
        project.experiment.background_estimate.use_model = 'ignore'
        project.analysis.calculate()
        basis(project.experiment, receipt['field'])
        expected = estimate_control(project)
        np.testing.assert_allclose(
            [r[2] for r in receipt['rows']],
            [r[2] for r in expected],
            rtol=1e-11,
            atol=1e-8,
            err_msg='App basis edits must estimate the fresh Python control coefficients',
        )

    # A bounded Qt producer proves the live action and writes its actual file.
    # Its complementary loader checks exact typed persistence and unchanged
    # calculation here, rather than opening a second full window inside one deadline.
    if case.startswith(('delegated_', 'transition_', 'undo_', 'mixed_')):
        receipt = json.loads(re.findall(r'BACKGROUND_REVIEW3_SAVED (\{[^\n]+\})', output)[0])
        source = materialize(tmp_path / 'app-saved', receipt['kind'])
        (source / 'experiments/d20.edi').write_text(receipt['file'])
        if case.startswith('undo_'):
            (source / 'project.edi').write_text(receipt['project_file'])
            assert declared_rule(source) == receipt['before_save']['suRule'], (
                'The actual saved project file carries the selected pre-Save rule'
            )
        loaded = engine.Project.load(source)
        if case.startswith('undo_'):
            require_undo_saved_state(
                receipt, rows(loaded.experiment), saved_background_parameters(loaded.experiment)
            )
        host = receipt['state']
        expected = [
            host['type'],
            host['origin'],
            host['low'],
            host['high'],
            host['mode'],
            host['points'] if host['type'] == 'line-segment' else host['terms'],
        ]
        assert json.loads(json.dumps(state(loaded.experiment))) == expected, (
            'Every app lifecycle save must write the exact typed background published to its host'
        )
        if case.startswith('mixed_'):
            observed = rows(loaded.experiment)
            live, uncertainties = receipt['live_rows'], receipt['live_su']
            assert len(observed) == len(live) == len(uncertainties), (
                'Saving a fitted background must preserve every live row '
                'and its uncertainty witness'
            )
            for actual, prior, uncertainty in zip(observed, live, uncertainties, strict=True):
                assert actual[:2] == tuple(prior[:2]) and actual[3] == prior[3], (
                    'IUCr save normalization must preserve fitted ids, '
                    'positions/orders and free flags'
                )
                assert actual[2] == iucr19_value(prior[2], uncertainty), (
                    'Saving fitted Auto values must use the declared independent IUCr decimal rule'
                )
        before = rows(loaded.experiment)
        loaded.analysis.calculate()
        assert rows(loaded.experiment) == before, (
            'The actual app lifecycle file must reload and calculate '
            'without replacing its saved rows'
        )
        if case.startswith('undo_'):
            require_undo_saved_state(
                receipt, rows(loaded.experiment), saved_background_parameters(loaded.experiment)
            )


def undo_observation_control(value, uncertainty, present, free, rule, token, native_su):
    # Authored observation records validate the boundary checker, not a fake
    # product/Qt owner and not claimed real Save branch coverage.
    row_data = [[f'control{i}', i, value, free] for i in range(2)]
    state = {
        'type': 'polynomial',
        'mode': 'manual',
        'origin': 80,
        'low': None,
        'high': None,
        'points': [],
        'terms': row_data,
    }
    before_parameters = [
        {
            'id': r[0],
            'value': value,
            'free': free,
            'hasUncertainty': present,
            'uncertainty': uncertainty,
            'refinable': True,
        }
        for r in row_data
    ]
    # Offered native SU is a literal input anchored in Edi io.cpp and the
    # actual parser tests, independent of saved_triplet's predicted optionality.
    triplet = (written_background_triplet(token)[0], native_su, free)
    after = copy.deepcopy(state)
    for row in after['terms']:
        row[2] = triplet[0]
    receipt = {
        'before_save': {'state': state, 'parameters': before_parameters, 'suRule': rule},
        'state': after,
        'su_rule': rule,
        'parameters': [
            dict(
                p,
                value=triplet[0],
                hasUncertainty=triplet[1] is not None,
                uncertainty=0 if triplet[1] is None else triplet[1],
            )
            for p in before_parameters
        ],
        'file': 'data_d20\n_background.type polynomial\n_background_estimate.mode manual\n'
        '_background.origin 80\nloop_\n_background.id\n_background.order\n_background.coef\n'
        + ''.join(f'{r[0]} {r[1]} {token}\n' for r in row_data),
    }
    return receipt, copy.deepcopy(after['terms']), [triplet] * len(row_data)


def undo_observation_mutants(receipt):
    # Every mutation changes a receipt field while preserving its authored
    # comparison/input witness; no current product output becomes expected data.
    mutations = []
    for field, value in [('type', 'chebyshev'), ('mode', 'auto'), ('origin', 81)]:
        changed = copy.deepcopy(receipt)
        changed['state'][field] = value
        mutations.append(changed)
    for field, value in [
        ('value', 0),
        ('free', not receipt['parameters'][0]['free']),
        ('hasUncertainty', not receipt['parameters'][0]['hasUncertainty']),
    ]:
        changed = copy.deepcopy(receipt)
        changed['parameters'][0][field] = (
            value if field != 'value' else receipt['parameters'][0]['value'] + 1
        )
        mutations.append(changed)
    for operation in ['missing', 'duplicate', 'reordered', 'id', 'descriptor']:
        changed = copy.deepcopy(receipt)
        rows = changed['state']['terms']
        if operation == 'missing':
            rows.pop()
        elif operation == 'duplicate':
            rows.append(copy.deepcopy(rows[0]))
        elif operation == 'reordered':
            rows.reverse()
        elif operation == 'id':
            rows[0][0] = 'other'
        else:
            rows[0][1] += 1
        mutations.append(changed)
    changed = copy.deepcopy(receipt)
    changed['su_rule'] = 'iucr_19' if receipt['su_rule'] == 'iucr_99' else 'iucr_99'
    mutations.append(changed)
    if receipt['before_save']['parameters'][0]['free']:
        changed = copy.deepcopy(receipt)
        changed['before_save']['parameters'][0]['hasUncertainty'] = not changed['before_save'][
            'parameters'
        ][0]['hasUncertainty']
        mutations.append(changed)
    changed = copy.deepcopy(receipt)
    changed['file'] = changed['file'].replace('control1 1 ', 'control0 1 ', 1)
    mutations.append(changed)
    changed = copy.deepcopy(receipt)
    changed['file'] = changed['file'].replace('control0 0 ', 'control0 0.5 ', 1)
    mutations.append(changed)
    changed = copy.deepcopy(receipt)
    changed['file'] = changed['file'].replace('data_d20', 'data_other', 1)
    mutations.append(changed)
    return mutations


@pytest.mark.parametrize(
    ('value', 'uncertainty', 'present', 'free', 'rule', 'token', 'native_su'),
    [
        (1.23456789, 0, False, True, 'iucr_99', '1.23457()', None),
        (1.23456789, 0, True, True, 'iucr_99', '1.23457(0)', 0.0),
        (1.23456789, 0, False, False, 'iucr_99', '1.23457', 0.0),
        (1.23456789, 0.03456, True, False, 'iucr_99', '1.23457', 0.0),
        (1.23456789, 0.03456, True, True, 'iucr_19', '1.23(4)', 0.04),
        (1.23456789, 0.03456, True, True, 'iucr_99', '1.235(35)', 0.035),
        (1.234565, 0, False, True, 'iucr_99', '1.23457()', None),
        (-1.234565, 0, False, True, 'iucr_99', '-1.23457()', None),
        (0, 0, False, True, 'iucr_99', '0()', None),
        (0.0001, 0.02, True, True, 'iucr_19', '0.0001(0.02)', 0.02),
    ],
)
def test_undo_save_receipt_optional_uncertainties_and_corruption_controls(
    value, uncertainty, present, free, rule, token, native_su
):
    receipt, native_rows, native_parameters = undo_observation_control(
        value, uncertainty, present, free, rule, token, native_su
    )
    require_undo_saved_state(receipt, native_rows, native_parameters)
    for damaged in undo_observation_mutants(receipt):
        assert damaged != receipt, 'Every independently authored observation counterfeit is armed'
        with pytest.raises(AssertionError):
            require_undo_saved_state(damaged, native_rows, native_parameters)
    reordered = list(reversed(native_rows))
    assert reordered != native_rows, (
        'The native row-order counterfeit uses distinct real identities'
    )
    with pytest.raises(AssertionError):
        require_undo_saved_state(receipt, reordered, native_parameters)
    partial = list(native_parameters)
    v, su, f = partial[0]
    partial[0] = (v, 0 if su is None else None, f)
    assert partial != native_parameters, 'The reopened optional-SU counterfeit is armed'
    with pytest.raises(AssertionError):
        require_undo_saved_state(receipt, native_rows, partial)
    # Optional-SU and free markers are actual file syntax, not interchangeable
    # zero-valued frontend projections. The literal token is independently authored.
    changed = copy.deepcopy(receipt)
    wrong = token.split('(', 1)[0] + ('()' if '(' not in token else '(0.123)')
    changed['file'] = changed['file'].replace(token, wrong, 1)
    assert changed != receipt, 'The raw-file marker/value adversary really reaches the first token'
    with pytest.raises(AssertionError):
        require_undo_saved_state(changed, native_rows, native_parameters)


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_fixed_pre_save_optional_states_have_one_positive_canonical_readback(rule):
    receipt, native_rows, native_parameters = undo_observation_control(
        1.23456789, 0, False, False, rule, '1.23457', 0.0
    )
    assert native_parameters == [(1.23457, 0.0, False)] * 2, (
        'The offered native positive is a literal engaged-zero readback, never helper prediction'
    )
    for present, uncertainty in [(False, 0), (True, 0), (True, 0.03456)]:
        equivalent = copy.deepcopy(receipt)
        for p in equivalent['before_save']['parameters']:
            p.update(hasUncertainty=present, uncertainty=uncertainty)
        # These are valid different PRE-Save inputs with the SAME bare token and
        # fixed adopted engaged-zero result. They are positive canonicalization,
        # not corrupt observable outputs that must spuriously fail.
        require_undo_saved_state(equivalent, native_rows, native_parameters)


@pytest.mark.parametrize('prior_su', [None, 0.0, 0.03456])
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_real_fixed_save_adopts_literal_native_zero_from_each_optional_input(
    tmp_path, prior_su, rule
):
    source = manual_input(tmp_path / 'fixed-source', 'line-segment')
    project = engine.Project.load(source)
    project.su_rule = rule
    project.experiment.background[0].intensity = engine.Parameter(1.23456789, prior_su, False)
    parameter = project.experiment.background[0].intensity
    assert (parameter.value, parameter.uncertainty, parameter.free) == (
        1.23456789,
        prior_su,
        False,
    ), 'The actual public owner reaches the requested distinct raw optional fixed input'
    assert saved_triplet(parameter.value, parameter.uncertainty, parameter.free, rule) == (
        1.23457,
        0.0,
        False,
    ), 'The shared persisted reference agrees with the independently literal Edi readback'
    destination = tmp_path / 'fixed-saved'
    project.save_as(destination)
    file = destination / 'experiments/bank.edi'
    block = gemmi.cif.read_string(file.read_text()).sole_block()
    assert next(iter(block.find_values('_background.intensity'))) == '1.23457', (
        'The actual file has a bare fixed token with no syntactic bracket/SU'
    )
    reopened = engine.Project.load(destination)
    assert declared_rule(destination) == rule, (
        'Both selected rules retain their project declaration'
    )
    for parameter in [
        project.experiment.background[0].intensity,
        reopened.experiment.background[0].intensity,
    ]:
        assert (parameter.value, parameter.uncertainty, parameter.free) == (1.23457, 0.0, False), (
            'Actual adopting Save AND native readback expose engaged zero '
            'for every fixed prior state'
        )
