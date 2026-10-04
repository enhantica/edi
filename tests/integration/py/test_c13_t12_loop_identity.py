""": every admitted loop has unique identities, including ignored ID columns.

Oracle: owner ruling 2026-09-28, not engine output. Inventory derived from
model.cpp/save_project.cpp and edi core/src/io.cpp: atom_site, scattering_length,
linked_structure, preferred_orientation, background, excluded_region, data,
sequential_fit_extract, joint_fit, fit_parameter; CIF atom_site_aniso also.
"""

import shlex
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
# location, identity key, companion keys, two independently valid row payloads.
ROWS = {
    'atom_site': (
        'structure',
        '_atom_site.id',
        (
            '_atom_site.type_symbol',
            '_atom_site.fract_x',
            '_atom_site.fract_y',
            '_atom_site.fract_z',
            '_atom_site.occupancy',
            '_atom_site.adp_iso',
            '_atom_site.adp_type',
            '_atom_site.wyckoff_letter',
        ),
        ('X Gd 0 0 0 0.7 0.8 Biso a', 'Y Gd 0 0 0 0.4 1.2 Biso a'),
    ),
    'scattering_length': (
        'structure',
        '_scattering_length.type_symbol',
        ('_scattering_length.length_fm',),
        ('Gd 6.1', 'O 5.8'),
    ),
    'linked_structure': (
        'experiment',
        '_linked_structure.structure_id',
        ('_linked_structure.scale',),
        ('structure 1',),
    ),
    'preferred_orientation': (
        'experiment',
        '_preferred_orientation.structure_id',
        (
            '_preferred_orientation.march_r',
            '_preferred_orientation.march_random_fract',
            '_preferred_orientation.index_h',
            '_preferred_orientation.index_k',
            '_preferred_orientation.index_l',
        ),
        ('structure 0.73 0.2 0 0 1',),
    ),
    'background': (
        'experiment',
        '_background.id',
        ('_background.position', '_background.intensity'),
        ('p17 0 1', 'p93 180 2'),
    ),
    'excluded_region': (
        'experiment',
        '_excluded_region.id',
        ('_excluded_region.start', '_excluded_region.end'),
        ('r17 41 42', 'r93 43 44'),
    ),
    'data': (
        'experiment',
        '_data.id',
        ('_data.two_theta', '_data.intensity_meas', '_data.intensity_meas_su'),
        ('d17 45 2 1', 'd93 46 3 1'),
    ),
    'sequential_fit_extract': (
        'analysis',
        '_sequential_fit_extract.id',
        (
            '_sequential_fit_extract.target',
            '_sequential_fit_extract.pattern',
            '_sequential_fit_extract.required',
        ),
        ("t17 temperature '(.*)' true", "t93 pressure '(.*)' false"),
    ),
    'joint_fit': (
        'analysis',
        '_joint_fit.experiment_id',
        ('_joint_fit.weight',),
        ('experiment 1', 'second 2'),
    ),
    'fit_parameter': (
        'analysis',
        '_fit_parameter.id',
        ('_fit_parameter.start_value', '_fit_parameter.start_uncertainty'),
        ('experiment.calib_twotheta_offset 0.17 .', 'experiment.setup_wavelength 1.53 .'),
    ),
}
CIF = {
    '_atom_site.id': '_atom_site_label',
    '_atom_site.type_symbol': '_atom_site_type_symbol',
    '_atom_site.fract_x': '_atom_site_fract_x',
    '_atom_site.fract_y': '_atom_site_fract_y',
    '_atom_site.fract_z': '_atom_site_fract_z',
    '_atom_site.occupancy': '_atom_site_occupancy',
    '_atom_site.adp_iso': '_atom_site_B_iso_or_equiv',
    '_atom_site.adp_type': '_atom_site_adp_type',
    '_atom_site.wyckoff_letter': '_atom_site_Wyckoff_symbol',
    '_linked_structure.structure_id': '_pd_phase_block.id',
    '_linked_structure.scale': '_pd_phase_block.scale',
    '_background.id': '_pd_background.id',
    '_background.position': '_pd_background.line_segment_X',
    '_background.intensity': '_pd_background.line_segment_intensity',
    '_excluded_region.id': '_easydiffraction_excluded_region.id',
    '_excluded_region.start': '_easydiffraction_excluded_region.start',
    '_excluded_region.end': '_easydiffraction_excluded_region.end',
    '_data.id': '_pd_data.point_id',
    '_data.two_theta': '_pd_meas.2theta_scan',
    '_data.intensity_meas': '_pd_meas.intensity_total',
    '_data.intensity_meas_su': '_pd_meas.intensity_total_su',
}
CIF_CATEGORIES = ('atom_site', 'linked_structure', 'background', 'excluded_region', 'data')


