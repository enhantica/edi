"""Decimal save references; no product imports (ADR-0092)."""

import math
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from tests.fixtures.adp_site_symmetry.model import equivalent
from tests.fixtures.report_units.iucr_reference import rounded_pair

PAIRS = [
    (2.16352, 0.00481),
    (-2.16352, 0.00481),
    (1.54249, 0.01532),
    (0.4637, 0.0196),
    (54912.0, 1234.0),
    (0.000183461, 0.000087),
    (0.1234567, 0.00201),
]


def expected_pair(value, su, rule):
    return rounded_pair(value, su, rule or 'iucr_99')


def six_digits(value):
    number = Decimal(str(value))
    quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - 5)
    return float(number.quantize(quantum, rounding=ROUND_HALF_UP))


def declared_rule(folder):
    path = Path(folder) / 'project.edi'
    match = (
        re.search(r'(?m)^_su_format\.rule\s+(\S+)', path.read_text()) if path.is_file() else None
    )
    return match[1].strip('"') if match else 'iucr_99'


def saved_triplet(value, uncertainty, free, rule='iucr_99'):
    """Independent Edi persisted state; bare fixed tokens read back as engaged zero."""
    if free and uncertainty is not None and math.isfinite(uncertainty) and uncertainty > 0:
        return (*expected_pair(value, uncertainty, rule), free)
    su = 0.0 if not free or uncertainty == 0 else None
    return six_digits(value), su, free


def saved_parameters(project, rule):
    """Project only persisted parameters; derive tensor equivalents from the rounded metric."""
    parameters = list(project.parameters)
    expected = [saved_triplet(p.value, p.uncertainty, p.free, rule) for p in parameters]
    positions = {id(p): i for i, p in enumerate(parameters)}
    derived = set()
    for structure in project.structures:
        cell = [
            saved_triplet(p.value, p.uncertainty, p.free, rule)[0]
            for p in (
                getattr(structure.cell, name)
                for name in (
                    'length_a',
                    'length_b',
                    'length_c',
                    'angle_alpha',
                    'angle_beta',
                    'angle_gamma',
                )
            )
        ]
        tensors = {row.id: row for row in structure.atom_site_aniso}
        for site in structure.atom_sites:
            if site.adp_type not in {'Uani', 'Bani', 'beta'}:
                continue
            tensor = tensors[site.id]
            values = [
                saved_triplet(p.value, p.uncertainty, p.free, rule)[0]
                for p in (
                    getattr(tensor, 'adp_' + suffix)
                    for suffix in ('11', '22', '33', '12', '13', '23')
                )
            ]
            index = positions[id(site.adp_iso)]
            expected[index] = (
                equivalent({'cell': cell}, site.adp_type, values),
                expected[index][1],
                expected[index][2],
            )
            derived.add(index)
    return expected, derived


def require_saved_parameters(parameters, reference):
    expected, derived = reference
    actual = [(p.value, p.uncertainty, p.free) for p in parameters]
    assert len(actual) == len(expected), 'Save retains the complete model parameter population'
    for index, (got, wanted) in enumerate(zip(actual, expected, strict=True)):
        assert got[1:] == wanted[1:], (
            'Save retains independently projected uncertainty and free state'
        )
        if index in derived:
            assert math.isclose(got[0], wanted[0], rel_tol=2e-14, abs_tol=2e-14), (
                'The isotropic mirror follows the tensor trace with the independently rounded cell'
            )
        else:
            assert got[0] == wanted[0], (
                'Persisted parameters follow exact independent decimal rounding'
            )
