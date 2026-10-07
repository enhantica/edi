"""Declared ADP types, cctbx conversions and the independent FullProf profile."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from conftest import project_record_datetime, tree_bytes_with_normalized_project_metadata

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/anisotropic_adps'
ORACLE = json.loads((FIXTURE / 'numeric.json').read_text())
TYPES = ('Uiso', 'Biso', 'Uani', 'Bani', 'beta')
SUFFIXES = ('11', '22', '33', '12', '13', '23')


def structure_text(kind, reference, *, free=False):
    text = 'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "P 1"\n'
    names = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    text += ''.join(
        f'_cell.{name} {value:.17g}\n'
        for name, value in zip(names, reference['cell'], strict=True)
    )
    text += 'loop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.wyckoff_letter\n'
    if kind is not None:
        text += '_atom_site.adp_type\n'
    text += (
        '_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n'
        '_atom_site.occupancy\n_atom_site.adp_iso\n'
    )
    scalar = reference[kind] if kind in {'Uiso', 'Biso'} else 0.0
    text += f'X O a {kind + " " if kind else ""}0.137 0.219 0.317 1 {scalar:.17g}\n'
    if kind in {'Uani', 'Bani', 'beta'}:
        text += 'loop_\n_atom_site_aniso.id\n'
        text += ''.join(f'_atom_site_aniso.adp_{suffix}\n' for suffix in SUFFIXES)
        text += (
            'X '
            + ' '.join(
                f'{value:.17g}{"()" if free else ""}' for value in reference['values'][kind]
            )
            + '\n'
        )
    return text


def experiment_text(grid, scale=1.0):
    text = f"""data_experiment
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt
_peak.broad_gauss_u 0.036631
_peak.broad_gauss_v -0.068345
_peak.broad_gauss_w 0.131426
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 20
_instrument.setup_wavelength 1.54822
_instrument.calib_twotheta_offset -0.01625
loop_
_linked_structure.structure_id
_linked_structure.scale
structure {scale}
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    return text + ''.join(f'{x:.17g} 0 1\n' for x in grid)


def load_project(path, text, grid=None, scale=1.0):
    (path / 'structures').mkdir(parents=True)
    (path / 'experiments').mkdir()
    (path / 'structures/structure.edi').write_text(text)
    (path / 'experiments/experiment.edi').write_text(
        experiment_text(
            np.linspace(25, 100, 101) if grid is None else grid,
            scale,
        )
    )
    return engine.Project.load(path)


def loop_rows(text, category):
    tokens = shlex.split(text, comments=True)
    result = []
    cursor = 0
    while cursor < len(tokens):
        if tokens[cursor] != 'loop_':
            cursor += 1
            continue
        cursor += 1
        columns = []
        while cursor < len(tokens) and tokens[cursor].startswith('_'):
            columns.append(tokens[cursor])
            cursor += 1
        values = []
        while cursor < len(tokens) and not tokens[cursor].startswith(('_', 'data_', 'loop_')):
            values.append(tokens[cursor])
            cursor += 1
        if columns and columns[0].startswith(category + '.'):
            assert len(values) % len(columns) == 0, (
                'Saved ADP rows must have every declared column'
            )
            result += [
                dict(zip(columns, values[i : i + len(columns)], strict=True))
                for i in range(0, len(values), len(columns))
            ]
    return result


def saved(project, path):
    project.save_as(path)
    files = sorted((path / 'structures').glob('*.edi'))
    assert len(files) == 1, 'The ADP vehicle must save exactly its one structure'
    return files[0].read_text()


def tensor_from_saved(text):
    rows = loop_rows(text, '_atom_site_aniso')
    assert len(rows) == 1, 'Saving an anisotropic site must retain its six-component tensor row'
    return [float(rows[0][f'_atom_site_aniso.adp_{s}'].split('(')[0]) for s in SUFFIXES]


def pattern(project):
    project.analysis.calculate()
    values = np.asarray(project.experiments[0].data.intensity_calc).copy()
    assert np.isfinite(values).all(), 'The ADP pattern must be finite'
    assert np.max(values) > 0, 'The ADP test must calculate a nonempty pattern'
    return values


@pytest.mark.parametrize('cell', [0, 1], ids=['monoclinic', 'hexagonal'])
@pytest.mark.parametrize('kind', TYPES)
def test_each_declared_type_survives_load_and_two_saves(tmp_path, cell, kind):
    reference = ORACLE['cells'][cell]
    project = load_project(tmp_path / 'input', structure_text(kind, reference))
    site = project.structure.atom_sites[0]
    assert site.adp_type == kind, 'Loading must preserve each declared ADP type'
    first = pattern(project)
    previous = None
    previous_files = None
    previous_modified = None
    for generation in range(2):
        text = saved(project, tmp_path / f'saved-{generation}')
        rows = loop_rows(text, '_atom_site')
        assert rows[0]['_atom_site.adp_type'] == kind, 'Saving must write the current ADP type'
        if kind in {'Uani', 'Bani', 'beta'}:
            np.testing.assert_allclose(
                tensor_from_saved(text),
                reference['values'][kind],
                rtol=2e-7,
                atol=2e-9,
                err_msg='All six declared tensor components must survive serialization',
            )
        if generation:
            assert text == previous, (
                'Repeated ADP save/load must retain byte-identical structure text'
            )
        destination = tmp_path / f'saved-{generation}'
        modified = project_record_datetime(
            (destination / 'project.edi').read_bytes(), 'last_modified'
        )
        files = tree_bytes_with_normalized_project_metadata(destination, 'last_modified')
        if previous_files is not None:
            assert modified >= previous_modified, (
                'Project persistence retains a monotone modification date'
            )
            assert files == previous_files, (
                'Repeated saves must retain every project byte except the owned modification date'
            )
        previous_files = files
        previous_modified = modified
        previous = text
        project = engine.Project.load(tmp_path / f'saved-{generation}')
        assert project.structure.atom_sites[0].adp_type == kind, (
            'Reloading must preserve the serialized ADP type'
        )
        np.testing.assert_allclose(
            pattern(project),
            first,
            rtol=3e-7,
            atol=1e-7,
            err_msg='A complete ADP round trip must preserve the calculated pattern',
        )


