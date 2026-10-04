""": construct and populate a tutorial graph in diffraction-lib's spelling."""

from __future__ import annotations

import json
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / 'data/python-surface.json'
REFERENCE = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank'
STRUCTURE_CIF = REFERENCE / 'ncaf.cif'
STRUCTURE_EDI = REFERENCE / 'project/structures/ncaf.edi'
EXPERIMENT_EDI = REFERENCE / 'project/experiments/wish_1_10.edi'

# Frozen from diffraction-lib 0ffba46f's public CIF descriptors.  These values are an
# independent reference, not a pin of edi's current parser output.
EXPERIMENT_CIF = """data_reference_cwl
_easydiffraction_experiment_type.sample_form powder
_easydiffraction_experiment_type.beam_mode 'constant wavelength'
_easydiffraction_experiment_type.radiation_probe neutron
_easydiffraction_experiment_type.scattering_type bragg
_diffrn_radiation_wavelength.value 1.494
_pd_calib.2theta_offset 0.6225
_easydiffraction_peak.broad_gauss_u 0.0834
_easydiffraction_peak.broad_gauss_v -0.1168
_easydiffraction_peak.broad_gauss_w 0.123
"""

EXPECTED_COUNTERPARTS = {
    'StructureFactory': {'from_scratch'},
    'Structures': {'add_from_cif_path', 'add_from_cif_str', 'add_from_edi_path'},
    'Experiments': {
        'add_from_cif_path',
        'add_from_cif_str',
        'add_from_data_path',
        'add_from_edi_path',
    },
}


def _fresh_parameter(project: edi.Project, route: str) -> edi.Parameter:
    """Resolve a parameter anew so a detached value cannot satisfy the liveness gate."""
    if route == 'cell':
        return project.structures['si'].cell.length_a
    if route == 'atom-site':
        return project.structures['si'].atom_sites['Si'].fract_x
    if route == 'tof-peak':
        return project.experiments['tof'].peak.rise_alpha_0
    if route == 'cwl-instrument':
        return project.experiments['cwl'].instrument.setup_wavelength
    raise AssertionError(f' gate named an unknown parameter route: {route}')


def _parameter_project() -> edi.Project:
    project = edi.Project()
    project.structures.clear()
    project.experiments.clear()
    project.structures.create(name='si')
    project.structures['si'].atom_sites.create(id='Si', type_symbol='Si')
    project.experiments.add(edi.ExperimentFactory.from_scratch(name='tof'))
    project.experiments.add(
        edi.ExperimentFactory.from_scratch(
            name='cwl',
            beam_mode='constant wavelength',
            radiation_probe='neutron',
        )
    )
    return project


def test_c34_t1c_project_named_constructor_preserves_the_name() -> None:
    project = edi.Project(name='si_sepd')

    assert project.name == 'si_sepd', (
        ' requires Project(name=...) to preserve diffraction-lib 0ffba46f naming'
    )


def test_c34_t1c_project_copy_constructor_is_retired() -> None:
    with pytest.raises(TypeError):
        edi.Project(edi.Structure(), edi.BraggPdExperiment())
    with pytest.raises(TypeError):
        edi.Project(structure=edi.Structure(), experiment=edi.BraggPdExperiment())


@pytest.mark.parametrize('route', ['cell', 'atom-site', 'tof-peak', 'cwl-instrument'])
def test_c34_t1c_numeric_parameter_assignment_reaches_live_storage(route: str) -> None:
    project = _parameter_project()
    parameter = _fresh_parameter(project, route)
    replacement = {
        'cell': 5.431,
        'atom-site': 0.137,
        'tof-peak': 0.042,
        'cwl-instrument': 1.494,
    }[route]

    owner_route = {
        'cell': project.structures['si'].cell,
        'atom-site': project.structures['si'].atom_sites['Si'],
        'tof-peak': project.experiments['tof'].peak,
        'cwl-instrument': project.experiments['cwl'].instrument,
    }[route]
    member = {
        'cell': 'length_a',
        'atom-site': 'fract_x',
        'tof-peak': 'rise_alpha_0',
        'cwl-instrument': 'setup_wavelength',
    }[route]
    setattr(owner_route, member, replacement)

    reread = _fresh_parameter(project, route)
    assert reread is parameter, (
        f' {route} numeric assignment must retain the live Parameter slot, not replace it'
    )
    assert float(reread.value) == pytest.approx(replacement, abs=1.0e-12), (
        f' {route} numeric assignment must reach storage visible through a fresh accessor'
    )


