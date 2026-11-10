"""Geometry renewal follows declared values and Cartesian closed forms."""

import runpy
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]


@pytest.mark.parametrize('family', ['coordinate', 'cell'])
@pytest.mark.parametrize('entry', ['stored', 'window'])
@pytest.mark.parametrize('invalid', [False, True])
def test_geometry_read_completes_declaration_only_changes(tmp_path, family, entry, invalid):
    left, right = (
        ('phase.cell.length_a', 'phase.cell.length_b')
        if family == 'cell'
        else ('phase.atom_site.A.fract_x', 'phase.atom_site.B.fract_y')
    )
    expression = 'b = 1.2*a' if family == 'cell' else 'b = 2*a + .1'
    project = engine.Project.load(MATERIALIZE(tmp_path, [('a', left), ('b', right)], [expression]))
    project.analysis.calculate()
    structure = project.structure
    held = structure.geometry()
    assert held.is_current(), 'the held window control must begin current'
    project.analysis.constraints['b'].expression = (
        'b = missing' if invalid else ('b = 1.3*a' if family == 'cell' else 'b = 3*a + .1')
    )
    stale = not held.is_current()
    if invalid:
        with pytest.raises(
            (ValueError, RuntimeError), match=r'(?i)constraint|alias|unknown|relation|missing'
        ):
            _ = (
                structure.expanded_atom_sites.fract_y
                if entry == 'stored'
                else structure.geometry()
            )
        assert stale, 'an invalid declaration must revoke held window currentness'
        return
    geometry = structure if entry == 'stored' else structure.geometry()
    atoms = geometry.expanded_atom_sites
    target = structure.cell.length_b if family == 'cell' else structure.atom_sites[1].fract_y
    assert target.value == pytest.approx(5.33 if family == 'cell' else 0.61, abs=2e-13), (
        'a geometry read must apply the edited dependent value'
    )
    indices = [i for i, name in enumerate(atoms.atom_site_id) if name == 'B']
    assert indices, 'the renewed geometry must contain the dependent atom'
    for i in indices:
        expected = 5.33 * 0.23 if family == 'cell' else 4.1 * 0.61
        assert atoms.cartn_y[i] == pytest.approx(expected, abs=2e-12), (
            'Cartesian coordinates must use the closed-form dependent coordinate or cell length'
        )
    assert stale, 'a declaration-only edit must revoke held window currentness'
