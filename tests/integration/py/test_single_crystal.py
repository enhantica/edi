"""Single-crystal behavior against frozen external values and weighted least squares."""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/single_crystal'
REFERENCE = json.loads((FIXTURE / 'fullprof.json').read_text())['cases']
CASES = tuple(REFERENCE)
NO_EXTINCTION = tuple(case for case in CASES if 'extinction' not in case)
SAMPLES = json.loads((FIXTURE / 'extinction.json').read_text())


def engine():
    return importlib.import_module('edi')


def imported(path, *, tof=False):
    return engine().ExperimentFactory.from_data_path(
        name='experiment',
        data_path=str(path),
        sample_form='single crystal',
        radiation_probe='neutron',
        scattering_type='bragg',
        beam_mode='time-of-flight' if tof else 'constant wavelength',
    )


def columns(experiment, *, tof=False):
    data = experiment.refln
    names = ['index_h', 'index_k', 'index_l', 'intensity_meas', 'intensity_meas_su']
    if tof:
        names.append('wavelength')
    return [list(row) for row in zip(*(getattr(data, name) for name in names), strict=True)]


def project(tmp_path, case):
    source = tmp_path / case
    shutil.copytree(FIXTURE / 'projects' / case, source)
    return engine().Project.load(source)


def calculated(project):
    project.analysis.calculate()
    result = np.asarray(project.experiments[0].refln.intensity_calc)
    assert result.size, 'Single-crystal calculation must return every reflection'
    assert np.isfinite(result).all(), (
        'Single-crystal calculation must publish a finite value for every input reflection'
    )
    return result.copy()


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('extension', ['int', 'dat'])
def test_each_reference_reader_preserves_every_input_row(case, extension):
    record = REFERENCE[case]
    path = FIXTURE / 'fullprof' / case / f'{record["stem"]}.{extension}'
    experiment = imported(path, tof='tof' in case)
    assert columns(experiment, tof='tof' in case) == record['input_rows'], (
        'Reflection import must preserve signed indices, row order, duplicates, F², s.u. '
        'and every TOF wavelength exactly, including weak and negative measurements'
    )


@pytest.mark.parametrize('extension', ['int', 'dat'])
@pytest.mark.parametrize(
    'bad',
    ['2.5 1 3 9 1', '2 1 3 nan 1', '2 1 3 9 0', '2 1 3 9 -1', '2 1 3 9', '2 1 3 9 1 garbage'],
    ids=[
        'fractional-index',
        'nonfinite-intensity',
        'zero-su',
        'negative-su',
        'missing-su',
        'trailing-word',
    ],
)
def test_reader_refusal_names_the_physical_line(tmp_path, extension, bad):
    prefix = 'Sample\n(3i4,2f12.4)\n1.234 0 0\n' if extension == 'int' else '# Sample\n\n'
    path = tmp_path / f'bad.{extension}'
    good = f'{1:4d}{2:4d}{3:4d}{18.5:12.4f}{0.7:12.4f}\n'
    path.write_text(prefix + good + bad + '\n')
    line = len(prefix.splitlines()) + 2
    with pytest.raises((ValueError, RuntimeError), match=rf'(?i)line\s*[:#]?\s*{line}\b'):
        imported(path)


