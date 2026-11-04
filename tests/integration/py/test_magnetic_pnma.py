"""Native magnetic categories and Pnma physics against independent inputs."""

import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path

import edi as api
import numpy as np
import pytest

from conftest import crysta_reference_prefix
from tests.fixtures.magnetic_pnma import reference as ref

PREFIXES = (
    '_space_group_magn.',
    '_space_group_magn_transforms.',
    '_space_group_symop_magn_',
    '_parent_space_group.',
    '_parent_propagation_vector.',
    '_magnetic_form_factor.',
    '_atom_site_moment.',
)


def load(tmp_path, text=None, *, show=True):
    return api.Project.load(ref.project(tmp_path / 'input', text, show=show))


def test_reference_files_have_committed_hashes():
    manifest = json.loads((ref.ROOT / 'cosio/manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((ref.ROOT / 'cosio' / name).read_bytes()).hexdigest() == digest, (
            'The independent FullProf inputs and outputs retain their authored bytes'
        )
    assert len(ref.expansion()) == 8, 'Pnma expands the two cobalt sites to eight magnetic atoms'
    assert ref.form_factor(0) == pytest.approx(0.9986, abs=1e-15), (
        'The Brown Co2+ coefficients retain their published zero-angle normalization'
    )


@pytest.mark.parametrize('show', [True, False])
def test_native_categories_survive_two_saves(tmp_path, show):
    model = load(tmp_path, show=show)
    expected = ref.columns((ref.ROOT / 'magnetic.edi').read_text())
    for index in range(2):
        saved = tmp_path / f'saved-{index}'
        model.save_as(saved)
        actual = ref.columns((saved / 'structures/cosio.edi').read_text())
        for tag, values in expected.items():
            if tag.startswith(PREFIXES):
                assert tag in actual, 'Every declared magnetic tag survives the native reader'
                assert len(actual[tag]) == len(values), (
                    'Every declared magnetic category retains its rows through load and save'
                )
                for observed, expected_value in zip(actual[tag], values, strict=True):
                    try:
                        equal = Decimal(observed) == Decimal(expected_value)
                    except ArithmeticError:
                        equal = observed == expected_value
                    assert equal, 'Every declared magnetic value survives load and save'
        settings = ref.columns((saved / 'project.edi').read_text())
        assert settings.get('_structure_view.show_moments') == [str(show).lower()], (
            'The project retains both moment-visibility settings'
        )
        model = api.Project.load(saved)

    fixture = (
        Path(__file__).resolve().parents[2] / 'fixtures/magnetic_form_factors/form-factor-ions.edi'
    )
    for mode in ('j0', 'dipole', 'beyond_dipole'):
        text = (
            fixture
            .read_text()
            .replace(
                '_magnetic_form_factor.j2_coefficient\n',
                '_magnetic_form_factor.j2_coefficient\n'
                '_magnetic_form_factor.approximation\n'
                '_magnetic_form_factor.j4_coefficient\n'
                '_magnetic_form_factor.j6_coefficient\n',
            )
            .replace('Ho Ho3+ 0.25', f'Ho Ho3+ 0.25 {mode} -0.4 1.1')
            .replace('Er Er3+ 0.1', f'Er Er3+ 0.1 {mode} 0.2 -0.3')
        )
        forms = load(tmp_path / mode, text, show=show)
        for index in range(2):
            destination = tmp_path / mode / f'roundtrip-{index}'
            forms.save_as(destination)
            actual = ref.columns((destination / 'structures/cosio.edi').read_text())
            for name in (
                'type_symbol',
                'ion',
                'approximation',
                'j2_coefficient',
                'j4_coefficient',
                'j6_coefficient',
            ):
                tag = '_magnetic_form_factor.' + name
                assert actual.get(tag) == ref.columns(text)[tag], (
                    'All modes retain both ion rows and signed coefficients on both saves'
                )
            forms = api.Project.load(destination)


def test_moment_symmetry_has_exactly_four_independent_components(tmp_path):
    model = load(tmp_path)
    moments = model.structure.atom_site_moment
    assert moments['Co1_1'].symmform == 'Mx,My,Mz', (
        'Inversion fixes an axial vector and leaves all 4a moment components free'
    )
    assert moments['Co2_1'].symmform == '0,My,0', (
        'The 4c mirror reverses axial Mx and Mz, leaving only My free'
    )


def test_load_repairs_forbidden_values_and_free_flags(tmp_path, capfd):
    text = (
        (ref.ROOT / 'magnetic.edi')
        .read_text()
        .replace('Co2_1 0 2.97 0 0,My,0', 'Co2_1 1.2() 2.97() -0.8() Mx,My,Mz')
    )
    model = load(tmp_path, text)
    fixed = model.structure.atom_site_moment['Co2_1']
    assert fixed.crystalaxis_x.value == fixed.crystalaxis_z.value == 0, (
        'A loaded moment obeys the site stabiliser even when the file declares forbidden values'
    )
    assert not any([fixed.crystalaxis_x.free, fixed.crystalaxis_z.free]), (
        'Symmetry-fixed components cannot enter the fit through saved free flags'
    )
    assert fixed.crystalaxis_y.free, 'The allowed My flag remains free after symmetry repair'
    diagnostics = capfd.readouterr().err
    assert all(word in diagnostics for word in ['symmform', 'Co2_1']), (
        'A contradictory symmform and repaired values produce a site-specific warning'
    )
    model.save_as(tmp_path / 'saved')
    saved = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    assert Decimal(saved['_atom_site_moment.crystalaxis_x'][1]) == 0, (
        'Saving a repaired moment removes the forbidden free flag'
    )


def test_every_expanded_moment_matches_the_published_axial_operations(tmp_path):
    model = load(tmp_path)
    sites = model.structure.expanded_atom_sites
    moments = model.structure.expanded_atom_site_moment
    actual = {}
    for i, expanded_id in enumerate(moments.id):
        row = int(expanded_id) - 1
        key = (
            sites.atom_site_id[row],
            *(round(float(getattr(sites, 'fract_' + a)[row]) % 1, 9) for a in 'xyz'),
        )
        actual[key] = [getattr(moments, 'crystalaxis_' + a)[i] for a in 'xyz']
    expected = ref.expansion()
    assert actual.keys() == expected.keys(), (
        'Every and only magnetic image appears once in the cell'
    )
    for key, value in expected.items():
        assert np.allclose(actual[key], value, rtol=0, atol=1e-12), (
            'Expanded moments use the axial det(R) R transformation for each published operation'
        )


@pytest.mark.parametrize('c2', [-0.2, 0, 0.2])
def test_pnma_magnetic_squared_factors_match_independent_sum(tmp_path, c2):
    text = (ref.ROOT / 'magnetic.edi').read_text().replace('Co Co2+ 0\n', f'Co Co2+ {c2}\n')
    model = load(tmp_path, text)
    model.analysis.calculate()
    reflections = model.experiment.refln
    values = {
        (int(h), int(k), int(index_l)): float(m)
        for h, k, index_l, m in zip(
            reflections.index_h,
            reflections.index_k,
            reflections.index_l,
            reflections.f_m_perp_squared_calc,
            strict=True,
        )
    }
    for hkl in [(1, 0, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1)]:
        assert hkl in values, 'Magnetic and mixed Pnma reflections survive nuclear extinctions'
        assert values[hkl] == pytest.approx(
            ref.magnetic_squared(hkl, c2) / 100, rel=1e-11, abs=1e-12
        ), (
            'The magnetic squared factor agrees with Brown coefficients '
            'and the perpendicular axial sum'
        )


def test_zero_moments_preserve_the_nuclear_pattern_bitwise(tmp_path):
    text = (
        (ref.ROOT / 'magnetic.edi')
        .read_text()
        .replace('0.7 2.6 0.3', '0 0 0')
        .replace('0 2.97 0', '0 0 0')
    )
    magnetic = api.Project.load(ref.project(tmp_path / 'magnetic', text))
    nuclear = api.Project.load(
        ref.project(tmp_path / 'nuclear', (ref.ROOT / 'nuclear.edi').read_text())
    )
    magnetic.analysis.calculate()
    nuclear.analysis.calculate()
    assert np.array_equal(
        magnetic.experiment.data.intensity_calc,
        nuclear.experiment.data.intensity_calc,
        equal_nan=True,
    ), 'Zero moments preserve every calculated nuclear profile value bit for bit'


def test_fullprof_fixed_profile_and_magnetic_peaks(tmp_path):
    model = load(tmp_path)
    model.analysis.calculate()
    lines = (ref.ROOT / 'cosio/cosio.prf').read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(' 2Theta')) + 1
    profile = np.array([
        [float(x) for x in line.split()[:5]] for line in lines[start : start + 1508]
    ])
    x = np.asarray(model.experiment.data.two_theta)
    assert np.allclose(x, profile[:, 0], rtol=0, atol=5e-5), (
        'FullProf and the product calculate on the same observed angle grid'
    )
    selected = (x >= 7.996) & (x <= 150.05) & ~((x >= 64.65) & (x <= 64.74))
    calculated = np.asarray(model.experiment.data.intensity_calc)
    expected = profile[:, 2]
    assert (
        np.linalg.norm((calculated - expected)[selected]) / np.linalg.norm(expected[selected])
        < 0.01
    ), 'The fixed calculated profile meets the predeclared FullProf relative L2 bound'
    for position, width in ref.magnetic_peak_windows():
        window = selected & (np.abs(x - position) <= 3 * width)
        signal = calculated - np.asarray(model.experiment.data.intensity_bkg)
        reference_signal = expected - profile[:, 4]
        assert (
            np.linalg.norm((signal - reference_signal)[window])
            / np.linalg.norm(reference_signal[window])
            < 0.01
        ), 'Magnetic-only peaks meet the FullProf bound after background subtraction'


