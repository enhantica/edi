"""Published measured-data assets retain the source observation tokens on both geometries."""

import json
from pathlib import Path

import gemmi
import pytest

from tools.data import build_collection as writer

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    'pd-neut-cwl_lbco-hrpt',
    'sc-neut-cwl_tb2ti2o7-heidi',
    'sc-neut-cwl_pr2nio4-5c2',
    'sc-neut-tof_taurine-senju',
    'sc-neut-cwl_cosio-heidi',
    'sc-neut-cwl_tb2ti2o7-heidi_simulation',
)


@pytest.mark.parametrize('case', CASES)
def test_actual_measured_asset_writer_retains_the_project_observations(case, tmp_path):
    folder = ROOT / 'docs/user/cli' / case
    (tmp_path / 'data').mkdir()
    for experiment in sorted((folder / 'project/experiments').glob('*.edi')):
        count = writer.export_measured_data(experiment, tmp_path, case, {'name': 'Measured β'})
        supplied = folder / 'data' / (experiment.stem + '.hkl')
        original = gemmi.cif.read_file(str(experiment)).sole_block()
        identity = case + '-' + experiment.stem
        if case.endswith('_simulation'):
            assert count == 0, 'Actual measured asset writer retains the project observations.'
            assert not list((tmp_path / 'data').iterdir()), (
                'Actual measured asset writer retains the project observations.'
            )
            continue
        assert count == 1, 'Actual measured asset writer retains the project observations.'
        if supplied.is_file():
            target = tmp_path / 'data' / (identity + '.hkl')
            assert target.read_bytes() == supplied.read_bytes(), (
                'Actual measured asset writer retains the project observations.'
            )
        elif case.startswith('sc-'):
            target = tmp_path / 'data' / (identity + '.hkl')
            written = gemmi.cif.read_file(str(target)).sole_block()
            columns = [
                '_refln.index_h',
                '_refln.index_k',
                '_refln.index_l',
                '_refln.intensity_meas',
                '_refln.intensity_meas_su',
            ]
            assert [list(row) for row in written.find(columns)] == [
                list(row) for row in original.find(columns)
            ], 'Actual measured asset writer retains the project observations.'
            assert not written.find_values('_refln.intensity_calc'), (
                'Actual measured asset writer retains the project observations.'
            )
        else:
            target = tmp_path / 'data' / (identity + '.xye')
            columns = ['_data.two_theta', '_data.intensity_meas', '_data.intensity_meas_su']
            assert [line.split() for line in target.read_text(encoding='utf-8').splitlines()] == [
                list(row) for row in original.find(columns)
            ], 'Actual measured asset writer retains the project observations.'
        sidecar = json.loads(
            target.with_name(target.name + '.meta.json').read_text(encoding='utf-8')
        )
        assert sidecar == {'id': identity + '-data', 'name': 'Measured β'}, (
            'Actual measured asset writer retains the project observations.'
        )


def test_reflection_export_refuses_incomplete_or_malformed_measurement_rows():
    text = (
        'data_reflections\n\nloop_\n'
        + '\n'.join(writer.REFLECTION_COLUMNS)
        + '\n1 2 -3 4.500 0.200\n'
    )
    assert '1 2 -3 4.500 0.200' in writer.measured_reflections(text), (
        'Reflection export refuses incomplete or malformed measurement rows.'
    )
    missing = text.replace('_refln.intensity_meas_su\n', '').replace(' 0.200', '')
    assert not writer.measured_reflections(missing), (
        'Reflection export refuses incomplete or malformed measurement rows.'
    )
    with pytest.raises(ValueError, match=r'(?i)number of values'):
        writer.measured_reflections(text.replace(' 0.200', ''))
