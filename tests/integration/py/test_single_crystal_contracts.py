"Single-crystal contracts from closed forms and saved-input invariants."

import math
import warnings

import numpy as np

from tests.integration.py.test_single_crystal import atom_project, calculated, engine

CELL = (5.1, 6.2, 7.3)
HKLS = ((2, 1, 3), (4, 1, 3), (-2, 1, 3), (2, -1, 3))


def bare(hkl, biso=0.41):
    s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
    return (1.03 * 0.73) ** 2 * math.exp(-2 * biso * s2)


def model(tmp_path, *, tof=False, biso=0.41, extinction='none', fields='', rows=None):
    sample = {
        'hkl': HKLS[0],
        'cell': CELL,
        'wavelength': 1.6,
        'radius': 0,
        'crystal_radius': 0,
        'mosaic_spread': 0,
    }
    atom_project(tmp_path, sample, 'gaussian', 2.3)
    # Build inputs through the file boundary so optional categories are selected normally.
    root = tmp_path / 'atom-gaussian-2.3'
    structure = root / 'structures/structure.edi'
    structure.write_text(structure.read_text().replace('Biso .41', f'Biso {biso}'))
    experiment = root / 'experiments/experiment.edi'
    text = experiment.read_text()
    text = (
        '\n'.join(line for line in text.splitlines() if not line.startswith('_extinction.')) + '\n'
    )
    text = text[: text.index('loop_\n_refln.index_h')]
    if tof:
        text = text.replace('constant wavelength', 'time-of-flight')
        text = text.replace('_instrument.setup_wavelength 1.6\n', '')
    text += f'_extinction.type {extinction}\n' + fields + '\n'
    text += (
        'loop_\n'
        '_refln.index_h\n'
        '_refln.index_k\n'
        '_refln.index_l\n'
        '_refln.intensity_meas\n'
        '_refln.intensity_meas_su\n'
    )
    if tof:
        text += '_refln.wavelength\n'
    rows = rows or [
        (*hkl, 1.8, 0.3, *([1.3 + 0.2 * i] if tof else [])) for i, hkl in enumerate(HKLS)
    ]
    text += ''.join(' '.join(map(str, row)) + '\n' for row in rows)
    experiment.write_text(text)
    return engine().Project.load(root)


def sphere(hkl, wavelength, crystal_mm, radius_um, g_inv_rad, kind, distribution):
    # Becker & Coppens sphere interpolation, independently evaluated in the fixture generator.
    s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
    c = 1 - 2 * wavelength * wavelength * s2
    sin2 = math.sqrt(1 - c * c)
    f2, volume = bare(hkl), math.prod(CELL)
    x = 1.5 * f2 * (wavelength * radius_um / volume) ** 2
    primary = (
        1 + 2 * x + (0.2 + 0.45 * c) * x * x / (1 + (0.22 - 0.12 * (0.5 - c) ** 2) * x)
    ) ** -0.5
    g = g_inv_rad * 1e-4
    if kind == 'becker-coppens-type-1':
        primary = 1
        block = g / (math.sqrt(1.125) * sin2) if distribution == 'gaussian' else g / sin2
    elif kind == 'becker-coppens-type-2':
        block = radius_um / wavelength
    else:
        block = (
            radius_um
            * g
            / (
                math.sqrt((g * wavelength) ** 2 + 1.125 * radius_um**2 * sin2**2)
                if distribution == 'gaussian'
                else g * wavelength + radius_um * sin2
            )
        )
    xs = 1.5 * f2 * wavelength**3 / volume**2 * (crystal_mm * 1000) * block
    if distribution == 'gaussian':
        a, b, k = 0.58 + 0.48 * c + 0.24 * c * c, 0.02 - 0.025 * c, 2.12
    else:
        a, b, k = 0.025 + 0.285 * c, 0.15 - 0.2 * (0.75 - c) ** 2 if c > 0 else -0.45 * c, 2
    return primary * (1 + k * xs + a * xs * xs / (1 + b * xs)) ** -0.5


def test_becker_coppens_types_separate_path_domain_and_plain_g(tmp_path):
    for distribution in ('gaussian', 'lorentzian'):
        for kind in ('becker-coppens-type-1', 'becker-coppens-type-2', 'becker-coppens-mixed'):
            for crystal in (0.037, 1.7):
                root = tmp_path / f'{distribution}-{kind}-{crystal}'
                fields = f'_extinction.crystal_radius {crystal}\n'
                fields += '_extinction.domain_radius 28.4\n_extinction.mosaic_spread 93100\n'
                fields += f'_extinction.mosaic_distribution {distribution}\n'
                if kind.endswith('type-1'):
                    fields = '\n'.join(
                        ell for ell in fields.splitlines() if 'domain_radius' not in ell
                    )
                if kind.endswith('type-2'):
                    fields = '\n'.join(
                        ell
                        for ell in fields.splitlines()
                        if not any(x in ell for x in ('mosaic_spread', 'mosaic_distribution'))
                    )
                p = model(root, extinction=kind, fields=fields)
                expected = [
                    2.3
                    * bare(h)
                    * sphere(
                        h,
                        1.6,
                        crystal,
                        28.4,
                        93100,
                        kind,
                        'gaussian' if kind.endswith('type-2') else distribution,
                    )
                    for h in HKLS
                ]
                np.testing.assert_allclose(
                    calculated(p),
                    expected,
                    rtol=2e-12,
                    atol=1e-13,
                    err_msg=(
                        'All BC types must separate mm crystal path, um domains and plain '
                        'inverse-radian g'
                    ),
                )