@pytest.mark.parametrize('pair', [False, True])
@pytest.mark.parametrize('moment', [(0, 2.3, 0), (1.7, 0, 0), (0.7, 1.3, -0.4)])
def test_ferromagnet_and_opposite_pair_closed_forms(tmp_path, pair, moment):
    text = """data_cosio
_edi.schema_version 3
_cell.length_a 8
_cell.length_b 9
_cell.length_c 10
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
_space_group_magn.name_BNS P1
_space_group_magn.number_BNS 1.1
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
_magnetic_form_factor.j2_coefficient
Co Co2+ 0
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
A Co a 0 0 0 0.63 0.17 Biso
"""
    if pair:
        text += 'B Co a .5 .5 .5 0.63 0.17 Biso\n'
    text += """loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
"""
    text += 'A ' + ' '.join(map(str, moment)) + '\n'
    if pair:
        text += 'B ' + ' '.join(str(-x) for x in moment) + '\n'
    model = load(tmp_path, text)
    model.analysis.calculate()
    reflections = model.experiment.refln
    for hkl in [(1, 0, 0), (2, 0, 0), (1, 1, 0)]:
        index = np.flatnonzero(
            (np.asarray(reflections.index_h) == hkl[0])
            & (np.asarray(reflections.index_k) == hkl[1])
            & (np.asarray(reflections.index_l) == hkl[2])
        )
        assert index.size == 1, (
            'The primitive cell retains each requested nuclear or magnetic reflection'
        )
        direction = np.array(hkl) / [8, 9, 10]
        s = np.linalg.norm(direction) / 2
        direction /= np.linalg.norm(direction)
        perpendicular = np.array(moment) - np.dot(moment, direction) * direction
        interference = (1 - (-1) ** sum(hkl)) ** 2 if pair else 1
        expected = (
            interference
            * np.dot(perpendicular, perpendicular)
            * (2.695 * 0.63 * ref.form_factor(s) * np.exp(-0.17 * s * s)) ** 2
            / 100
        )
        assert reflections.f_m_perp_squared_calc[int(index[0])] == pytest.approx(
            expected, rel=1e-11, abs=1e-12
        ), (
            'Single and opposite moments follow the closed form with occupancy, '
            'B and perpendicular projection'
        )


