"""Authored CIF inputs; IUCr CIF 1.1, ITA symmetry and exact tensor invariants."""

import importlib
import json
import math
import os
import re
import shutil
import warnings
from decimal import Decimal
from pathlib import Path

import gemmi
import yaml

ROOT = Path(__file__).resolve().parents[2]
API = 'edi'
STRUCTURE = """data_witness
_cell_length_a 5.1000
_cell_length_b 6.2000
_cell_length_c 7.3000
_cell_angle_alpha 90.0000
_cell_angle_beta 90.0000
_cell_angle_gamma 90.0000
_space_group_name_H-M_alt 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_Wyckoff_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_B_iso_or_equiv
Ba1 Ba a 0.17000 0.23000 0.31000 0.58000 0.52000
O1 O a 0.27000 0.33000 0.41000 0.68000 0.62000
"""
EXPERIMENT = """data_witness
_easydiffraction_experiment_type.sample_form powder
_easydiffraction_experiment_type.beam_mode 'constant wavelength'
_easydiffraction_experiment_type.radiation_probe neutron
_easydiffraction_experiment_type.scattering_type bragg
_easydiffraction_peak.type cwl-gaussian
_diffrn_radiation_wavelength.value 1.5406
_pd_calib.2theta_offset 0.123
_pd_phase_block.id phase
_pd_phase_block.scale 2.3000
loop_
_pd_meas.2theta_scan
_pd_meas.intensity_total
_pd_meas.intensity_total_su
10 21 2
11 24 3
12 26 4
"""
COMPONENTS = ['11', '22', '33', '12', '13', '23']


def key(tag):
    return tag.lower().replace('.', '_', 1)


def columns(text):
    result = {}
    if not text.lstrip().lower().startswith('data_'):
        text = 'data_saved\n' + text
    for block in gemmi.cif.read_string(text):
        for item in block:
            if item.pair is not None:
                result[key(item.pair[0])] = list(item.pair[1:])
            elif item.loop is not None:
                for i, tag in enumerate(item.loop.tags):
                    result[key(tag)] = list(item.loop.values[i :: len(item.loop.tags)])
    return result


def decoded(token):
    return gemmi.cif.as_string(token)


def same(actual, token):
    try:
        value = Decimal(re.sub(r'\(\d+\)', '', token))
        return abs(Decimal(actual) - value) <= Decimal(5).scaleb(value.as_tuple().exponent - 1)
    except (ValueError, ArithmeticError):
        return decoded(actual) == decoded(token)


def notices(note, tag):
    return tag.lower().replace('.', '_') in note.lower().replace('.', '_')


def source_root():
    if API == 'crysta':
        return ROOT

    return Path(os.environ.get('CRYSTA_CONSUMER_SRC', ROOT / 'build/crysta-src'))


def inventory():
    document = yaml.safe_load((source_root() / 'data/dictionary/parameters.yaml').read_text())
    rows = []
    for row in document['parameters'] + document.get('items', []):
        names = row.get('cif_names', [row.get('cif_tag', ''), *row.get('aliases', [])])
        for variant in row.get('variants', {}).values():
            if isinstance(variant, dict):
                names += variant.get('cif_names', [])
        rows.append({
            **row,
            'cif_names': list(dict.fromkeys(filter(None, names))),
            'edi_names': row.get('edi_names', [row.get('cif_tag', '')]),
        })
    known = {key(n) for row in rows for n in row['edi_names']}
    census = json.loads((source_root() / 'data/category-census.json').read_text())
    for category in census['categories']:
        for column in category.get('columns', []):
            for item in column.get('items', []):
                canonical = category['name'] + '.' + item
                if key(canonical) not in known:
                    rows.append({
                        'uid': canonical,
                        'category': category['name'].lstrip('_'),
                        'dtype': 'string',
                        'cif_names': [canonical],
                        'edi_names': [canonical],
                    })
                    known.add(key(canonical))
    return rows


