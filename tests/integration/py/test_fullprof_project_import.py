"""The ordinary project loader imports measured FullProf projects into the native model."""

from pathlib import Path
from shutil import copyfile

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / 'knowledge/verification/fullprof'
PBSO4 = REFERENCES / 'pd-neut-cwl_pbso4_basic'
SINGLE_CRYSTAL = ROOT / 'tests/fixtures/single_crystal/fullprof/sc-neut-cwl_pr2nio4_basic'


@pytest.mark.parametrize(
    ('case', 'control', 'expected_rows', 'expected_included'),
    [
        ('pd-neut-cwl_pbso4_basic', 'pbso4', 2910, 2908),
        ('pd-neut-tof_si-sepd', 'fixed', 5600, 5600),
        ('pd-xray-cwl_lif_single', 'lif_single_unpolarized', 6001, 5999),
    ],
)
def test_fullprof_powder_calculates_from_imported_values(
    case, control, expected_rows, expected_included
):
    source = REFERENCES / case
    reference_x, reference_y = np.loadtxt(
        source / f'{control}.prf', skiprows=3, max_rows=expected_rows, usecols=(0, 2), unpack=True
    )
    project = edi.Project.load(source / f'{control}.pcr')
    project.calculate()
    experiment = project.experiments[0]
    assert len(project.structures) == 1, (
        'The imported powder model retains its structure, links, measured grid and '
        'FullProf calculated profile.'
    )
    assert len(experiment.linked_structures) == 1, (
        'The imported powder model retains its structure, links, measured grid and '
        'FullProf calculated profile.'
    )
    pattern = experiment.data
    candidate = np.asarray(pattern.intensity_calc)
    included = np.isfinite(candidate)
    assert len(candidate) == expected_rows, (
        'The imported powder model retains its structure, links, measured grid and '
        'FullProf calculated profile.'
    )
    np.testing.assert_allclose(pattern.axis(), reference_x, atol=0.0005, rtol=0)
    assert int(included.sum()) == expected_included, (
        'The imported powder model retains its structure, links, measured grid and '
        'FullProf calculated profile.'
    )
    # The committed FullProf files report rounded Icalc. The curve uses the imported scale as read.
    relative_error = np.linalg.norm(candidate[included] - reference_y[included]) / np.linalg.norm(
        reference_y[included]
    )
    assert relative_error < 0.001, (
        'The imported powder model retains its structure, links, measured grid and '
        'FullProf calculated profile.'
    )


def test_fullprof_reflection_companion(tmp_path):
    project = edi.Project.load(SINGLE_CRYSTAL / 'prnio.pcr')
    project.calculate()
    rows = project.experiments[0].refln
    reference = {}
    for line in (SINGLE_CRYSTAL / 'prnio.prf').read_text().splitlines()[2:]:
        fields = line.split()
        if len(fields) >= 8:
            reference[tuple(map(int, fields[5:8]))] = float(fields[2])
    indices = zip(rows.index_h, rows.index_k, rows.index_l, strict=True)
    expected = [reference[key] for key in indices]
    assert len(expected) == len(reference) == 198, (
        'FullProf reflection imports preserve the independent companion intensities '
        'through native save.'
    )
    assert np.linalg.norm(rows.intensity_calc - expected) / np.linalg.norm(expected) < 0.001, (
        'FullProf reflection imports preserve the independent companion intensities '
        'through native save.'
    )

    saved = tmp_path / 'native'
    project.save_as(saved)
    reopened = edi.Project.load(saved)
    assert reopened.experiments[0].refln.intensity_meas == pytest.approx(rows.intensity_meas), (
        'FullProf reflection imports preserve the independent companion intensities '
        'through native save.'
    )


