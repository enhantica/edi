"""A successful scientific save remains in the loader's physical and numeric domain."""

import math
import re
import shutil
from decimal import Decimal

import edi as engine
import pytest

from tests.fixtures.report_units.iucr_reference import rounded_pair
from tests.integration.py.test_report_iucr_persistence import project
from tests.integration.py.test_report_storage import inventory

CASES = {
    'alpha-endpoint': ([4.1, 4.2, 4.3, 179.99, 90, 90], [0, 0, 0, 3, 0, 0]),
    'beta-endpoint': ([4.1, 4.2, 4.3, 90, 179.99, 90], [0, 0, 0, 0, 3, 0]),
    'gamma-endpoint': ([4.1, 4.2, 4.3, 90, 90, 179.99], [0, 0, 0, 0, 0, 3]),
    'joint-degenerate': ([4.1, 4.2, 4.3, 60.049, 60.049, 120.051], [0, 0, 0, 3, 3, 3]),
    'volume-overflow': ([5.5e102] * 3 + [90, 90, 90], [3e102] * 3 + [0, 0, 0]),
    'reciprocal-overflow': ([7.49e-155, 4.2, 4.3, 90, 90, 90], [3e-155, 0, 0, 0, 0, 0]),
    'ordinary-control': ([4.1234, 4.2345, 4.3456, 79.1234, 88.1234, 97.1234], [0.003] * 6),
    'nonzero-control': ([0.0023, 4.2, 4.3, 90, 90, 90], [0.019, 0, 0, 0, 0, 0]),
}
NAMES = ['length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma']


def realizable(values):
    a, b, c, alpha, beta, gamma = values
    if not all(math.isfinite(x) and x > 0 for x in (a, b, c)):
        return False
    if not all(math.isfinite(x) and 0 < x < 180 for x in (alpha, beta, gamma)):
        return False
    ca, cb, cg = [math.cos(math.radians(x)) for x in (alpha, beta, gamma)]
    determinant = 1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg
    # The exact trigonometric boundary is degenerate even when libm leaves a positive ulp.
    if (
        min(
            alpha + beta - gamma,
            alpha + gamma - beta,
            beta + gamma - alpha,
            360 - alpha - beta - gamma,
        )
        <= 0
        or determinant <= 0
    ):
        return False
    volume = a * b * c * math.sqrt(determinant)
    if not math.isfinite(volume) or volume <= 0:
        return False
    lengths = [b * c, a * c, a * b]
    reciprocal = [
        length * math.sin(math.radians(angle)) / volume
        for length, angle in zip(lengths, (alpha, beta, gamma), strict=True)
    ]
    return all(math.isfinite(x * x) for x in reciprocal)