def token(row):
    if row.get('enum'):
        return gemmi.cif.quote(str(row['enum'][0]))
    if row.get('dtype') in {'float', 'number'}:
        return '0.271828' if row['category'] != 'cell' else '5.271828'
    if row.get('dtype') in {'int', 'integer'}:
        return '13'
    return 'external_witness'


def payload(kind, row, name, shape, value):
    block = gemmi.cif.read_string(STRUCTURE if kind == 'structure' else EXPERIMENT).sole_block()
    aliases = {key(n) for n in row['cif_names'] + row['edi_names']}
    for item in list(block):
        if item.pair is not None and key(item.pair[0]) in aliases:
            item.erase()
        elif item.loop is not None:
            for tag in list(item.loop.tags):
                if key(tag) in aliases:
                    block.find_loop(tag).erase()
    if shape == 'item':
        block.set_pair(name, value)
    else:
        loop = block.init_loop('', [name])
        loop.add_row([value])
        loop.add_row([value])
    return block.as_string()


def project_input(kind, text, directory, suffix='.cif'):
    source = directory / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    folder = source / ('structures' if kind == 'structure' else 'experiments')
    if kind == 'experiment':
        for path in folder.iterdir():
            path.unlink()
    (folder / ('witness' + suffix)).write_text(text)
    return source


def attach(api, kind, obj):
    if API == 'crysta' and kind == 'structure':
        return api.Project(obj,[])
    if API == 'crysta' and kind == 'experiment':
        phase = api.StructureFactory.from_cif_str(
            STRUCTURE.replace('data_witness', 'data_phase', 1)
        )
        project = api.Project(phase, obj)
        for link in obj.linked_structures:
            name = str(link.structure_id)
            if name not in project.structures:
                project.structures.add(
                    api.StructureFactory.from_cif_str(
                        STRUCTURE.replace('data_witness', 'data_' + name, 1)
                    )
                )
        return project
    project = api.Project()
    if API == 'edi':
        project.experiments.clear()
        project.structures.clear()
    if kind == 'structure':
        project.structures.add(obj)
    else:
        project.structures.add(
            api.StructureFactory.from_cif_str(STRUCTURE.replace('data_witness', 'data_phase', 1))
        )
        project.experiments.add(obj)
        for link in obj.linked_structures:
            name = str(link.structure_id)
            if name not in project.structures:
                project.structures.add(
                    api.StructureFactory.from_cif_str(
                        STRUCTURE.replace('data_witness', 'data_' + name, 1)
                    )
                )
    return project


def observe(kind, text, directory, route='factory-str', suffix='.cif'):
    api = importlib.import_module(API)
    directory.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        try:  # noqa: PLW0717 - one terminal import boundary
            if route == 'project':
                project = api.Project.load(project_input(kind, text, directory, suffix))
            elif route.startswith('collection'):
                project = api.Project()
                if API == 'edi':
                    project.experiments.clear()
                    project.structures.clear()
                if kind == 'experiment':
                    project.structures.add(
                        api.StructureFactory.from_cif_str(
                            STRUCTURE.replace('data_witness', 'data_phase', 1)
                        )
                    )
                collection = project.structures if kind == 'structure' else project.experiments
                if route == 'collection-str':
                    collection.add_from_cif_str(text)
                else:
                    path = directory / ('input' + suffix)
                    path.write_text(text)
                    getattr(
                        collection, 'add_from_' + ('edi' if suffix == '.edi' else 'cif') + '_path'
                    )(path)
            else:
                factory = api.StructureFactory if kind == 'structure' else api.ExperimentFactory
                if route == 'factory-str':
                    obj = factory.from_cif_str(text)
                else:
                    path = directory / ('input' + suffix)
                    path.write_text(text)
                    obj = factory.from_cif_path(path)
                project = attach(api, kind, obj)
        except (ValueError, RuntimeError) as error:
            return {'refused': str(error), 'notes': [str(w.message) for w in caught]}
        saved = directory / 'saved'
        project.save_as(saved)
    folder = saved / ('structures' if kind == 'structure' else 'experiments')
    target = folder / 'witness.edi'
    assert target.is_file(), (
        'Every successful import must reach the saved model of its requested block'
    )
    return {
        'cells': columns(target.read_text()),
        'notes': [str(w.message) for w in caught],
        'saved': saved,
        'text': target.read_text(),
    }