def test_fullprof_twin_layout_with_independent_reflections(tmp_path):
    source = tmp_path / 'prnio.pcr'
    control = (
        (SINGLE_CRYSTAL / source.name)
        .read_text()
        .replace('DAT-file: prnio,', 'DAT-file: observed.dat,')
    )
    source.write_text(control)
    companion = tmp_path / 'observed.int'
    rows = (SINGLE_CRYSTAL / 'prnio.int').read_text().splitlines()
    rows[2] = '0.8302 0 1'
    companion.write_text('\n'.join([*rows[:3], '! Reflection block', *rows[3:]]) + '\n')
    project = edi.Project.load(source)
    assert len(project.experiments[0].refln.intensity_meas) == 198, (
        'FullProf twin reflection inputs retain the source row inventory and '
        'uncertainty convention.'
    )

    rows[3] = '   2   0   0    175.6782      0.0000   1'
    companion.write_text('\n'.join(rows) + '\n')
    project = edi.Project.load(source)
    assert project.experiments[0].refln.intensity_meas_su[0] == 2, (
        'FullProf twin reflection inputs retain the source row inventory and '
        'uncertainty convention.'
    )

    rows[3] = '   2   0   0     -1.0000      0.0000   1'
    companion.write_text('\n'.join(rows) + '\n')
    with pytest.raises((ValueError, RuntimeError), match='require a twin observation model'):
        edi.Project.load(source)


def test_fullprof_refinement_codeword_keeps_the_signed_shift(tmp_path):
    source = tmp_path / 'pbso4.PCR'
    original = (PBSO4 / 'pbso4.pcr').read_text()
    with_codes = (
        original
        .replace('0    !Number of refined', '1    !Number of refined')
        .replace('210.0598          0.00', '210.0598         -12.0')
        .replace('-0.14357    0.0', '-0.14357   11.0')
    )
    assert with_codes != original, (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )
    source.write_text(with_codes)
    data = tmp_path / 'pbso4.dat'
    copyfile(PBSO4 / data.name, data)
    project = edi.Project.load(source)
    experiment = project.experiments[0]
    zero = experiment.instrument.calib_twotheta_offset
    point = experiment.background[0].intensity
    assert zero.free != point.free, (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )
    zero_start, point_start = zero.value, point.value
    if zero.free:
        zero.value += 0.01
    else:
        point.value += 0.02
    project.calculate()
    assert point.value - point_start == pytest.approx(-2 * (zero.value - zero_start)), (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )

    destination = tmp_path / 'saved'
    project.save_as(destination)
    assert source.read_text() == with_codes, (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )
    assert data.read_bytes() == (PBSO4 / data.name).read_bytes(), (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )
    assert len(edi.Project.load(destination).experiments) == 1, (
        'FullProf codewords retain their signed parameter relation without rewriting source files.'
    )


def test_fullprof_companion_error_names_the_file(tmp_path):
    source = tmp_path / 'pbso4.pcr'
    copyfile(PBSO4 / source.name, source)
    with pytest.raises((ValueError, RuntimeError), match=r'companion pbso4\.dat'):
        edi.Project.load(source)


def test_fullprof_rejects_an_active_alternative_weighting_objective(tmp_path):
    source = tmp_path / 'pbso4.pcr'
    lines = (PBSO4 / source.name).read_text().splitlines()
    job = next(i for i, line in enumerate(lines) if line.startswith('!Job '))
    fields = lines[job + 1].split()
    fields[8] = '1'
    lines[job + 1] = ' '.join(fields)
    for i, line in enumerate(lines):
        if '!Number of refined parameters' in line:
            lines[i] = '1 !Number of refined parameters'
            break
    source.write_text('\n'.join(lines) + '\n')
    with pytest.raises((ValueError, RuntimeError), match=r'refinement weighting \(Iwg\)'):
        edi.Project.load(source)


def test_fullprof_tof_reflection_dataset_scales(tmp_path):
    source = ROOT / 'tests/fixtures/single_crystal/example_fits/taurine_converged/taurine.pcr'
    project = edi.Project.load(source)
    assert len(project.experiments) == 6, (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )
    scales = [experiment.linked_structures[0].scale.value for experiment in project.experiments]
    assert scales == pytest.approx([2.783, 3.855, 3.230, 2.825, 2.744, 2.960]), (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )
    assert all(len(experiment.refln.wavelength) > 0 for experiment in project.experiments), (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )
    project.calculate()
    assert sum(len(exp.refln.intensity_calc) for exp in project.experiments) == 1540, (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )
    destination = tmp_path / 'native'
    project.save_as(destination)
    experiments = list((destination / 'experiments').glob('*.edi'))
    assert len(experiments) == 6, (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )
    assert all('_reflns.threshold_sigma' in path.read_text() for path in experiments), (
        'FullProf TOF reflection imports preserve every dataset scale, wavelength and threshold.'
    )