def cell_input(path, values, state):
    record = path / 'structures/phase.edi'
    text = record.read_text()
    for name, value in zip(NAMES, values, strict=True):
        token = format(Decimal(str(value)), 'f') + ('()' if state == 'free' else '')
        text = re.sub(
            r'^_cell\.' + name + r'\s+\S+', '_cell.' + name + ' ' + token, text, flags=re.MULTILINE
        )
    record.write_text(text)
    if state == 'dependent':
        analysis = path / 'analysis/analysis.edi'
        aliases = 'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        aliases += ''.join(f'c{i} phase.cell.{name}\n' for i, name in enumerate(NAMES))
        constraints = 'loop_\n_constraint.expression\n'
        constraints += ''.join(f'"c{i} = {value!r}"\n' for i, value in enumerate(values))
        analysis.write_text(analysis.read_text() + '\n' + aliases + constraints)


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('state', ['free', 'fixed', 'dependent'])
@pytest.mark.parametrize('case', CASES)
def test_rounded_cell_must_remain_readable_or_refuse_before_publication(
    tmp_path, rule, operation, state, case
):
    path = project(tmp_path, '4()', rule)
    values, uncertainties = CASES[case]
    rounded = [
        rounded_pair(v, u, rule)[0] if state != 'fixed' else v
        for v, u in zip(values, uncertainties, strict=True)
    ]
    assert realizable(values), 'The authored cell starts inside the independent metric domain'
    cell_input(path, values, state)
    loaded = engine.Project.load(path)
    for name, su in zip(NAMES, uncertainties, strict=True):
        getattr(loaded.structures[0].cell, name).uncertainty = su
    before = inventory(path)
    destination = path if operation == 'save' else tmp_path / 'destination'
    if operation == 'save-as':
        shutil.copytree(path, destination)
        (destination / 'retained.txt').write_bytes(b'independent destination bytes')
    previous = inventory(destination)
    try:
        loaded.save() if operation == 'save' else loaded.save_as(destination)
    except (OSError, ValueError, RuntimeError):
        assert not realizable(rounded), (
            'Fixed and ordinarily rounded cells inside the reader domain must save successfully'
        )
        assert inventory(path) == before, 'A physical-domain refusal preserves all source bytes'
        assert inventory(destination) == previous, (
            'A physical-domain refusal preserves the pre-existing destination bytes'
        )
        return
    if operation == 'save-as':
        assert inventory(path) == before, 'Successful Save as retains every source byte'
    try:
        restored = engine.Project.load(destination)
    except (OSError, ValueError, RuntimeError) as error:
        pytest.fail('A successful save must be accepted by its scientific loader: ' + str(error))
    actual = [getattr(restored.structures[0].cell, name).value for name in NAMES]
    assert realizable(actual), (
        'Successful tokens retain angle bounds, positive volume and finite reciprocal metric'
    )
    text = next((destination / 'structures').glob('*.edi')).read_text()
    persisted = [
        float(re.search(r'^_cell\.' + name + r'\s+([^\s(]+)', text, re.MULTILINE)[1])
        for name in NAMES
    ]
    assert realizable(persisted), (
        'The written cell satisfies the metric domain before constraints or save adoption'
    )
    if realizable(rounded) and state != 'dependent':
        assert persisted == rounded, 'Ordinary and fixed tokens retain independent IUCr rounding'
    else:
        assert all(a in {v, r} for a, v, r in zip(persisted, values, rounded, strict=True)), (
            'Readable tokens use source values or independent rounding without invented geometry'
        )
    if state == 'dependent':
        assert all(a in {v, r} for a, v, r in zip(actual, values, rounded, strict=True)), (
            'Constraints may restore their declared constants within the same physical domain'
        )
    else:
        assert actual == persisted, 'Reload retains the exact physical values actually written'


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('state', ['free', 'fixed'])
def test_rounded_line_shift_pair_stays_inside_the_loader_joint_domain(
    tmp_path, rule, operation, state
):
    path = project(tmp_path, '4()', rule)
    record = path / 'experiments/bank.edi'
    values = [9e307, 8.9e307]
    terms = ['calib_sample_displacement', 'calib_sample_transparency']
    text = ''.join(
        f'\n_instrument.{term} {format(Decimal(str(value)), "f")}'
        + ('()' if state == 'free' else '')
        for term, value in zip(terms, values, strict=True)
    )
    record.write_text(record.read_text() + text + '\n')
    loaded = engine.Project.load(path)
    for term in terms:
        getattr(loaded.experiments['bank'].instrument, term).uncertainty = 3e307
    before = inventory(path)
    destination = path if operation == 'save' else tmp_path / 'destination'
    if operation == 'save-as':
        shutil.copytree(path, destination)
    original = inventory(destination)
    rounded = [rounded_pair(v, 3e307, rule)[0] if state != 'fixed' else v for v in values]
    try:
        loaded.save() if operation == 'save' else loaded.save_as(destination)
    except (OSError, ValueError, RuntimeError):
        assert not math.isfinite(sum(abs(v) for v in rounded)), (
            'Representable ordinary or fixed line-shift pairs must still save successfully'
        )
        assert inventory(path) == before, 'A joint-domain refusal preserves all source bytes'
        assert inventory(destination) == original, (
            'A joint-domain refusal preserves all destination bytes'
        )
        return
    try:
        restored = engine.Project.load(destination)
    except (OSError, ValueError, RuntimeError) as error:
        pytest.fail('Successful rounded line-shift pairs must remain loadable: ' + str(error))
    actual = [getattr(restored.experiments['bank'].instrument, term).value for term in terms]
    assert math.isfinite(sum(abs(v) for v in actual)), (
        'Individually finite serialized shifts must also retain their finite joint magnitude'
    )
    assert actual in [values, rounded], (
        'A joint-domain fallback retains source values or independent IUCr rounding'
    )
