"""Imported scene references address authored collections, including empty targets."""

import copy
import json

import edi
import pytest

from tests.unit.py.test_report_integer_domain import SEED, replace

# The regression seed supplies schema fields only. Counts and identities below are authored.
ROUTES = [
    ('scene.atoms.0.major', 'scene.atoms.0.parts'),
    ('scene.bonds.0.atom_1', 'scene.atoms'),
    ('scene.bonds.0.atom_2', 'scene.atoms'),
    ('scene.labels.0.atom', 'scene.atoms'),
    ('drawing.spheres.0.atom', 'scene.atoms'),
    ('drawing.shared.0', 'scene.atoms'),
    ('labels.0.atom', 'scene.atoms'),
]


def model():
    document = copy.deepcopy(SEED)
    structure = document['structures'][0]
    scene, drawing = structure['scene'], structure['drawing']
    atom = copy.deepcopy(scene['atoms'][0])
    atom['parts'] = atom['parts'][:1]
    atom['major'], atom['drawn'] = 0, True
    scene['atoms'] = [atom, copy.deepcopy(atom)]
    bond = copy.deepcopy(scene['bonds'][0])
    bond['atom_1'], bond['atom_2'] = 0, 1
    scene['bonds'] = [bond]
    scene['labels'] = [{'atom': 1, 'anchor': [0, 0, 0], 'text': 'authored last atom'}]
    sphere = copy.deepcopy(drawing['spheres'][0])
    sphere['atom'] = 1
    drawing['spheres'] = [sphere]
    drawing['shared'] = [1]
    structure['labels'] = copy.deepcopy(scene['labels'])
    return document


def collection(structure, path):
    for word in path.split('.'):
        structure = structure[int(word)] if word.isdigit() else structure[word]
    return structure


@pytest.mark.parametrize(('route', 'target'), ROUTES)
@pytest.mark.parametrize('boundary', ['one-past', 'empty'])
def test_parsed_scene_references_must_address_their_target_collection(route, target, boundary):
    document = model()
    structure = document['structures'][0]
    items = collection(structure, target)
    if boundary == 'empty':
        items.clear()
        index = 0
    else:
        index = len(items)
    replace(document, 'structures.0.' + route, index)
    with pytest.raises(ValueError, match=r'.+') as error:
        edi.ReportModel.from_json(json.dumps(document))
    assert str(error.value), (
        'An imported scene reference must refuse an empty target or exactly-one-past-end '
        'index before native or HTML rendering can dereference it'
    )


@pytest.mark.parametrize(('route', 'target'), ROUTES)
def test_last_valid_scene_identity_round_trips_without_truncation(route, target):
    document = model()
    replace(
        document, 'structures.0.' + route, len(collection(document['structures'][0], target)) - 1
    )
    restored = json.loads(edi.ReportModel.from_json(json.dumps(document)).to_json())
    assert restored == document, (
        'The collection check must preserve the final valid part, bond, sphere, shared-site '
        'and displayed-label identity without changing any serialized field'
    )


@pytest.mark.parametrize('field', ['bar_low', 'bar_high', 'rows'])
@pytest.mark.parametrize('length', [0, 1, 3])
def test_measured_point_arrays_have_exactly_one_entry_per_point(field, length):
    document = model()
    series = document['experiments'][0]['pattern']['series'][0]
    series['kind'] = 'measured'
    series['x'], series['y'] = [12.5, 13.75], [31.0, 42.0]
    series['bar_low'], series['bar_high'], series['rows'] = [1.0, 2.0], [3.0, 4.0], [0, 1]
    series[field] = [0] * length
    with pytest.raises(ValueError, match=r'.+') as error:
        edi.ReportModel.from_json(json.dumps(document))
    assert str(error.value), (
        'Measured point indices and both error-bar arrays must match the point collection '
        'before the native chart indexes them'
    )


def test_equal_point_arrays_and_nonaddressing_provenance_rows_remain_valid():
    document = model()
    structure = document['structures'][0]
    for atom in structure['scene']['atoms']:
        atom['row'] = 900
        atom['parts'][0]['row'] = 901
    structure['scene']['bonds'][0]['row'] = 902
    for instance in structure['drawing']['cylinders']:
        instance['atom'] = 903
    restored = json.loads(edi.ReportModel.from_json(json.dumps(document)).to_json())
    assert restored == document, (
        'Expanded-site and bond provenance rows and unused cylinder atom fields are not '
        'indices into the serialized scene atom collection'
    )