def test_c34_t1c_keyword_population_and_existing_value_spelling_stay_live() -> None:
    project = edi.Project()
    project.structures.clear()
    project.structures.create(name='si')

    assert (
        project.structures['si'].atom_sites.create(
            id='Si',
            type_symbol='Si',
            fract_x=0.125,
            fract_y=0.25,
            fract_z=0.375,
            occupancy=0.875,
        )
        is None
    ), ' keyword population must retain the upstream create return convention'
    site = project.structures['si'].atom_sites['Si']
    assert [float(site.fract_x.value), float(site.fract_y.value), float(site.fract_z.value)] == [
        0.125,
        0.25,
        0.375,
    ], ' create(**numeric_parameters) must populate every coordinate in live storage'
    assert float(site.occupancy.value) == pytest.approx(0.875, abs=1.0e-12), (
        ' create(**numeric_parameters) must populate occupancy in live storage'
    )

    project.structures['si'].cell.length_a.value = 6.279
    assert float(project.structures['si'].cell.length_a.value) == pytest.approx(
        6.279, abs=1.0e-12
    ), ' must preserve the existing nested .value spelling through a fresh accessor'


@pytest.mark.parametrize('method_name', ['from_scratch', 'from_cif_str', 'from_cif_path'])
def test_c34_t1c_structure_factories_build_live_objects(
    method_name: str,
    tmp_path: Path,
) -> None:
    cif_path = tmp_path / 'structure.cif'
    cif_path.write_text(STRUCTURE_CIF.read_text(encoding='utf-8'), encoding='utf-8')
    arguments = {
        'from_scratch': {'name': 'si'},
        'from_cif_str': {'cif_str': cif_path.read_text(encoding='utf-8')},
        'from_cif_path': {'cif_path': cif_path},
    }[method_name]
    structure = getattr(edi.StructureFactory, method_name)(**arguments)

    project = edi.Project()
    project.structures.clear()
    assert project.structures.add(structure) is None, (
        f' StructureFactory.{method_name} result must be accepted by Structures.add'
    )
    structure.cell.length_a.value = 5.431
    assert float(project.structures[structure.name].cell.length_a.value) == pytest.approx(
        5.431, abs=1.0e-12
    ), f' StructureFactory.{method_name} result must remain live after insertion'


@pytest.mark.parametrize('method_name', ['from_scratch', 'from_cif_str', 'from_cif_path'])
def test_c34_t1c_experiment_factories_build_live_objects(
    method_name: str,
    tmp_path: Path,
) -> None:
    cif_path = tmp_path / 'experiment.cif'
    cif_path.write_text(EXPERIMENT_CIF, encoding='utf-8')
    arguments = {
        'from_scratch': {'name': 'tof'},
        'from_cif_str': {'cif_str': EXPERIMENT_CIF},
        'from_cif_path': {'cif_path': cif_path},
    }[method_name]
    experiment = getattr(edi.ExperimentFactory, method_name)(**arguments)

    project = edi.Project()
    project.experiments.clear()
    assert project.experiments.add(experiment) is None, (
        f' ExperimentFactory.{method_name} result must be accepted by Experiments.add'
    )
    experiment.linked_structure.scale.value = 0.625
    assert float(
        project.experiments[experiment.name].linked_structure.scale.value
    ) == pytest.approx(0.625, abs=1.0e-12), (
        f' ExperimentFactory.{method_name} result must remain live after insertion'
    )