def _loop(category, *, duplicate=False, quoted=False, reverse=False):
    _, key, rest, originals = ROWS[category]
    tags = [key, *rest]
    rows = list(originals)
    identity = rows[0].split()[0]
    if duplicate:
        # Last row collides with the first, with an intervening distinct row where legal.
        repeat = rows[-1].split(maxsplit=1)[1]
        rows.append(f'{chr(39) + identity + chr(39) if quoted else identity} {repeat}')
    if reverse:
        tags.reverse()
        # shlex preserves a quoted multiword cell as one field for the extraction regex.

        rows = [' '.join(reversed(shlex.split(row))) for row in rows]
    return 'loop_\n' + '\n'.join(tags) + '\n' + '\n'.join(rows) + '\n', identity


def _base():
    text = (ROOT / 'tests/fixtures/c13_t4_march/model.edi').read_text()
    structure, experiment = text.split('data_experiment', 1)
    # Replace complete loop sections, not arbitrary values in a physical fixture.
    structure = structure.split('loop_', 1)[0]
    experiment = 'data_experiment' + experiment
    start = experiment.index('loop_')
    end = experiment.index('_instrument.setup_wavelength', start)
    experiment = experiment[:start] + experiment[end:]
    experiment += '\n_background.type line-segment\n'
    return structure, experiment


def _texts(category, *, duplicate=False, quoted=False, reverse=False):
    structure, experiment = _base()
    atom, _ = _loop('atom_site')
    linked, _ = _loop('linked_structure')
    data, _ = _loop('data')
    target, identity = _loop(category, duplicate=duplicate, quoted=quoted, reverse=reverse)
    structure += target if category == 'atom_site' else atom
    experiment += target if category == 'linked_structure' else linked
    experiment += target if category == 'data' else data
    if category != 'background':
        experiment += _loop('background')[0]
    location = ROWS[category][0]
    if location == 'structure' and category != 'atom_site':
        structure += target
    if location == 'experiment' and category not in {'linked_structure', 'data'}:
        experiment += target
    return structure, experiment, target if location == 'analysis' else '', identity


def _cif(text, location):
    mapping = dict(CIF)
    mapping.update({
        '_experiment_type.': '_easydiffraction_experiment_type.',
        '_peak.': '_easydiffraction_peak.',
        '_instrument.setup_wavelength': '_instr.wavelength',
        '_instrument.calib_twotheta_offset': '_instr.2theta_offset',
        '_background.type': '_easydiffraction_background.type',
    })
    if location == 'structure':
        mapping.update({f'_cell.length_{x}': f'_cell_length_{x}' for x in 'abc'})
        mapping.update({
            f'_cell.angle_{x}': f'_cell_angle_{x}' for x in ('alpha', 'beta', 'gamma')
        })
        mapping['_space_group.name_h_m'] = '_space_group_name_H-M_alt'
    for before, after in mapping.items():
        text = text.replace(before, after)
    return text


def _load(tmp_path, category, route, *, duplicate=False, quoted=False, reverse=False):
    structure, experiment, analysis, identity = _texts(
        category, duplicate=duplicate, quoted=quoted, reverse=reverse
    )
    location = ROWS[category][0]
    if route == 'project':
        (tmp_path / 'structures').mkdir(parents=True)
        (tmp_path / 'experiments').mkdir()
        (tmp_path / 'structures/structure.edi').write_text(structure)
        (tmp_path / 'experiments/experiment.edi').write_text(experiment)
        (tmp_path / 'experiments/second.edi').write_text(
            experiment.replace('data_experiment', 'data_second')
        )
        if analysis:
            (tmp_path / 'analysis').mkdir()
            (tmp_path / 'analysis/analysis.edi').write_text('_edi.schema_version 3\n' + analysis)
        return engine.Project.load(tmp_path), identity
    text = structure if location == 'structure' else experiment
    if route.startswith('cif'):
        text = _cif(text, location)
    factory = engine.StructureFactory if location == 'structure' else engine.ExperimentFactory
    if route.endswith('path'):
        path = tmp_path / 'input.cif'
        tmp_path.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return factory.from_cif_path(path), identity
    return factory.from_cif_str(text), identity


CASES = [
    (category, route)
    for category, (location, _, _, _) in ROWS.items()
    for route in (
        ['project']
        if location == 'analysis'
        else ['project', 'edi-text', 'edi-path']
        + (['cif-text', 'cif-path'] if category in CIF_CATEGORIES else [])
    )
]


def _named(action, identity):
    with pytest.raises((ValueError, RuntimeError)) as caught:
        action()
    message = str(caught.value)
    assert identity in message, ' duplicate refusal must name the colliding identity'
    assert any(
        word in message.lower() for word in ('duplicat', 'unique', 'collision', 'more than once')
    ), ' duplicate identities must refuse as an identity violation'


