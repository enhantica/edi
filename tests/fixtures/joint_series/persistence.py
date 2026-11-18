"""Independent persistence transforms and preservation checks (ADRs 0088/0092/0132)."""

import itertools
from decimal import ROUND_HALF_UP, Decimal

import gemmi
import numpy as np

from tests.fixtures.joint_series import cases, oracle

CELL_ITEMS = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
MOMENT_NAMES = ['phase.atom_site_moment.A.crystalaxis_' + axis for axis in 'xyz']
MOMENT_NAMES += ['phase.cell.' + item for item in CELL_ITEMS]


def significant(value, digits):
    number = Decimal(str(value))
    if not number:
        return 0.0
    place = Decimal(1).scaleb(number.copy_abs().adjusted() - digits + 1)
    return float(number.quantize(place, rounding=ROUND_HALF_UP))


def adopted_covariance(values, errors, covariance):
    pairs = np.array(
        list(itertools.starmap(oracle.reported_pair, zip(values, errors, strict=True)))
    )
    rho = covariance / np.sqrt(np.outer(np.diag(covariance), np.diag(covariance)))
    rho = np.array([[significant(r, 3 if abs(r) >= 0.95 else 2) for r in row] for row in rho])
    return pairs[:, 0], pairs[:, 1], rho, rho * np.outer(pairs[:, 1], pairs[:, 1])


def correlations(text, names, expected):
    block = gemmi.cif.read_string('data_analysis\n' + text).sole_block()
    rows = block.find([
        '_fit_parameter_correlation.parameter_unique_name_i',
        '_fit_parameter_correlation.parameter_unique_name_j',
        '_fit_parameter_correlation.correlation',
    ])
    wanted = {
        frozenset((names[i], names[j])): expected[i, j]
        for i, j in itertools.combinations(range(len(names)), 2)
    }
    actual = {}
    for row in rows:
        key = frozenset((row[0], row[1]))
        assert key not in actual, 'Saved covariance must not duplicate an independent pair'
        actual[key] = float(row[2])
    assert actual.keys() == wanted.keys(), (
        'Saved covariance must preserve the complete authored independent pair table'
    )
    np.testing.assert_allclose(
        list(actual.values()),
        [wanted[k] for k in actual],
        rtol=0,
        atol=1e-14,
        err_msg='Saved correlations must preserve independently rounded input covariance',
    )


def moment_reference(root, inputs, covariance):
    values, errors, rho, adopted = adopted_covariance(
        inputs, np.sqrt(np.diag(covariance)), covariance
    )
    saved = gemmi.cif.read_file(str(root / 'structures/phase.edi')).sole_block()
    tags = ['_atom_site_moment.crystalaxis_' + axis for axis in 'xyz']
    tags += ['_cell.' + item for item in CELL_ITEMS]
    actual = [oracle.token_pair(next(iter(saved.find_values(tag)))) for tag in tags]
    np.testing.assert_allclose(
        actual,
        np.column_stack((values, errors)),
        rtol=0,
        atol=1e-13,
        err_msg='Saved independent moment values and marginals must preserve authored inputs',
    )
    correlations((root / 'analysis/analysis.edi').read_text(), MOMENT_NAMES, rho)
    # The writer is checked, never used as the scientific reference.
    return cases.propagated_spherical(values, adopted)


def volume(cell):
    angles = np.cos(np.radians(cell[3:]))
    a, b, g = angles
    return np.prod(cell[:3]) * np.sqrt(1 + 2 * a * b * g - a * a - b * b - g * g)


def adopted_fraction(values, errors, covariance, cells):
    seeds, marginal, rho, adopted = adopted_covariance(values, errors, covariance)
    cells = np.array([[significant(v, 6) for v in cell] for cell in cells])
    first, second = [volume(cell) for cell in cells]
    u, v, _t = seeds
    total = u * first + v * second
    gradient = np.array([-v, u, 0]) * first * second / total**2
    return {
        'values': seeds,
        'errors': marginal,
        'rho': rho,
        'cells': cells,
        'fraction': v * second / total,
        'sigma': float(np.sqrt(gradient @ adopted @ gradient)),
    }


def check_adopted(project, parameters, reference):
    np.testing.assert_allclose(
        [(p.value, p.uncertainty) for p in parameters],
        np.column_stack((reference['values'], reference['errors'])),
        rtol=0,
        atol=1e-13,
        err_msg='Adopting Save must independently round each fitted seed and marginal',
    )
    cells = [
        [getattr(project.structures[phase].cell, item).value for item in CELL_ITEMS]
        for phase in ('phase', 'other')
    ]
    np.testing.assert_allclose(
        cells,
        reference['cells'],
        rtol=0,
        atol=1e-13,
        err_msg='Adopting Save must round fixed cells before Hill-Howard propagation',
    )
