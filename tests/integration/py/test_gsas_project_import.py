import json
import math

import edi
import pytest


def _bundle():
    return {
        'format': 'gsas-ii-pnc-v1',
        'source': {'filename': 'test.gpx'},
        'phase': {
            'name': 'PbSO4',
            'space_group': 'P n m a',
            'cell': [8.48, 5.398, 6.958, 90, 90, 90],
            'atoms': [['Pb1', 'Pb', 0.1882, 0.25, 0.167, 1, 0.01]],
        },
        'histogram': {
            'name': 'PWDR PbSO4',
            'type': 'PNC',
            'instrument': {
                'Lam': [1.909, False],
                'Zero': [-0.001, False],
                'U': [354.031, True],
                'V': [-760.404, False],
                'W': [651.592, False],
                'X': [0, False],
                'Y': [0, False],
                'SH/L': [0.002, False],
            },
            'sample': {
                'size_um': 1,
                'microstrain_ppm': 1000,
                'scale': [10000, True],
                'phase_scale': [1, False],
            },
            'background': {'refine': False, 'coefficients': [5, 1]},
            'observations': [[10, 4, 0.25], [20, 8, 0.0625], [30, 12, 0.25]],
        },
    }


def test_gsas_text_import_round_trips_settings_and_observations(tmp_path):
    source = tmp_path / 'test.gsas.json'
    source.write_text(json.dumps(_bundle()), encoding='ascii')
    project = edi.Project.load(source)
    project.save_as(tmp_path / 'saved')
    reopened = edi.Project.load(tmp_path / 'saved/project.edi')
    experiment = reopened.experiments['powder']
    assert experiment.linked_structure.structure_id == 'phase', (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.linked_structure.scale.free is True, (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.linked_structure.scale.value == pytest.approx(0.313969), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.broad_gauss_u.free is True, (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.broad_gauss_u.value == pytest.approx(
        354.031 * 8 * math.log(2) / 10000, abs=5e-7
    ), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.broad_lorentz_x.value == pytest.approx(0.05729578), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.broad_lorentz_y.value == pytest.approx(0.0109377643, abs=5e-8), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.asym_fcj_1.value == pytest.approx(0.001), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.peak.asym_fcj_2.value == pytest.approx(0.001), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert experiment.instrument.calib_twotheta_offset.value == pytest.approx(-0.001), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert tuple(experiment.data.two_theta) == (10, 20, 30), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert tuple(experiment.data.intensity_meas) == (4, 8, 12), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )
    assert tuple(experiment.data.intensity_meas_su) == (2, 4, 2), (
        'GSAS-II import and native reopen preserve converted profile parameters and '
        'measured observations.'
    )


def test_gsas_cw_import_uses_native_parameter_metadata_before_save(tmp_path):
    bundle = _bundle()
    histogram = bundle['histogram']
    histogram['type'] = 'PXC'
    histogram['instrument'].update({
        'Lam2': [1.913, False],
        'ratio': [0.5, False],
        'polarization': [0.8, False],
        'azimuth': [0, False],
    })
    histogram['sample'] = {
        'scale': [10000, True],
        'radius_mm': 200,
        'displace_x': [0, False],
        'displace_y': [0, False],
    }
    histogram['links'] = [
        {
            'phase_index': 0,
            'phase_scale': [1, False],
            'size_um': 1,
            'microstrain_ppm': 1000,
        }
    ]
    source = tmp_path / 'test.gsas.json'
    source.write_text(
        json.dumps({
            'format': 'gsas-ii-powder-v2',
            'source': bundle['source'],
            'phases': [bundle['phase']],
            'histograms': [histogram],
        }),
        encoding='ascii',
    )
    project = edi.Project.load(source)
    experiment = project.experiments['powder']

    for field, units in {
        'setup_wavelength': 'angstroms',
        'calib_twotheta_offset': 'degrees',
        'calib_sample_displacement': 'degrees',
        'calib_sample_transparency': 'degrees',
        'setup_wavelength_2': 'angstroms',
        'setup_wavelength_2_to_1_ratio': 'dimensionless',
        'setup_polarization_coefficient': 'dimensionless',
        'setup_monochromator_twotheta': 'degrees',
    }.items():
        parameter = getattr(experiment.instrument, field)
        assert parameter.name == field, (
            'GSAS-II CW parameters retain their declared native names and units before saving.'
        )
        assert parameter.units == units, (
            'GSAS-II CW parameters retain their declared native names and units before saving.'
        )

    for field in (
        'broad_gauss_u',
        'broad_gauss_v',
        'broad_gauss_w',
        'broad_lorentz_x',
        'broad_lorentz_y',
        'asym_fcj_1',
        'asym_fcj_2',
    ):
        assert getattr(experiment.peak, field).name == field, (
            'GSAS-II CW parameters retain their declared native names and units before saving.'
        )


def test_gsas_text_refuses_zero_weight(tmp_path):
    bundle = _bundle()
    bundle['histogram']['observations'][1][2] = 0
    source = tmp_path / 'test.gsas.json'
    source.write_text(json.dumps(bundle), encoding='ascii')
    with pytest.raises(edi.IoError, match='positive weights'):
        edi.Project.load(source)


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (b'cbuiltins\nstr\n.', 'unsupported serialized object'),
        (b']X\x04\x00\x00\x00Y', 'truncated GPX'),
        (b'\x80\x05].', 'unsupported GPX pickle protocol'),
    ],
)
def test_native_gpx_refuses_unknown_objects_and_incomplete_records(tmp_path, payload, message):
    source = tmp_path / 'test.gpx'
    source.write_bytes(payload)
    with pytest.raises(edi.IoError, match=message):
        edi.Project.load(source)


