"""The rebuilt four-frame fixture labels references and scan pins separately."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'docs/user/cli/pd-xray-cwl_latp_scan-4f'


def test_latp_reference_quantities_are_fullprof_values_not_scan_regression_pins():
    quantities = json.loads((CASE / 'expected.json').read_text())['quantities']
    template = json.loads(
        (ROOT / 'knowledge/fitting/fullprof/pd-xray-cwl_latp-bm01_scan/reference.json').read_text()
    )
    assert {name for name, row in quantities.items() if row['kind'] == 'reference'} == {'n_free'}, (
        'The rebuilt scan keeps only its same-model FullProf free count as a reference'
    )
    assert quantities['n_free']['value'] == template['n_free'], (
        'The rebuilt fixture and its template FullProf model have the same independent free count'
    )
    frames = {'latp_312.dat', 'latp_304.dat', 'latp_296.dat', 'latp_288.dat'}
    expected = {
        f'results[{name}].{field}'
        for name in frames
        for field in ['fit_result.reduced_chi_square', 'latp.cell.length_c']
    }
    assert set(quantities) == expected | {'n_free'}, (
        'Exactly the four owner-selected frames keep per-file chi-square and cell-c pins'
    )
    assert all(quantities[name]['kind'] == 'regression-pin' for name in expected), (
        'Sequential results are regression pins and cannot claim agreement with another measurement'
    )
    assert not (CASE / 'fullprof').exists(), (
        'The rebuilt fixture must not retain FullProf evidence from the replaced measurement'
    )