def accounted(result, name, value, canonical, block='witness', count=1):
    if 'refused' in result:
        assert result['refused'].strip(), (
            'A terminal refusal must explain why nothing can be imported'
        )
        assert notices(result['refused'], name) or notices(result['refused'], canonical), (
            'A refusal must identify the probed declaration rather than '
            'an unrelated host failure: '
        ) + name
        return
    reports = [
        n
        for n in result['notes']
        if notices(n, name) and re.search(r'not (?:read|used)|no place', n)
    ]
    if reports:
        assert all(block in n for n in reports), (
            'Each reported declaration identifies its source block'
        )
        assert len(reports) == 1, 'A supplied declaration receives one terminal report'
        return
    if value in {'?', '.'}:
        return
    found = result['cells'].get(key(canonical), [])
    assert len(found) == count, 'A supplied declaration must reach its complete saved column'
    assert all(same(v, value) for v in found), (
        'A copied or looked-up declaration must reach its complete saved column: ' + name
    )


def tensor(group='P 1', form='U', scalar=None, *, moved=False, sparse=False):
    hexagonal = group == 'P 3 1 2'
    cubic = group == 'P m -3 m'
    values = (
        [0.0200, 0.0200, 0.0200, 0.0100, 0, 0]
        if hexagonal
        else [
            0.0111 if cubic else 0.0240,
            0.0222 if cubic else 0.0240,
            0.0333 if cubic else 0.0240,
            0,
            0.0030 if moved and cubic else 0,
            0,
        ]
    )
    if cubic and moved:
        values = [0.0200, 0.0200, 0.0200, 0, 0.0030, 0]
    a, b, c, gamma = (5, 5, 7, 120) if hexagonal else (5, 5, 5, 90)
    xyz = '0.3000 0.6000 0.0000' if hexagonal else ('0.5000 0.0000 0.5000' if moved else '0 0 0')
    if not cubic and not hexagonal:
        xyz = '0.1700 0.2300 0.3100'
    # beta = 2 pi^2 N U N, with reciprocal lengths from this declared metric.
    reciprocal = [
        1 / (a * math.sin(math.radians(gamma))),
        1 / (b * math.sin(math.radians(gamma))),
        1 / c,
    ]
    pairs = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]
    numbers = [
        v
        * (
            8 * math.pi**2
            if form == 'B'
            else 2 * math.pi**2 * reciprocal[i] * reciprocal[j]
            if form == 'beta'
            else 1
        )
        for v, (i, j) in zip(values, pairs, strict=True)
    ]
    text = f"data_witness\n_space_group_name_H-M_alt '{group}'\n"
    for field, value in [
        ('length_a', a),
        ('length_b', b),
        ('length_c', c),
        ('angle_alpha', 90),
        ('angle_beta', 90),
        ('angle_gamma', gamma),
    ]:
        text += f'_cell_{field} {value:.4f}\n'
    text += (
        'loop_\n_atom_site_label\n_atom_site_type_symbol\n'
        '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n'
    )
    if scalar is not None:
        text += '_atom_site_U_iso_or_equiv\n'
    text += (
        'Ba1 Ba '
        + xyz
        + (' ' + scalar if scalar is not None else '')
        + '\nloop_\n_atom_site_aniso_label\n'
    )
    count = 3 if sparse else 6
    text += ''.join(
        '_atom_site_aniso.' + form + '_' + component + '\n' for component in COMPONENTS[:count]
    )
    return text + 'Ba1 ' + ' '.join(f'{v:.10f}' for v in numbers[:count]) + '\n'