@pytest.mark.parametrize(('category', 'route'), CASES)
def test_unique_loop_ids_are_admitted(tmp_path, category, route):
    loaded, _ = _load(tmp_path, category, route, reverse=True)
    assert loaded is not None, ' valid unique loop IDs must remain admitted'
    if category == 'joint_fit':
        assert [bank.dataset_weight for bank in loaded.experiments] == [1, 2], (
            ' the unique joint-weight control must consume its analysis file'
        )
    if category == 'fit_parameter':
        instrument = loaded.experiments[0].instrument
        assert instrument.calib_twotheta_offset.start_value == pytest.approx(0.17), (
            ' the unique snapshot control must restore its declared start state'
        )


@pytest.mark.parametrize(('category', 'route'), CASES)
@pytest.mark.parametrize('quoted', [False, True], ids=['bare', 'quoted'])
def test_duplicate_loop_ids_refuse_at_load(tmp_path, category, route, quoted):
    identity = ROWS[category][3][0].split()[0]
    _named(lambda: _load(tmp_path, category, route, duplicate=True, quoted=quoted), identity)


@pytest.mark.parametrize('format_name', ['edi', 'cif'])
def test_attached_site_id_mutation_refuses_atomically(tmp_path, format_name):
    model, _ = _load(tmp_path, 'atom_site', format_name + '-text')
    first, second = list(model.atom_sites)
    original = second.id
    _named(lambda: setattr(second, 'id', first.id), first.id)
    assert second.id == original, ' a refused ID rename must leave the collection unchanged'
    second.id = 'renamed-unique'
    assert second.id == 'renamed-unique', ' a valid unique ID rename must succeed'


def test_attached_experiment_name_mutation_refuses_atomically(tmp_path):
    model, _ = _load(tmp_path, 'data', 'project')
    first, second = list(model.experiments)
    original = second.name
    _named(lambda: setattr(second, 'name', first.name), first.name)
    assert second.name == original, ' rejected bank rename must preserve identity'
    second.name = 'renamed-unique'
    assert second.name == 'renamed-unique', ' unique bank rename remains supported'


@pytest.mark.parametrize('route', ['text', 'path'])
@pytest.mark.parametrize('duplicate', [False, True], ids=['unique', 'duplicate'])
def test_cif_aniso_identity_table(tmp_path, route, duplicate):
    structure, _, _, _ = _texts('atom_site')
    text = _cif(structure, 'structure')
    text += (
        'loop_\n_atom_site_aniso_label\n_atom_site_aniso_U_11\n'
        '_atom_site_aniso_U_22\n_atom_site_aniso_U_33\n'
        'X 0.01 0.02 0.03\nY 0.02 0.03 0.04\n'
    )
    if duplicate:
        text += 'X 0.03 0.04 0.05\n'
    path = tmp_path / 'structure.cif'
    path.write_text(text)

    def load():
        if route == 'text':
            return engine.StructureFactory.from_cif_str(text)
        return engine.StructureFactory.from_cif_path(path)

    if duplicate:
        _named(load, 'X')
    else:
        model = load()
        assert [site.id for site in model.atom_sites] == ['X', 'Y'], (
            ' unique anisotropic site identities must retain both sites'
        )


def test_identity_names_are_local_to_their_loop_category(tmp_path):
    # Reuse one label across unrelated collections; uniqueness is not global.
    structure, experiment, _, _ = _texts('background')
    experiment = experiment.replace('p17', 'X').replace('d17', 'X')
    root = tmp_path / 'valid'
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'structures/structure.edi').write_text(structure)
    (root / 'experiments/experiment.edi').write_text(experiment)
    loaded = engine.Project.load(root)
    assert loaded is not None, ' distinct categories may reuse the same identity'


def test_attached_structure_name_mutation_refuses_atomically():
    project = engine.Project()
    first = engine.Structure()
    first.name = 'first'
    second = engine.Structure()
    second.name = 'second'
    project.structures.clear()
    project.structures.add(first)
    project.structures.add(second)
    _named(lambda: setattr(second, 'name', first.name), first.name)
    assert second.name == 'second', ' rejected structure rename must be atomic'
    second.name = 'third'
    assert second.name == 'third', ' unique structure rename remains supported'


def test_structure_factory_rejects_duplicate_site_ids():
    first = {'id': 'X', 'type_symbol': 'Gd', 'adp_type': 'Biso'}
    second = dict(first, id='Y')
    control = engine.StructureFactory.from_dict({'atom_sites': [first, second]})
    assert [site.id for site in control.atom_sites] == ['X', 'Y'], (
        ' factory construction must preserve distinct sites'
    )
    _named(lambda: engine.StructureFactory.from_dict({'atom_sites': [first, first]}), 'X')
