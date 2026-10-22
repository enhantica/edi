"""Non-identity values from previously verified FullProf project pairs."""

import json
import math
import re
from pathlib import Path

import edi
import numpy as np
import pytest
from edi import verification

from tests.fixtures.example_catalogue.fullprof_inputs import Writer, read_cif, rows

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'


@pytest.mark.parametrize('form', ['start', 'fit', 'fixed', 'generated-start', 'generated-fit'])
def test_synchrotron_fullprof_inputs_state_the_independent_dispersion(tmp_path, form):
    reference = json.loads(
        (ROOT / 'tests/fixtures/example_catalogue/synchrotron-dispersion.json').read_text()
    )
    case = 'pd-xray-cwl_lam7o3-p021'
    if form.startswith('generated-'):
        path = tmp_path / 'probe.pcr'
        Writer(case, form == 'generated-start').write(path)
    else:
        kind = 'verification' if form == 'fixed' else 'fitting'
        path = ROOT / 'knowledge' / kind / 'fullprof' / case / f'{form}.pcr'
    text = path.read_text()
    nsc = re.search(r'^!\s*Job[^\n]+\n([^\n]+)', text, re.MULTILINE)
    assert nsc and int(nsc[1].split()[5]) == 9, (
        'The synchrotron FullProf input must declare all nine wavelength-specific scatterers'
    )
    assert reference['brackets']['La']['f_prime'] == [-0.4505, -0.5011], (
        'The frozen lanthanum brackets must be the independent Sasaki 0.20 and 0.21 A entries'
    )
    for element, bracket in reference['brackets'].items():
        low, high = bracket['wavelength_angstrom']
        fraction = (1 / 0.207109 - 1 / low) / (1 / high - 1 / low)
        expected = [
            values[0] + fraction * (values[1] - values[0])
            for values in [bracket['f_prime'], bracket['f_double_prime']]
        ]
        row = re.search(
            rf'^{element.lower()}\s+([-+\d.Ee]+)\s+([-+\d.Ee]+)\s+2\s*$', text, re.MULTILINE
        )
        assert row, 'FullProf must receive each explicit dispersion pair through its type-2 record'
        assert [float(value) for value in row.groups()] == pytest.approx(expected, abs=5e-6), (
            'The PCR must retain the independent Sasaki corrections within '
            'its five-decimal output precision'
        )


def loaded(case):
    return edi.Project.load(CLI / case / 'project')


def pcr(case):
    paths = list((ROOT / 'knowledge/verification/fullprof' / case).glob('*.pcr'))
    assert len(paths) == 1, 'The established convention witness must have one independent input'
    return paths[0].read_text()


def record(text, marker):
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if re.search(marker, line))
    row = next(line for line in lines[index + 1 :] if line.strip() and not line.startswith('!'))
    return [float(value) for value in row.split() if re.fullmatch(r'[-+0-9.Ee]+', value)]


def test_signed_zero_displacement_and_transparency_survive_the_cw_boundary():
    case = 'pd-neut-cwl_lab6-11b-echidna_tch-fcj'
    experiment = loaded(case).experiment
    values = record(pcr(case), r'^!\s*Zero')
    for field, expected, index in [
        ('calib_twotheta_offset', -0.21356, 0),
        ('calib_sample_displacement', 0.05395, 2),
        ('calib_sample_transparency', 0.09127, 4),
    ]:
        assert values[index] == pytest.approx(expected), 'FullProf pins the signed CW convention'
        assert getattr(experiment.instrument, field).value == pytest.approx(expected), (
            'CW correction values must retain the FullProf sign at nonzero inputs'
        )
    assert (
        loaded('pd-neut-cwl_lbco-hrpt').experiment.instrument.calib_twotheta_offset.value == 0.3
    ), 'The positive LBCO zero must remain the owner-selected unfitted start'


def test_tch_widths_and_fcj_lengths_retain_the_independent_units():
    case = 'pd-neut-cwl_lab6-11b-echidna_tch-fcj'
    peak = loaded(case).experiment.peak
    reference = record(pcr(case), r'^!\s+U\s+V')
    expected = [0.089876, -0.377516, 0.476188, 0, 0.052654]
    assert reference[:5] == pytest.approx(expected), 'FullProf supplies the TCH degree units'
    names = [
        'broad_gauss_u',
        'broad_gauss_v',
        'broad_gauss_w',
        'broad_lorentz_x',
        'broad_lorentz_y',
    ]
    assert [getattr(peak, name).value for name in names] == pytest.approx(expected), (
        'The TCH coefficients must cross the format boundary without conversion'
    )
    assert [peak.asym_fcj_1.value, peak.asym_fcj_2.value] == [0.08, 0.08], (
        'The two FCJ length ratios must retain their separate nonzero meanings'
    )