def test_larson_isotropic_and_anisotropic_match_manual_before_scale(tmp_path):
    # ILL Mag2Pol manual section 3.3: neutron p=.001; cross terms occur once.
    coefficients = (0.8, 0.3, 1.4, 0.17, 0.11, 0.23)
    for tof in (False, True):
        for kind in ('larson-isotropic', 'larson-anisotropic'):
            root = tmp_path / f'{tof}-{kind}'
            fields = '_extinction.coefficient 1700\n'
            if kind.endswith('anisotropic'):
                fields = ''.join(
                    f'_extinction.coefficient_{key} {value}\n'
                    for key, value in zip(
                        ('11', '22', '33', '12', '13', '23'), coefficients, strict=True
                    )
                )
            p = model(root, tof=tof, extinction=kind, fields=fields)
            expected = []
            for i, (h, k, ell) in enumerate(HKLS):
                lam = 1.3 + 0.2 * i if tof else 1.6
                s2 = sum((v / a) ** 2 for v, a in zip((h, k, ell), CELL, strict=True)) / 4
                sin2 = 2 * lam * math.sqrt(s2) * math.sqrt(1 - lam * lam * s2)
                x = (
                    1700
                    if kind.endswith('isotropic') and not kind.endswith('anisotropic')
                    else (
                        0.8 * h * h
                        + 0.3 * k * k
                        + 1.4 * ell * ell
                        + 0.17 * h * k
                        + 0.11 * h * ell
                        + 0.23 * k * ell
                    )
                    / (4 * s2)
                )
                expected.append(
                    2.3
                    * bare((h, k, ell))
                    / math.sqrt(1 + 0.001 * x * bare((h, k, ell)) * lam**3 / sin2)
                )
            np.testing.assert_allclose(
                calculated(p),
                expected,
                rtol=2e-12,
                atol=1e-13,
                err_msg=(
                    'Larson F squared uses exponent minus one half, lambda cubed, '
                    'metric denominator and single cross terms'
                ),
            )


def test_new_single_crystal_defaults_and_tof_saved_category_absence(tmp_path):
    for tof in (False, True):
        p = model(tmp_path / str(tof), tof=tof)
        assert p.experiments[0].extinction.type == 'none', (
            'New single crystals must default to no extinction'
        )
        calculated(p)
        dest = tmp_path / f'saved-{tof}'
        p.save_as(dest)
        text = next((dest / 'experiments').glob('*.edi')).read_text()
        if tof:
            assert '_instrument.' not in text, (
                'TOF single crystals must save no unused instrument category'
            )
        else:
            assert '_instrument.setup_wavelength' in text, (
                'CW single crystals must retain their wavelength'
            )


def test_out_of_range_displacement_values_save_load_and_calculate(tmp_path):
    for biso in (-0.37, 0, 0.41):
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter('always')
            p = model(tmp_path / str(biso), biso=biso)
            before = calculated(p)
            dest = tmp_path / f'saved-{biso}'
            p.save_as(dest)
            q = engine().Project.load(dest)
            after = calculated(q)
        assert math.isclose(
            float(q.structures[0].atom_sites[0].adp_iso.value), biso, rel_tol=0, abs_tol=0
        ), 'Finite negative, zero and positive Biso must survive save and load unchanged'
        np.testing.assert_allclose(
            after,
            before,
            rtol=1e-12,
            atol=1e-12,
            err_msg=(
                'Out-of-range displacement round trips must retain their physical calculation'
            ),
        )
        if biso == 0:
            assert not any('adp_not_positive_definite' in str(w.message) for w in notices), (
                'A zero displacement tensor is allowed and must not raise an eigenvalue warning'
            )


def test_larson_tensor_allows_signed_offdiagonal_components(tmp_path):
    fields = ''.join(
        f'_extinction.coefficient_{key} {value}\n'
        for key, value in zip(
            ('11', '22', '33', '12', '13', '23'), (0.8, 0.3, 1.4, 0.17, -0.11, 0.23), strict=True
        )
    )
    p = model(tmp_path, extinction='larson-anisotropic', fields=fields)
    expected = []
    for h, k, ell in HKLS:
        s2 = sum((v / a) ** 2 for v, a in zip((h, k, ell), CELL, strict=True)) / 4
        sin2 = 2 * 1.6 * math.sqrt(s2) * math.sqrt(1 - 1.6**2 * s2)
        coefficient = (
            0.8 * h * h
            + 0.3 * k * k
            + 1.4 * ell * ell
            + 0.17 * h * k
            - 0.11 * h * ell
            + 0.23 * k * ell
        ) / (4 * s2)
        expected.append(
            2.3
            * bare((h, k, ell))
            / math.sqrt(1 + 0.001 * coefficient * bare((h, k, ell)) * 1.6**3 / sin2)
        )
    np.testing.assert_allclose(
        calculated(p),
        expected,
        rtol=2e-12,
        atol=1e-13,
        err_msg=(
            'A positive definite Larson tensor may have signed cross terms and'
            ' must load and calculate unchanged'
        ),
    )