def test_magnetic_categories_are_declared_in_the_product_schema():
    census = json.loads((ref.ROOT.parents[2] / 'data/category-census.json').read_text())
    categories = {row['name']: row for row in census['categories']}
    for name in [
        'space_group_magn',
        'space_group_magn_transforms',
        'space_group_symop_magn_operation',
        'space_group_symop_magn_centering',
        'atom_site_moment',
        'parent_space_group',
        'parent_propagation_vector',
        'magnetic_form_factor',
    ]:
        assert '_' + name in categories, (
            'The product schema declares every native magnetic input category'
        )


@pytest.mark.parametrize('first_writer', ['crysta', 'edi'])
def test_each_product_reads_the_other_products_saved_moments(tmp_path, first_writer):
    cli = crysta_reference_prefix() / 'bin/crysta'
    original = ref.project(tmp_path / 'original')
    if first_writer == 'edi':
        api.Project.load(original).save_as(tmp_path / 'edi-saved')
        exchange = tmp_path / 'edi-saved'
    else:
        exchange = original
    result = subprocess.run(
        [str(cli), str(exchange), 'calc'], capture_output=True, text=True, check=False, timeout=25
    )
    assert result.returncode == 0, (
        'The paired SDK calculates and saves the native magnetic project'
    )
    api.Project.load(exchange).save_as(tmp_path / 'final')
    actual = ref.columns((tmp_path / 'final/structures/cosio.edi').read_text())
    expected = ref.columns((ref.ROOT / 'magnetic.edi').read_text())
    for tag in [
        '_atom_site_moment.label',
        '_atom_site_moment.crystalaxis_x',
        '_atom_site_moment.crystalaxis_y',
        '_atom_site_moment.crystalaxis_z',
    ]:
        assert tag in actual, 'Cross-product saves retain the magnetic companion table'
        if tag.endswith('label'):
            assert actual[tag] == expected[tag], 'Cross-product moment rows retain their atom keys'
        else:
            assert [Decimal(x) for x in actual[tag]] == [Decimal(x) for x in expected[tag]], (
                'Cross-product saves preserve every magnetic component exactly'
            )


