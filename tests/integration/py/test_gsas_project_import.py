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
    assert experiment.linked_structure.structure_id == 'phase'
    assert experiment.linked_structure.scale.free is True
    assert experiment.linked_structure.scale.value == pytest.approx(0.313969)
    assert experiment.peak.broad_gauss_u.free is True
    assert experiment.peak.broad_gauss_u.value == pytest.approx(
        354.031 * 8 * math.log(2) / 10000, abs=5e-7
    )
    assert experiment.peak.broad_lorentz_x.value == pytest.approx(0.05729578)
    assert experiment.peak.broad_lorentz_y.value == pytest.approx(0.0109377643, abs=5e-8)
    assert experiment.peak.asym_fcj_1.value == pytest.approx(0.001)
    assert experiment.peak.asym_fcj_2.value == pytest.approx(0.001)
    assert experiment.instrument.calib_twotheta_offset.value == pytest.approx(-0.001)
    assert tuple(experiment.data.two_theta) == (10, 20, 30)
    assert tuple(experiment.data.intensity_meas) == (4, 8, 12)
    assert tuple(experiment.data.intensity_meas_su) == (2, 4, 2)


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
