"""Public free writes follow current measurements, links and declared dependence."""

import importlib
import re
import warnings
from pathlib import Path

import pytest

from tests.fixtures.fittability.inputs import CELL_FIELDS, materialize

ROOT = Path(__file__).resolve().parents[3]
DATA = "this fit's data cannot determine it"
CAPABILITY = 'the fit cannot vary it yet'


@pytest.fixture(scope='module')
def api():
    return importlib.import_module('edi')


def require_refusal(parameter, reason):
    with pytest.raises(ValueError, match=re.escape(reason)) as error:
        parameter.free = True
    assert 'cannot be fitted:' in str(error.value), (
        'A public free refusal uses the common parameter-and-reason message'
    )
    assert not parameter.free, 'A refused free assignment preserves the false flag'
    parameter.free = False


@pytest.mark.parametrize('field', CELL_FIELDS)
def test_every_independent_single_crystal_cell_degree_is_blocked(api, tmp_path, field):
    project = api.Project.load(materialize(tmp_path / field))
    require_refusal(getattr(project.structure.cell, field), DATA)


@pytest.mark.parametrize('mixed', [False, True])
@pytest.mark.parametrize('field', CELL_FIELDS)
def test_cubic_metric_precedes_context_and_powder_frees_only_a(api, tmp_path, mixed, field):
    project = api.Project.load(materialize(tmp_path / 'cell', cubic=True, mixed=mixed))
    parameter = getattr(project.structure.cell, field)
    if field != 'length_a':
        with pytest.warns(UserWarning, match='set by symmetry'):
            parameter.free = True
        assert not parameter.free, 'The cubic metric keeps all five dependent cell flags fixed'
    elif mixed:
        parameter.free = True
        assert parameter.free, 'Powder positions determine the independent cubic length'
    else:
        require_refusal(parameter, DATA)


@pytest.mark.parametrize('kind', ['symmetry', 'constraint'])
def test_dependent_flags_warn_with_the_shared_reason(api, tmp_path, kind):
    project = api.Project.load(
        materialize(tmp_path / kind, cubic=kind == 'symmetry', constraint=kind == 'constraint')
    )
    site = project.structure.atom_sites['Ni']
    parameter = site.fract_x if kind == 'symmetry' else site.adp_iso
    reason = 'set by symmetry' if kind == 'symmetry' else 'set by a constraint'
    with pytest.warns(UserWarning, match=reason):
        parameter.free = True
    assert not parameter.free, 'A dependent remains fixed after a warned free assignment'


@pytest.mark.parametrize('field', ['length_a', 'occupancy', 'adp_iso'])
def test_an_unlinked_structure_uses_no_other_structures_experiment(api, tmp_path, field):
    project = api.Project.load(materialize(tmp_path / field, single=False, other=True))
    unused = project.structures['other']
    parameter = (
        unused.cell.length_a if field == 'length_a' else getattr(unused.atom_sites['Ni'], field)
    )
    require_refusal(parameter, DATA)
    active = project.structures['phase']
    control = (
        active.cell.length_a if field == 'length_a' else getattr(active.atom_sites['Ni'], field)
    )
    control.free = True
    assert control.free, 'The same quantity on the linked structure remains fittable'


def test_disabled_link_blocks_its_scale_and_structure(api, tmp_path):
    project = api.Project.load(materialize(tmp_path / 'disabled', single=False, enabled=False))
    require_refusal(project.experiments['bank'].linked_structures[0].scale, DATA)
    require_refusal(project.structure.cell.length_a, DATA)
    project.experiments['bank'].linked_structures[0].enabled = True
    project.structure.cell.length_a.free = True
    assert project.structure.cell.length_a.free, (
        'Re-enabling the link immediately restores the structure measurement context'
    )


def test_measured_fit_excludes_the_data_free_experiment(api, tmp_path):
    root = materialize(tmp_path / 'measured', single=False, data_free=True)
    with (root / 'experiments/powder.edi').open('a') as stream:
        stream.write(
            '_data_range.two_theta_min 20\n_data_range.two_theta_max 100\n'
            '_data_range.two_theta_step 0.2\n'
        )
    project = api.Project.load(root)
    require_refusal(project.experiments['powder'].peak.broad_gauss_w, DATA)
    project.experiments['bank'].peak.broad_gauss_w.free = True
    project.structure.cell.length_a.free = True
    assert project.experiments['bank'].peak.broad_gauss_w.free, (
        'A measured experiment supplies its own profile information'
    )
    assert project.structure.cell.length_a.free, (
        'A measured linked powder still supplies the shared structure positions'
    )


def test_dispersion_change_rechecks_a_retained_parameter_handle(api, tmp_path):
    root = materialize(tmp_path / 'xray', single=False, xray=True)
    project = api.Project.load(root)
    blocked = project.experiments['bank'].instrument.setup_wavelength
    require_refusal(blocked, CAPABILITY)
    # Python exposes the source through project files, without a source-selector setter.
    source = root / 'experiments/bank.edi'
    original = source.read_text()
    source.write_text(original.replace('xray_dispersion sasaki1989', 'xray_dispersion none'))
    admitted = api.Project.load(root)
    parameter = admitted.experiments['bank'].instrument.setup_wavelength
    parameter.free = True
    assert parameter.free, 'Loading dispersion none admits a retained wavelength handle'
    require_refusal(blocked, CAPABILITY)
    source.write_text(original)
    restored = api.Project.load(root)
    require_refusal(restored.experiments['bank'].instrument.setup_wavelength, CAPABILITY)
    assert parameter.free, 'Loading a different source preserves the earlier project handle'


@pytest.mark.parametrize('case', ['basic', 'powder', 'constrained'])
def test_real_projects_expose_the_same_blocker_text(api, case):
    if case == 'basic':
        root = ROOT / 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project'
        project = api.Project.load(root)
        require_refusal(project.structure.cell.length_a, DATA)
        with pytest.warns(UserWarning, match='set by symmetry'):
            project.structure.cell.length_b.free = True
    elif case == 'powder':
        root = ROOT / 'docs/user/cli/pd-neut-cwl_hs-hrpt/project'
        project = api.Project.load(root)
        require_refusal(project.experiments[0].peak.asym_beba_limit, 'a descriptor, never fitted')
    else:
        root = ROOT / 'docs/user/cli/sc-neut-tof_taurine_fit/project'
        project = api.Project.load(root)
        targets = [parameter for parameter in project.parameters if parameter.user_constrained]
        assert targets, 'The real taurine project carries declared dependent parameters'
        with warnings.catch_warnings(record=True) as notes:
            warnings.simplefilter('always')
            targets[0].free = True
        assert not targets[0].free, 'The real constrained parameter stays fixed'
        assert any('set by a constraint' in str(note.message) for note in notes), (
            'The real project uses the same declared-constraint reason'
        )