def test_fullprof_reflection_positions_and_orbit_multiplicities(tmp_path):
    model = load(tmp_path)
    model.analysis.calculate()
    reflections = model.experiment.refln
    actual = {
        tuple(abs(int(v)) for v in hkl): float(d)
        for *hkl, d in zip(
            reflections.index_h,
            reflections.index_k,
            reflections.index_l,
            reflections.d_spacing,
            strict=True,
        )
    }
    checked = set()
    for line in (ref.ROOT / 'cosio/cosio.hkl').read_text().splitlines():
        fields = line.split()
        if len(fields) != 9 or fields[0] in {'!', 'h', 'Pattern#'}:
            continue
        hkl = tuple(int(value) for value in fields[:3])
        multiplicity = int(fields[3])
        position, spacing = float(fields[5]), float(fields[6])
        if not 10 < position < 148 or Decimal(fields[8]).is_zero():
            continue
        orbit = {tuple(rotation * hkl) for rotation in ref.ROTATIONS}
        assert multiplicity == len(orbit), (
            'FullProf multiplicities agree with the independently published point-group orbit'
        )
        key = tuple(abs(value) for value in hkl)
        assert key in actual, 'Every nuclear and magnetic FullProf orbit survives enumeration'
        assert abs(actual[key] - spacing) <= 0.0000005, (
            'Every reflection spacing agrees within half the FullProf printed final digit'
        )
        checked.add(key)
    assert {(1, 0, 0), (0, 0, 1), (1, 0, 1)} <= checked, (
        'The reflection comparison reaches magnetic-only and mixed reflections'
    )