def test_gsas_powder_bundle_preserves_zero_weight_and_fit_range(tmp_path):
    bundle = _bundle()
    phase = bundle['phase']
    hist = bundle['histogram']
    hist['sample'] = {'scale': [1, False]}
    hist['links'] = [
        {
            'phase_index': 0,
            'phase_scale': [1, False],
            'size_um': 1,
            'microstrain_ppm': 0,
        }
    ]
    hist['background']['basis'] = 'chebyschev'
    hist['background']['coefficients'] = [2, 0, 4]
    hist['observations'] = [[10, 4, 0], [20, 8, 0.25], [30, 7, 1], [40, 5, 0.5]]
    hist['fit_limits'] = [[20, 40]]
    source = tmp_path / 'test.gsas.json'
    source.write_text(
        json.dumps({
            'format': 'gsas-ii-powder-v2',
            'source': bundle['source'],
            'phases': [phase],
            'histograms': [hist, hist],
        }),
        encoding='ascii',
    )
    project = edi.Project.load(source)
    project.save_as(tmp_path / 'saved')
    reopened = edi.Project.load(tmp_path / 'saved/project.edi')
    assert reopened.analysis.fitting_mode == 'joint', (
        'GSAS-II powder imports preserve joint banks, fit ranges, background order '
        'and zero-weight exclusions.'
    )
    for experiment in reopened.experiments:
        assert tuple(experiment.data.two_theta) == (10, 20, 30, 40), (
            'GSAS-II powder imports preserve joint banks, fit ranges, background order '
            'and zero-weight exclusions.'
        )
        assert experiment.background_x_min == 20, (
            'GSAS-II powder imports preserve joint banks, fit ranges, background order '
            'and zero-weight exclusions.'
        )
        assert experiment.background_x_max == 40, (
            'GSAS-II powder imports preserve joint banks, fit ranges, background order '
            'and zero-weight exclusions.'
        )
        assert tuple(term.coef.value for term in experiment.background_terms) == (4, 0, 2), (
            'GSAS-II powder imports preserve joint banks, fit ranges, background order '
            'and zero-weight exclusions.'
        )
        assert 'gsas-zero-weight-1' in experiment.excluded_region_ids, (
            'GSAS-II powder imports preserve joint banks, fit ranges, background order '
            'and zero-weight exclusions.'
        )


def test_gsas_free_axial_aperture_is_one_parameter_after_save(tmp_path):
    bundle = _bundle()
    bundle['histogram']['instrument']['SH/L'] = [0.02, True]
    source = tmp_path / 'test.gsas.json'
    source.write_text(json.dumps(bundle), encoding='ascii')
    project = edi.Project.load(source)
    project.save_as(tmp_path / 'saved')
    reopened = edi.Project.load(tmp_path / 'saved/project.edi')
    peak = reopened.experiments['powder'].peak
    assert peak.asym_fcj_1.value == peak.asym_fcj_2.value == 0.01, (
        'A free GSAS-II axial aperture remains one independent parameter after native reopen.'
    )
    assert peak.asym_fcj_1.free is True, (
        'A free GSAS-II axial aperture remains one independent parameter after native reopen.'
    )
    assert peak.asym_fcj_2.free is False, (
        'A free GSAS-II axial aperture remains one independent parameter after native reopen.'
    )
    assert len(reopened.analysis.constraints) == 1, (
        'A free GSAS-II axial aperture remains one independent parameter after native reopen.'
    )