def test_an_absent_type_gets_the_biso_default(tmp_path):
    project = load_project(tmp_path / 'input', structure_text(None, ORACLE['cells'][0]))
    assert project.structure.atom_sites[0].adp_type == 'Biso', (
        'An absent declared type must resolve to the Biso default'
    )
    assert (
        loop_rows(saved(project, tmp_path / 'saved'), '_atom_site')[0]['_atom_site.adp_type']
        == 'Biso'
    ), 'The resolved default must be the saved current ADP type'


@pytest.mark.parametrize('source', TYPES)
@pytest.mark.parametrize('target', TYPES)
def test_user_type_change_converts_with_cctbx_and_saves_current_type(tmp_path, source, target):
    reference = ORACLE['cells'][0]
    project = load_project(tmp_path / 'input', structure_text(source, reference))
    project.structure.atom_sites[0].adp_type = target
    text = saved(project, tmp_path / 'changed')
    row = loop_rows(text, '_atom_site')[0]
    assert row['_atom_site.adp_type'] == target, (
        'A user type change must become the saved current type'
    )
    if target in {'Uani', 'Bani', 'beta'}:
        expected = reference['isotropic' if source in {'Uiso', 'Biso'} else 'values'][target]
        np.testing.assert_allclose(
            tensor_from_saved(text),
            expected,
            rtol=2e-7,
            atol=2e-9,
            err_msg='Type changes must use the noncubic cctbx conversion',
        )
    else:
        assert project.structure.atom_sites[0].adp_iso.value == pytest.approx(
            reference[target], rel=2e-7
        ), 'Scalar conversion and tensor equivalent values must agree with cctbx'


@pytest.mark.parametrize('kind', ['Uani', 'Bani', 'beta'])
def test_anisotropic_site_exposes_the_computed_isotropic_value(tmp_path, kind):
    reference = ORACLE['cells'][0]
    project = load_project(tmp_path / 'input', structure_text(kind, reference))
    site = project.structure.atom_sites[0]
    pattern(project)
    expected = reference['Uiso' if kind == 'Uani' else 'Biso']
    assert site.adp_iso.value == pytest.approx(expected, rel=2e-7), (
        'The ADP group isotropic value must be computed from the tensor with its noncubic metric'
    )
    assert not site.adp_iso.free, (
        'A computed isotropic equivalent must not be an independent fit parameter'
    )


def test_fullprof_reference_retains_the_upstream_bytes():
    hashes = json.loads((FIXTURE / 'fullprof-sha256.json').read_text())
    for name, expected in hashes.items():
        assert (
            hashlib.sha256((FIXTURE / 'fullprof' / name).read_bytes()).hexdigest() == expected
        ), 'Every FullProf input and output must retain its independent upstream bytes'


@pytest.mark.parametrize('kind', ['Uani', 'Bani', 'beta'])
def test_y2o3_all_three_types_match_the_same_fullprof_profile(tmp_path, kind):
    raw = (FIXTURE / 'fullprof/y2o3.prf').read_text().split('BEGIN', 1)[1].split('END', 1)[0]
    profile = np.array([
        [float(x) for x in line.split()] for line in raw.splitlines() if line.strip()
    ])
    background = np.loadtxt(FIXTURE / 'fullprof/y2o3.bac', skiprows=1)
    x = profile[:, 0]
    reference = profile[:, 2] - np.interp(x, background[:, 0] - 0.01625, background[:, 1])
    included = (x >= 12) & (x <= 137.5)
    text = """data_structure
_edi.schema_version 3
_space_group.name_h_m "I a -3"
_cell.length_a 10.605744
_cell.length_b 10.605744
_cell.length_c 10.605744
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
"""
    for site, symbol, letter, xyz in [
        ('Y1', 'Y', 'd', '-.03236 0 .25'),
        ('Y2', 'Y', 'b', '.25 .25 .25'),
        ('O1', 'O', 'e', '.39072 .15204 .38030'),
    ]:
        text += f'{site} {symbol} {letter} {kind} {xyz} 1 0\n'
    text += 'loop_\n_atom_site_aniso.id\n' + ''.join(
        f'_atom_site_aniso.adp_{s}\n' for s in SUFFIXES
    )
    for site, tensors in ORACLE['y2o3'].items():
        text += site + ' ' + ' '.join(format(v, '.17g') for v in tensors[kind]) + '\n'
    project = load_project(tmp_path / 'input', text, x[included], 1.0602)
    actual = pattern(project)
    expected = reference[included]
    relative = np.max(np.abs(actual - expected)) / np.max(expected)
    assert relative < 0.0001, (
        'Every ADP declaration must meet the Y2O3 FullProf '
        'maximum profile difference bound of 0.01 percent'
    )