def test_fullprof_legacy_pr_occupancy_and_extinction():
    source = ROOT / 'tests/fixtures/single_crystal/example_fits/pr2nio4/input.pcr'
    project = edi.Project.load(source)
    experiment = project.experiments[0]
    assert project.structures[0].atom_sites[0].occupancy.value == pytest.approx(1.0), (
        'Legacy FullProf imports preserve the chemical occupancy, native scale and '
        'extinction convention.'
    )
    assert experiment.linked_structures[0].scale.value == pytest.approx(4.03072), (
        'Legacy FullProf imports preserve the chemical occupancy, native scale and '
        'extinction convention.'
    )
    assert experiment.extinction.type == 'larson-isotropic', (
        'Legacy FullProf imports preserve the chemical occupancy, native scale and '
        'extinction convention.'
    )
    assert experiment.extinction.coefficient.value == pytest.approx(0.0067456), (
        'Legacy FullProf imports preserve the chemical occupancy, native scale and '
        'extinction convention.'
    )


def test_fullprof_combines_nuclear_and_magnetic_overlays():
    fixture = ROOT / 'tests/fixtures/magnetic_pnma/cosio'
    project = edi.Project.load(fixture / 'cosio.pcr')
    assert len(project.structures) == 1, (
        'A nuclear and magnetic FullProf overlay becomes one linked structure with '
        'the reference profile.'
    )
    assert len(project.experiments[0].linked_structures) == 1, (
        'A nuclear and magnetic FullProf overlay becomes one linked structure with '
        'the reference profile.'
    )
    project.calculate()
    reference_x, reference_y = np.loadtxt(
        fixture / 'cosio.prf', skiprows=7, max_rows=1508, usecols=(0, 2), unpack=True
    )
    native = project.experiments[0].data
    calculated = np.interp(reference_x, native.axis(), native.intensity_calc)
    included = np.isfinite(calculated) & (reference_x >= 8.0953) & (reference_x <= 149.9953)
    assert included.sum() == 1418, (
        'A nuclear and magnetic FullProf overlay becomes one linked structure with '
        'the reference profile.'
    )
    assert (
        np.linalg.norm(calculated[included] - reference_y[included])
        / np.linalg.norm(reference_y[included])
        < 0.01
    ), (
        'A nuclear and magnetic FullProf overlay becomes one linked structure with '
        'the reference profile.'
    )


def test_fullprof_reads_forward_bin_widths_in_gsas_ralf(tmp_path):
    source = ROOT / 'knowledge/fitting/fullprof/pd-neut-tof_ceo2-pearl_polynomial'
    control = (source / 'Ceo2_PEARL.pcr').read_text()
    control = control.replace(' -3  10 ', ' -3  12 ', 1).replace(
        'DAT-file: full-fit.dat', 'DAT-file: raw.dat', 1
    )
    (tmp_path / 'pearl.pcr').write_text(control)
    copyfile(source / 'Ceo2_PEARL.ralf', tmp_path / 'raw.dat')

    pattern = edi.Project.load(tmp_path / 'pearl.pcr').experiments[0].data
    assert len(pattern.axis()) == 2523, (
        'The FullProf RALF importer preserves source bin centres, intensities and uncertainties.'
    )
    assert pattern.axis()[:2] == pytest.approx([1500.25, 1502.25]), (
        'The FullProf RALF importer preserves source bin centres, intensities and uncertainties.'
    )
    assert pattern.intensity_meas[:2] == pytest.approx([3471.65, 3373.25]), (
        'The FullProf RALF importer preserves source bin centres, intensities and uncertainties.'
    )
    assert pattern.intensity_meas_su[:2] == pytest.approx([85.2, 84.1]), (
        'The FullProf RALF importer preserves source bin centres, intensities and uncertainties.'
    )


def test_fullprof_moves_an_equivalent_site_to_its_wyckoff_representative():
    source = REFERENCES / 'pd-neut-cwl_lab6-11b-echidna_tch-fcj' / 'ECH0030684_LaB6_1p622A.pcr'
    project = edi.Project.load(source)
    boron = project.structures[0].atom_sites[1]
    assert boron.type_symbol == '11B', (
        'The imported isotope and equivalent position retain the source Wyckoff geometry.'
    )
    x = boron.fract_x.value
    assert [min(x, 1 - x), boron.fract_y.value, boron.fract_z.value] == pytest.approx([
        0.19978,
        0.5,
        0.5,
    ]), 'The imported isotope and equivalent position retain the source Wyckoff geometry.'


