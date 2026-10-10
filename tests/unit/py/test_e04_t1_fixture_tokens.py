"""Independent token witnesses for the source-text app oracle generator."""

import runpy
from pathlib import Path

GENERATOR = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / 'fixtures/e04_t1/generate.py')
)
NUMERIC = GENERATOR['numeric']


def test_app_oracle_preserves_symbolic_and_incomplete_numeric_tokens():
    for token in ('e', 'E', '+', '-', '.', '1e', '1e+', '1.2.3'):
        assert NUMERIC(token) == token, (
            'I19 : source-text oracle preserves Wyckoff letters and nonnumeric tokens'
        )


def test_app_oracle_retains_number_free_flag_and_uncertainty():
    witnesses = {
        '-1.25e+2()': {'value': -125.0, 'free': True, 'uncertainty': None},
        '1.230(4)': {'value': 1.23, 'free': True, 'uncertainty': 0.004},
        '1.230e2(4)': {'value': 123.0, 'free': True, 'uncertainty': 0.4},
        '+.5': {'value': 0.5, 'free': False, 'uncertainty': 0.0},
        '5.': {'value': 5.0, 'free': False, 'uncertainty': 0.0},
    }
    for token, expected in witnesses.items():
        assert NUMERIC(token) == expected, (
            'I19 : independent decimal/exponent witnesses retain value and free uncertainty'
        )


def test_app_text_oracle_preserves_carriage_return_field_separators(tmp_path):
    experiment = tmp_path / 'experiment.edi'
    experiment.write_bytes(
        b'loop_\n_data.two_theta\n_data.id\n_data.intensity_meas\n_data.intensity_meas_su\n'
        b'12.125 1 31.25\r 0.75\n13.875 2 44.5\r 1.25\n'
    )
    rows = GENERATOR['tables'](experiment, ('_data',))['data']
    assert [row['intensity_meas']['value'] for row in rows] == [31.25, 44.5], (
        'the independent ASCII oracle treats in-record CR as whitespace, not a new record'
    )
    scan = tmp_path / 'scan'
    scan.mkdir()
    (scan / '01.txt').write_bytes(b'12.125 31.25\r 0.75\n13.875 44.5\r 1.25\n')
    datasets = GENERATOR['scan_inputs'](
        tmp_path,
        {
            '_fitting_mode.type': 'sequential',
            '_sequential_fit.data_dir': 'scan',
            '_sequential_fit.file_pattern': '*.txt',
        },
    )
    assert datasets[0]['samples'] == [
        {'index': 0, 'values': [12.125, 31.25, 0.75]},
        {'index': 1, 'values': [13.875, 44.5, 1.25]},
    ], 'scan samples preserve every independently authored ASCII column and measured value'
    (scan / '01.txt').write_bytes(b'11.125 -1.5\n12.125 0.25\n13.875 9\n')
    datasets = GENERATOR['scan_inputs'](
        tmp_path,
        {
            '_fitting_mode.type': 'sequential',
            '_sequential_fit.data_dir': 'scan',
            '_sequential_fit.file_pattern': '*.txt',
        },
    )
    assert datasets[0]['samples'] == [
        {'index': 0, 'values': [12.125, 0.25, 0.5]},
        {'index': 1, 'values': [13.875, 9.0, 3.0]},
    ], 'scan points skip negative intensity and follow the independent Poisson uncertainty rule'