@pytest.mark.parametrize('instances', ['spheres', 'shared', 'both'])
@pytest.mark.parametrize('count', [0, 1, 2, 4])
def test_drawable_structures_supply_every_addressed_axis_view(instances, count):
    document = model()
    structure = document['structures'][0]
    structure['scene']['current'] = True
    if instances == 'spheres':
        structure['drawing']['shared'] = []
    elif instances == 'shared':
        structure['drawing']['spheres'] = []
    views = structure['along']
    structure['along'] = [copy.deepcopy(views[i % 3]) for i in range(count)]
    with pytest.raises(ValueError, match=r'.+') as error:
        edi.ReportModel.from_json(json.dumps(document))
    assert str(error.value), (
        'A current drawable structure must supply all three axis views '
        'before its a, b and c controls address them'
    )


@pytest.mark.parametrize('state', ['complete', 'not-current', 'no-instances', 'no-figures'])
def test_complete_views_and_genuinely_undrawable_models_remain_valid(state):
    document = model()
    structure = document['structures'][0]
    structure['scene']['current'] = state != 'not-current'
    if state != 'complete':
        structure['along'] = []
    if state in {'no-instances', 'no-figures'}:
        structure['drawing']['spheres'] = []
        structure['drawing']['shared'] = []
    if state == 'no-figures':
        structure['drawing']['cylinders'] = []
        document['sections'] = [section for section in document['sections'] if section != 'charts']
    restored = json.loads(edi.ReportModel.from_json(json.dumps(document)).to_json())
    assert restored == document, (
        'Complete axis views and genuinely undrawable figure-free models '
        'preserve every serialized field'
    )


SHAPES = [
    ('scene.cell_edges.0.start', 3),
    ('scene.cell_edges.0.end', 3),
    ('scene.axes.0.vector', 3),
    ('scene.cell_basis', 3),
    ('scene.cell_basis.1', 3),
    ('scene.atoms.0.centre', 3),
    ('scene.atoms.0.semi_axes', 3),
    ('scene.atoms.0.orientation', 4),
    ('scene.bonds.0.start', 3),
    ('scene.bonds.0.end', 3),
    ('scene.labels.0.anchor', 3),
    ('scene.frame.target', 3),
    ('scene.frame.view_direction', 3),
    ('scene.frame.view_up', 3),
    ('view.direction', 3),
    ('view.up', 3),
    ('along.0.direction', 3),
    ('along.1.up', 3),
    ('along.2.direction', 3),
    ('drawing.spheres.0.position', 3),
    ('drawing.spheres.0.scale', 3),
    ('drawing.spheres.0.rotation', 4),
    ('drawing.cylinders.0.position', 3),
    ('drawing.cylinders.0.scale', 3),
    ('drawing.cylinders.0.rotation', 4),
    ('drawing.triad.0.origin', 3),
    ('drawing.triad.1.direction', 3),
    ('drawing.triad.2.letter_anchor', 3),
    ('labels.0.anchor', 3),
]


@pytest.mark.parametrize(('path', 'size'), SHAPES)
@pytest.mark.parametrize('delta', [-100, -1, 1], ids=['empty', 'short', 'long'])
def test_every_addressed_fixed_collection_has_its_full_shape(path, size, delta):
    document = model()
    current = collection(document['structures'][0], path)
    count = max(0, size + delta)
    replacement = [copy.deepcopy(current[index % size]) for index in range(count)]
    replace(document, 'structures.0.' + path, replacement)
    with pytest.raises(ValueError, match=r'.+') as error:
        edi.ReportModel.from_json(json.dumps(document))
    assert str(error.value), (
        'Every indexed vector, quaternion, basis and view must reject an empty, short '
        'or oversized fixed collection before a renderer addresses its coordinates'
    )


@pytest.mark.parametrize('field', ['x', 'y'])
@pytest.mark.parametrize('length', [0, 1, 3])
def test_pattern_coordinate_arrays_pair_every_point(field, length):
    document = model()
    series = document['experiments'][0]['pattern']['series'][0]
    series['x'], series['y'] = [12.5, 13.75], [31.0, 42.0]
    series['rows'] = [0, 1]
    series['bar_low'], series['bar_high'] = [1.0, 2.0], [3.0, 4.0]
    series[field] = [0.0] * length
    with pytest.raises(ValueError, match=r'.+') as error:
        edi.ReportModel.from_json(json.dumps(document))
    assert str(error.value), 'A parsed point has both x and y before a chart indexes it'