def test_beba_map_is_exercised_at_the_nonzero_fitted_witness():
    case = 'pd-neut-cwl_yap-spodi_3k'
    fullprof = record(pcr(case), r'^!\s*Pref1')
    assert fullprof[2:6] == pytest.approx([0.21542, 0.00305, -0.27811, 0.05563]), (
        'The BeBa map must be checked at the independent nonzero fitted values'
    )
    peak = loaded(case).experiment.peak
    actual = [
        getattr(peak, field).value
        for field in ['asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1']
    ]
    assert actual == pytest.approx([-0.22457, -0.00305, 0.11122, -0.05563]), (
        'BeBa coefficients must apply both the sign and the threefold term'
    )
    # This checks the parameter convention. Pattern agreement remains separately gated;
    # a mapped coefficient does not establish equivalence of the full profile families.


def test_xray_doublet_and_monochromator_polarization_are_nontrivial():
    case = 'pd-xray-cwl_pbso4-lab_round-robin'
    expected = record(pcr(case), r'^!\s*Lambda1')
    instrument = loaded(case).experiment.instrument
    assert expected[:3] == pytest.approx([1.54056, 1.5444, 0.5]), (
        'FullProf fixes the two wavelengths and their non-unit intensity ratio'
    )
    assert [
        instrument.setup_wavelength.value,
        instrument.setup_wavelength_2.value,
        instrument.setup_wavelength_2_to_1_ratio.value,
    ] == pytest.approx(expected[:3]), 'Both wavelengths and the ratio must survive project loading'
    assert instrument.setup_polarization_coefficient.value == 0.5, (
        'The monochromator convention requires the half polarization coefficient'
    )
    assert math.cos(
        math.radians(instrument.setup_monochromator_twotheta.value)
    ) ** 2 == pytest.approx(expected[5], abs=1e-5), (
        'The monochromator angle must map to FullProf Cthm near 0.8'
    )


def test_tof_sigma_is_variance_and_calibration_retains_its_quadratic_term():
    case = 'pd-neut-tof_si-sepd_jorgensen-von-dreele'
    text = pcr(case)
    sigma = record(text, r'^!\s*Sigma-2')
    gamma = record(text, r'^!\s*Gamma-2')
    calibration = record(text, r'^!\s*Zero')
    assert sigma[:3] == pytest.approx([0, 33.0419, 3.5544]), (
        'FullProf supplies Gaussian variance coefficients, not standard deviations'
    )
    assert gamma[1] == pytest.approx(2.543), 'Lorentzian width retains its linear coefficient'
    zero, linear, quadratic = calibration[:6:2]
    assert [zero, linear, quadratic] == pytest.approx([-9.18766, 7476.91016, -1.54]), (
        'The independent TOF witness includes nonzero offset and quadratic calibration'
    )
    d = 1.92015
    tof = zero + linear * d + quadratic * d * d
    width = math.sqrt(sigma[0] * d**4 + sigma[1] * d * d + sigma[2])
    assert tof == pytest.approx(14341.9, abs=0.1) and width == pytest.approx(11.20, abs=0.01), (
        'The independent Si 220 witness fixes both the calibration and variance convention'
    )


def test_occupancy_and_beta_tensors_keep_the_independent_crystallographic_units():
    project = loaded('pd-neut-cwl_y2o3_beta-adp')
    atoms = project.structures['y2o3'].atom_sites
    tensor = project.structures['y2o3'].atom_site_aniso['Y2']
    assert [
        getattr(tensor, f'adp_{suffix}').value for suffix in ['11', '22', '33', '12', '13', '23']
    ] == pytest.approx([0.00304] * 3 + [-0.00013] * 3), (
        'Beta tensors must retain their diagonal and signed off-diagonal FullProf values'
    )
    text = pcr('pd-neut-cwl_y2o3_beta-adp')
    for label, multiplicity in [('Y1', 24), ('Y2', 8)]:
        row = re.search(rf'^{label}\s+.+$', text, re.MULTILINE)[0].split()
        assert float(row[6]) == pytest.approx(
            atoms[label].occupancy.value * multiplicity / 48, abs=5e-6
        ), 'FullProf occupancy is site occupancy times site multiplicity over the general position'