@pytest.mark.parametrize(
    ('collection_name', 'method_name'),
    [
        pytest.param('structures', 'add_from_cif_str', id='structure-cif-str'),
        pytest.param('structures', 'add_from_cif_path', id='structure-cif-path'),
        pytest.param('structures', 'add_from_edi_path', id='structure-edi-path'),
        pytest.param('experiments', 'add_from_cif_str', id='experiment-cif-str'),
        pytest.param('experiments', 'add_from_cif_path', id='experiment-cif-path'),
        pytest.param('experiments', 'add_from_edi_path', id='experiment-edi-path'),
        pytest.param('experiments', 'add_from_data_path', id='experiment-data-path'),
    ],
)
def test_c34_t1c_add_from_loader_populates_a_live_collection(
    tmp_path: Path,
    collection_name: str,
    method_name: str,
) -> None:
    structure_cif_path = tmp_path / 'structure.cif'
    structure_cif_path.write_text(STRUCTURE_CIF.read_text(encoding='utf-8'), encoding='utf-8')
    structure_edi_path = tmp_path / 'structure.edi'
    structure_edi_path.write_text(STRUCTURE_EDI.read_text(encoding='utf-8'), encoding='utf-8')
    experiment_cif_path = tmp_path / 'experiment.cif'
    experiment_cif_path.write_text(EXPERIMENT_CIF, encoding='utf-8')
    experiment_edi_path = tmp_path / 'experiment.edi'
    experiment_edi_path.write_text(EXPERIMENT_EDI.read_text(encoding='utf-8'), encoding='utf-8')
    data_path = tmp_path / 'pattern.xye'
    data_path.write_text('1000 25 5\n1010 36 6\n1020 49 7\n', encoding='utf-8')
    sources = {
        ('structures', 'add_from_cif_str'): ((structure_cif_path.read_text(),), {}),
        ('structures', 'add_from_cif_path'): ((structure_cif_path,), {}),
        ('structures', 'add_from_edi_path'): ((structure_edi_path,), {}),
        ('experiments', 'add_from_cif_str'): ((EXPERIMENT_CIF,), {}),
        ('experiments', 'add_from_cif_path'): ((experiment_cif_path,), {}),
        ('experiments', 'add_from_edi_path'): ((experiment_edi_path,), {}),
        ('experiments', 'add_from_data_path'): (
            (),
            {'name': 'data', 'data_path': data_path},
        ),
    }
    args, kwargs = sources[collection_name, method_name]
    project = edi.Project()
    collection = getattr(project, collection_name)
    collection.clear()

    assert getattr(collection, method_name)(*args, **kwargs) is None, (
        f' {collection_name}.{method_name} must preserve the upstream return convention'
    )
    assert len(collection) == 1, (
        f' {collection_name}.{method_name} must add exactly one live object'
    )
    key = collection.names[0]
    item = collection[key]
    if collection_name == 'structures':
        item.cell.length_a.value = 5.431
        observed = collection[key].cell.length_a.value
    else:
        item.linked_structure.scale.value = 0.625
        observed = collection[key].linked_structure.scale.value
    assert float(observed) == pytest.approx(
        5.431 if collection_name == 'structures' else 0.625,
        abs=1.0e-12,
    ), f' {collection_name}.{method_name} result must stay live after insertion'


def test_c34_t1c_tutorial_graph_constructs_and_populates_end_to_end(tmp_path: Path) -> None:
    data_path = tmp_path / 'pattern.xye'
    data_path.write_text('1000 25 5\n1010 36 6\n1020 49 7\n', encoding='utf-8')
    project = edi.Project(name='si_sepd')
    project.structures.clear()
    project.experiments.clear()

    structure = edi.StructureFactory.from_scratch(name='si')
    project.structures.add(structure)
    project.experiments.add_from_data_path(name='sepd', data_path=data_path)
    project.structures['si'].cell.length_a = 5.431
    project.structures['si'].atom_sites.create(
        id='Si',
        type_symbol='Si',
        fract_x=0.125,
        fract_y=0.25,
        fract_z=0.375,
        occupancy=1.0,
    )

    assert project.name == 'si_sepd', ' tutorial graph must retain its project name'
    assert float(project.structures['si'].cell.length_a.value) == pytest.approx(
        5.431, abs=1.0e-12
    ), ' tutorial graph must expose the populated cell through a fresh accessor'
    assert project.structures['si'].atom_sites.names == ['Si'], (
        ' tutorial graph must expose its keyword-created site in live storage'
    )
    assert project.experiments.names == ['sepd'], (
        ' tutorial graph must expose its loaded experiment in live storage'
    )


def test_c34_t1c_new_surface_is_classified_by_upstream_counterpart() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))

    for owner, expected_members in EXPECTED_COUNTERPARTS.items():
        public_members = set(manifest['public'][owner]['members'])
        assert expected_members <= public_members, (
            f' requires every new {owner} loader in the published-surface manifest'
        )
        for member in expected_members:
            need = manifest['classification']['members'][owner][member]['need']
            assert need == {
                'by': 'counterpart',
                'ref': f'{owner}.{member}',
                'verdict': 'keep',
            }, (
                f' requires {owner}.{member} to resolve to diffraction-lib 0ffba46f, '
                'not an unreasoned local surface'
            )