@pytest.mark.parametrize('value', ['0', '-1.7', 'nan', 'inf'])
def test_tof_refuses_unusable_wavelength_at_its_line(tmp_path, value):
    path = tmp_path / 'bad.dat'
    path.write_text(f'# TOF\n1 2 3 18.5 0.7 1.25\n2 3 4 20 1 {value}\n')
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)line\s*[:#]?\s*3\b'):
        imported(path, tof=True)


@pytest.mark.parametrize('case', NO_EXTINCTION)
def test_fullprof_per_reflection_forward_values(tmp_path, case):
    model = project(tmp_path, case)
    rows = REFERENCE[case]['calculated_rows']
    hkl = [row[:3] for row in columns(model.experiments[0], tof='tof' in case)]
    assert hkl == [row['hkl'] for row in rows], (
        'FullProf parity must compare each signed reflection in input order, with no '
        'dropping or merging'
    )
    np.testing.assert_allclose(
        calculated(model),
        [row['f2_calc'] for row in rows],
        rtol=1e-4,
        atol=5.1e-5,
        err_msg='Each calculated F² must match FullProf within 0.01 percent plus output rounding',
    )


@pytest.mark.parametrize('case', CASES)
def test_project_round_trip_retains_reflections_and_model(tmp_path, case):
    model = project(tmp_path, case)
    if case == 'sc-neut-cwl_tbti_basic':
        omitted = tmp_path / 'omitted-extinction'
        shutil.copytree(FIXTURE / 'projects' / case, omitted)
        path = omitted / 'experiments/experiment.edi'
        text = (
            '\n'.join(
                line
                for line in path.read_text().splitlines()
                if not line.startswith('_extinction.')
            )
            + '\n'
        )
        path.write_text(text)
        default = engine().Project.load(omitted)
        extinction = default.experiments[0].extinction
        assert (
            extinction.model,
            float(extinction.radius.value),
            float(extinction.mosaicity.value),
        ) == ('gauss', 1.0, 1.0), (
            'Omitted single-crystal extinction must use the diffraction-lib defaults'
        )
        path.write_text(
            text + '_extinction.type becker-coppens\n_extinction.model gauss\n'
            '_extinction.radius 1\n_extinction.mosaicity 1\n'
        )
        explicit = engine().Project.load(omitted)
        np.testing.assert_allclose(
            calculated(default),
            calculated(explicit),
            rtol=0,
            atol=0,
            err_msg='An omitted extinction category must calculate like its explicit defaults',
        )
    before = columns(model.experiments[0], tof='tof' in case)
    first_calc = calculated(model)
    previous = None
    for generation in range(2):
        destination = tmp_path / f'saved-{generation}'
        model.save_as(destination)
        scientific = {
            str(p.relative_to(destination)): p.read_bytes()
            for folder in ('structures', 'experiments')
            for p in sorted((destination / folder).glob('*.edi'))
        }
        if previous is not None:
            assert scientific == previous, (
                'Repeated saves must retain every structure and experiment byte, '
                'including extinction and TOF data'
            )
        previous = scientific
        model = engine().Project.load(destination)
        assert columns(model.experiments[0], tof='tof' in case) == before, (
            'A saved single-crystal project must reload all measured reflection fields exactly'
        )
        np.testing.assert_allclose(
            calculated(model),
            first_calc,
            rtol=1e-12,
            atol=1e-12,
            err_msg='Single-crystal save/load must preserve the forward model',
        )


def atom_project(tmp_path, row, model, scale):
    root = tmp_path / f'atom-{model}-{scale}'
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    text = 'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "P 1"\n'
    for name, value in zip(('a', 'b', 'c'), row['cell'], strict=True):
        text += f'_cell.length_{name} {value}\n'
    text += '_cell.angle_alpha 90\n_cell.angle_beta 90\n_cell.angle_gamma 90\n'
    text += (
        'loop_\n_atom_site.id\n_atom_site.type_symbol\n'
        '_atom_site.wyckoff_letter\n_atom_site.fract_x\n'
        '_atom_site.fract_y\n_atom_site.fract_z\n_atom_site.occupancy\n'
        '_atom_site.adp_type\n_atom_site.adp_iso\nNi Ni a .13 .27 .39 .73 Biso .41\n'
    )
    (root / 'structures/structure.edi').write_text(text)
    text = (
        'data_experiment\n_edi.schema_version 3\n_experiment_type.sample_form "single crystal"\n'
        '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_scattering_source.neutron_scattering_length sears1992\n'
    )
    text += f'_instrument.setup_wavelength {row["wavelength"]}\n'
    text += f'_extinction.type becker-coppens\n_extinction.model {model}\n'
    text += f'_extinction.radius {row["radius"]}\n_extinction.mosaicity {row["mosaicity"]}\n'
    text += f'loop_\n_linked_structure.structure_id\n_linked_structure.scale\nstructure {scale}\n'
    text += (
        'loop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n'
        '_refln.intensity_meas\n_refln.intensity_meas_su\n'
    )
    text += ' '.join(str(v) for v in row['hkl']) + ' 1 0.3\n'
    (root / 'experiments/experiment.edi').write_text(text)
    return engine().Project.load(root)


@pytest.mark.parametrize('model', ['gauss', 'lorentz'])
@pytest.mark.parametrize('sample', range(len(SAMPLES)))
def test_extinction_matches_decimal_closed_form_before_scale(tmp_path, model, sample):
    row = SAMPLES[sample]
    for scale in (0.37, 2.7):
        result = calculated(atom_project(tmp_path, row, model, scale))
        expected = scale * float(row['f2']) * float(row[model])
        assert result.tolist() == pytest.approx([expected], rel=2e-11, abs=1e-12), (
            'Becker-Coppens must apply the spherical primary and selected secondary correction '
            'to unscaled F² with micrometre radius and the stored mosaicity convention, on both '
            'angular branches'
        )


def test_negative_measurements_and_duplicate_hkl_are_independent_rows(tmp_path):
    path = tmp_path / 'signed.dat'
    path.write_text('# signed observations\n-2 1 3 -4.5 0.7\n-2 1 3 9.2 1.3\n0 0 2 0 0.2\n')
    assert columns(imported(path)) == [
        [-2, 1, 3, -4.5, 0.7],
        [-2, 1, 3, 9.2, 1.3],
        [0, 0, 2, 0.0, 0.2],
    ], (
        'Measured F² may be negative or zero and repeated hkl measurements must retain '
        'their own weights'
    )


def test_powder_forward_regression_pin_is_unchanged(tmp_path):
    source = tmp_path / 'powder'
    shutil.copytree(FIXTURE / 'powder', source)
    reference = json.loads((FIXTURE / 'powder-regression.json').read_text())
    assert reference['kind'] == 'regression-pin', (
        'The pre-feature powder calculation must remain labelled as a regression pin'
    )
    model = engine().Project.load(source)
    model.analysis.calculate()
    np.testing.assert_allclose(
        model.experiments[0].data.intensity_calc,
        reference['intensity_calc'],
        rtol=1e-12,
        atol=1e-9,
        err_msg='Adding single-crystal support must preserve the pre-feature powder calculation',
    )