def test_constraints_share_fullprof_code_indices_with_the_correct_sign():
    home = ROOT / 'knowledge/fitting/fullprof'
    text = (home / 'pd-neut-cwl_cosio-d20/fit.pcr').read_text()

    def atom_code(label, field):
        line = re.search(rf'^{label}\s+.+\n(.+)', text, re.MULTILINE)
        assert line, 'Every constrained atom must occur in the external fitting input'
        return float(line[1].split()[field])

    assert atom_code('Co1', 3) == atom_code('Co2', 3) != 0, (
        'Tied cobalt Biso values must use one active FullProf codeword'
    )
    text = (home / 'pd-neut-cwl_lmo-echidna/fit.pcr').read_text()
    li1, ni1, li2, ni2 = [atom_code(label, 4) for label in ['Li1', 'Ni1', 'Li2', 'Ni2']]
    assert li1 == ni2 == -ni1 == -li2 != 0, (
        'The complementary lithium/nickel occupancies must share one signed variable'
    )
    # The declared mixed start uses 3a/3b sites in a general position of multiplicity 36.
    occupancies = {'Li1': 0.95, 'Ni1': 0.05, 'Li2': 0.05, 'Ni2': 0.95}
    assert loaded('pd-neut-cwl_lmo-echidna').structures['lmo'].atom_sites[
        'Li1'
    ].occupancy.value == pytest.approx(0.95), (
        'The declared LMO start must retain five-percent lithium/nickel mixing'
    )
    for label, occupancy in occupancies.items():
        atom = re.search(rf'^{label}\s+.+$', text, re.MULTILINE)[0].split()
        assert float(atom[6]) == pytest.approx(occupancy * 3 / 36), (
            'FullProf must start with the same mixed occupancies in its multiplicity units'
        )
    assert re.search(r'^24\s+!Number of refined parameters', text, re.MULTILINE), (
        'The lithium model must retain the independently specified shared free count'
    )


@pytest.mark.parametrize(
    'case', ['pd-neut-tof_cecoal-polaris_chebyshev', 'pd-neut-tof_ceo2-pearl_polynomial']
)
def test_nonconstant_background_uses_the_declared_domain_and_origin(case):

    project = loaded(case)
    path = next((CLI / case / 'project/experiments').glob('*.edi'))
    scalars, loops = read_cif(path)
    coefficients = [
        float(row['_background.coef'].split('(')[0]) for row in rows(loops, '_background')
    ]
    project.calculate()
    experiment = project.experiment
    grid = np.asarray(experiment.data.time_of_flight)
    if 'chebyshev' in case:
        low, high = float(scalars['_background.x_min']), float(scalars['_background.x_max'])
        assert [low, high] == [3001.5891, 19004.6582], (
            'The Chebyshev domain is the independently declared FullProf range'
        )
        assert coefficients[:4] == pytest.approx([26833.258, 4390.511, 2629.871, -513.844]), (
            'The non-flat reference must exercise more than its constant coefficient'
        )
        expected = np.polynomial.chebyshev.chebval(
            2 * (grid - low) / (high - low) - 1, coefficients
        )
    else:
        origin = float(scalars['_background.origin'])
        assert origin == 7000, 'The polynomial origin must retain FullProf Bkpos in TOF units'
        assert coefficients[:4] == pytest.approx([2181.025, 221.415, 376.639, -1931.690]), (
            'The polynomial witness must retain its signed nonconstant coefficients'
        )
        expected = np.polynomial.polynomial.polyval((grid - origin) / origin, coefficients)
    actual = np.asarray(experiment.data.intensity_bkg)
    included = np.isfinite(actual)
    assert included.any(), 'The convention witness must exercise included observations'
    np.testing.assert_allclose(
        actual[included],
        expected[included],
        rtol=1e-10,
        atol=1e-7,
        err_msg='The calculated background must follow its closed-form convention',
    )


def test_line_background_interpolates_at_an_interior_point():

    project = loaded('pd-neut-cwl_lbco-hrpt')
    points = project.experiment.background
    points[0].intensity.value = 100
    points[1].intensity.value = 300
    verification.set_reference_as_measured(
        project.experiment, np.array([19.0, 20.0, 21.0]), np.ones(3)
    )
    project.calculate()
    assert project.experiment.data.intensity_bkg[1] == pytest.approx(200), (
        'A line-segment background must interpolate the midpoint of its bounding anchors'
    )
