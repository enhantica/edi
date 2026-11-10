"""Declaration edits invalidate results and obey save admission (ADR-0078)."""

import runpy
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
ALIASES = [('a', 'phase.atom_site.A.adp_iso'), ('b', 'phase.atom_site.B.adp_iso')]


@pytest.mark.parametrize('category', ['data', 'refln'])
def test_declaration_only_change_renews_held_computed_category(tmp_path, category):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'input', ALIASES, ['b = 2*a + 1']))
    project.analysis.calculate()
    held = project.experiment.data if category == 'data' else project.experiment.refln
    field = 'intensity_calc' if category == 'data' else 'f_squared_calc'
    before = np.asarray(getattr(held, field)).copy()
    target = project.structure.atom_sites[1].adp_iso
    state = (target.value, target.free, target.user_constrained)
    project.analysis.constraints['b'].expression = 'b = 3*a + 1'
    assert (target.value, target.free, target.user_constrained) == state, (
        'the witness must change only the declaration, with no incidental parameter write'
    )
    renewed = np.asarray(getattr(held, field)).copy()
    assert target.value == pytest.approx(1.9, abs=2e-14), (
        'a held category read must apply the new expression at a=0.3'
    )
    assert not np.allclose(renewed, before, equal_nan=True), (
        'the old computed array must not survive a physically different declaration'
    )
    project.analysis.calculate()
    assert np.allclose(renewed, getattr(held, field), equal_nan=True, rtol=1e-12, atol=1e-12), (
        'lazy renewal must equal a subsequent explicit calculation of the same declaration'
    )


@pytest.mark.parametrize('invalid', ['reserved', 'dangling'])
@pytest.mark.parametrize('history', ['alias-only', 'last-removed', 'disabled'])
def test_invalid_alias_save_refuses_before_disk_publication(tmp_path, invalid, history):
    expressions = [] if history == 'alias-only' else ['b = 2*a + 1']
    project = engine.Project.load(MATERIALIZE(tmp_path / 'input', ALIASES, expressions))
    if history == 'last-removed':
        project.analysis.constraints.remove('b')
    elif history == 'disabled':
        project.analysis.constraints['b'].enabled = False
    if invalid == 'reserved':
        project.analysis.aliases['a'].id = 'sin'
    else:
        project.structure.atom_sites.remove('A')
    destination = tmp_path / 'output'
    destination.mkdir()
    sentinel = destination / 'keep.txt'
    sentinel.write_text('caller-owned bytes')
    before = {
        p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()
    }
    with pytest.raises(
        (ValueError, RuntimeError), match=r'(?i)alias|reserved|unknown|parameter|constraint'
    ):
        project.save_as(destination)
    after = {
        p.relative_to(destination): p.read_bytes() for p in destination.rglob('*') if p.is_file()
    }
    assert after == before, (
        'invalid alias admission must publish no file and retain existing bytes'
    )


def test_relation_removal_restores_no_loop_bytes_and_disabled_values_stay_bare(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'input'))
    project.save_as(tmp_path / 'before')
    project.analysis.aliases.create(id='a', param=project.structure.atom_sites[0].adp_iso)
    project.analysis.aliases.create(id='b', param=project.structure.atom_sites[1].adp_iso)
    project.analysis.constraints.create(expression='b = 2*a + 1')
    project.analysis.constraints['b'].enabled = False
    project.save_as(tmp_path / 'disabled')
    reopened = engine.Project.load(tmp_path / 'disabled')
    assert reopened.structure.atom_sites[1].adp_iso.value == pytest.approx(0.8, abs=1e-15), (
        'saving a disabled declaration must preserve its target value without applying it'
    )
    assert not reopened.analysis.constraints['b'].enabled, (
        'saving must retain the disabled declaration'
    )
    project.analysis.constraints.remove('b')
    project.analysis.aliases.remove('a')
    project.analysis.aliases.remove('b')
    project.save_as(tmp_path / 'after')
    for relative in ('analysis/analysis.edi', 'structures/phase.edi', 'experiments/bank.edi'):
        assert (tmp_path / 'before' / relative).read_bytes() == (
            tmp_path / 'after' / relative
        ).read_bytes(), (
            'removing the last declarations must restore no-loop serialization byte for byte'
        )
