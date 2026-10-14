"""Exact tensor zeros from the reciprocal-cell closed form."""

import math

import pytest

from tests.integration.py.test_anisotropic_adps import (
    load_project,
    loop_rows,
    saved,
    structure_text,
)

CELLS = {
    'cubic': [5.3, 5.3, 5.3, 90, 90, 90],
    'tetragonal': [4.1, 4.1, 7.9, 90, 90, 90],
    'orthorhombic': [3.7, 5.2, 8.1, 90, 90, 90],
    'hexagonal': [4.1, 4.1, 7.9, 90, 90, 120],
    'monoclinic': [4.2, 5.7, 8.3, 90, 104, 90],
}
SUFFIXES = ('11', '22', '33', '12', '13', '23')
BISO = 0.73


def closed_tensor(cell, target):  # noqa: PLR0914 — retain named reciprocal-cell quantities
    a, b, c, alpha, beta, gamma = cell
    ca, cb, cg = [0.0 if x == 90 else math.cos(math.radians(x)) for x in (alpha, beta, gamma)]
    sa, sb, sg = [math.sin(math.radians(x)) for x in (alpha, beta, gamma)]
    volume = a * b * c * math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)
    reciprocal = (b * c * sa / volume, a * c * sb / volume, a * b * sg / volume)
    cosines = (
        1,
        1,
        1,
        (ca * cb - cg) / (sa * sb),
        (ca * cg - cb) / (sa * sg),
        (cb * cg - ca) / (sb * sg),
    )
    u = BISO / (8 * math.pi**2)
    pairs = ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2))
    if target == 'Uani':
        return [u * x for x in cosines]
    if target == 'Bani':
        return [BISO * x for x in cosines]
    return [
        2 * math.pi**2 * u * x * reciprocal[i] * reciprocal[j]
        for x, (i, j) in zip(cosines, pairs, strict=True)
    ]


@pytest.mark.parametrize('cell_name', CELLS)
@pytest.mark.parametrize('target', ['Uani', 'Bani', 'beta'])
@pytest.mark.parametrize('route', ['change', 'load-missing-tensor'])
def test_isotropic_tensor_preserves_exact_zeros_and_oblique_values(
    tmp_path, cell_name, target, route
):
    cell = CELLS[cell_name]
    reference = {'cell': cell, 'Biso': BISO}
    text = structure_text('Biso', reference)
    if route == 'load-missing-tensor':
        text = text.replace('X O a Biso ', f'X O a {target} ')
        if target == 'Uani':
            text = text.replace(f'1 {BISO:.17g}', f'1 {BISO / (8 * math.pi**2):.17g}')
    project = load_project(tmp_path / 'input', text)
    if route == 'change':
        project.structure.atom_sites[0].adp_iso.uncertainty = 0.031
        project.structure.atom_sites[0].adp_type = target
    output = saved(project, tmp_path / 'output')
    row = loop_rows(output, '_atom_site_aniso')[0]
    for suffix, expected in zip(SUFFIXES, closed_tensor(cell, target), strict=True):
        token = row['_atom_site_aniso.adp_' + suffix]
        component = getattr(project.structure.atom_site_aniso[0], 'adp_' + suffix)
        actual = component.value
        if expected == 0:
            assert actual == 0, 'Right-angle tensor components must be exactly zero'
            assert float(token.split('(')[0]) == 0, 'Saved exact zeros must remain exactly zero'
            assert component.uncertainty is None, (
                'The model must not assign an s.u. to an exact zero'
            )
            assert '(' not in token, 'A symmetry-exact zero must carry no numerical uncertainty'
        else:
            assert actual == pytest.approx(expected, rel=2e-14, abs=0), (
                'Oblique components and tensor units must agree with the reciprocal-cell '
                'closed form'
            )
    if cell_name == 'monoclinic':
        assert closed_tensor(cell, target)[4] != 0, (
            'The oblique control must retain its nonzero U13'
        )