def test_fullprof_single_fcj_parameter_maps_to_two_physical_apertures(tmp_path):
    source = REFERENCES / 'pd-neut-cwl_lab6-echidna_fcj-asymmetry'
    stem = 'ECH0030684_LaB6_1p622A_fcj'
    control = (source / f'{stem}.pcr').read_text()
    lines = control.splitlines()
    index = next(i for i, line in enumerate(lines) if 'S_L' in line and 'D_L' in line)
    fields = lines[index + 1].split()
    fields[6:] = ['0.16', '0']
    lines[index + 1] = ' '.join(fields)
    (tmp_path / f'{stem}.pcr').write_text('\n'.join(lines) + '\n')
    copyfile(source / f'{stem}.dat', tmp_path / f'{stem}.dat')

    peak = edi.Project.load(tmp_path / f'{stem}.pcr').experiments[0].peak
    assert [peak.asym_fcj_1.value, peak.asym_fcj_2.value] == pytest.approx([0.08, 0.08]), (
        'One imported FullProf FCJ parameter maps to both physical apertures.'
    )


def test_fullprof_tof_size_direction_offsets_the_base_width(tmp_path):
    source = REFERENCES / 'pd-neut-tof_si-sepd'
    control = (
        (source / 'fixed.pcr')
        .read_text()
        .replace('0 !Number of refined parameters', '1 !Number of refined parameters')
    )
    lines = control.splitlines()
    index = next(i for i, line in enumerate(lines) if 'Sigma-2' in line and 'Iso-GSize' in line)
    values = lines[index + 1].split()
    values[0], values[5] = '10', '1.5'
    lines[index + 1] = ' '.join(values)
    lines[index + 2] = '0 0 0 0 0 11 0'
    (tmp_path / 'fixed.pcr').write_text('\n'.join(lines) + '\n')
    copyfile(source / 'fixed.dat', tmp_path / 'fixed.dat')

    project = edi.Project.load(tmp_path / 'fixed.pcr')
    peak = project.experiments[0].peak
    width, size = peak.broad_gauss_sigma_2, peak.broad_gauss_size
    assert [width.value, size.value] == pytest.approx([8.5, 1.5]), (
        'The FullProf TOF size direction preserves the coupled base-width relation.'
    )
    assert width.free != size.free, (
        'The FullProf TOF size direction preserves the coupled base-width relation.'
    )
    driver = width if width.free else size
    driver.value += 0.25
    project.calculate()
    assert width.value + size.value == pytest.approx(10), (
        'The FullProf TOF size direction preserves the coupled base-width relation.'
    )


def test_fullprof_imports_tof_absorption_and_float32_range():
    source = REFERENCES / 'pd-neut-tof_cecoal-polaris' / 'fixed.pcr'
    pattern = edi.Project.load(source).experiments[0]
    assert pattern.absorption.abscor1.value == pytest.approx(0.01729), (
        'FullProf TOF imports retain the source absorption and printed grid boundary.'
    )
    assert pattern.data.axis()[0] == pytest.approx(3001.589), (
        'FullProf TOF imports retain the source absorption and printed grid boundary.'
    )


def test_fullprof_imports_phase_profile_and_isis_ralf_observations():
    source = REFERENCES / 'pd-neut-tof_ncaf-wish_jorgensen-von-dreele'
    project = edi.Project.load(source / 'tmpl_one_bank.pcr')
    project.calculate()
    data = project.experiments[0].data
    x = np.asarray(data.axis())
    sample = np.searchsorted(x, 9106.08)
    assert x[sample] == pytest.approx(9106.08801), (
        'FullProf ISIS RALF import preserves the source phase profile and observed bin values.'
    )
    assert data.intensity_meas[sample] == pytest.approx(370.31, abs=0.011), (
        'FullProf ISIS RALF import preserves the source phase profile and observed bin values.'
    )
    assert data.intensity_calc[sample] == pytest.approx(543.11, rel=0.004), (
        'FullProf ISIS RALF import preserves the source phase profile and observed bin values.'
    )
