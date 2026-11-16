"""Only derived fitted outputs use the existing parity rule; original data bytes stay exact."""

import base64
import json
import zlib

import pytest

from tests.fixtures.fittability import calculated_bytes
from tests.fixtures.fittability.calculated_bytes import restore_calculated_reflections
from tests.fixtures.fittability.freeze_fitted_experiment import freeze

REFERENCE = (
    b'data_test\nloop_\n_refln.id\n_refln.index_h\n_refln.intensity_meas\n'
    b'_refln.intensity_calc\n_refln.include_status\n'
    b'1 2 6.125 15 o\n2 4 7.75 0 <\n3 6 8.875 3.5 o\n'
)


def test_derived_reflection_bytes_keep_every_other_token_and_the_original_precision():
    actual = REFERENCE.replace(b' 15 o', b' 15.00000003 o').replace(b' 0 <', b' 0.000000000001 <')
    assert restore_calculated_reflections(actual, REFERENCE) == REFERENCE, (
        'Only derived intensity uses the existing ADR-0057 bound, including a nonzero sample'
    )


@pytest.mark.parametrize(
    'damage',
    [
        'outside',
        'zero-outside',
        'nonfinite',
        'index',
        'measured',
        'status',
        'missing',
        'order',
        'extra',
    ],
)
def test_derived_reflection_adapter_refuses_each_numeric_and_original_data_escape(damage):
    changed = {
        'outside': REFERENCE.replace(b' 15 o', b' 15.0000002 o'),
        'zero-outside': REFERENCE.replace(b' 0 <', b' 0.000000002 <'),
        'nonfinite': REFERENCE.replace(b' 15 o', b' nan o'),
        'index': REFERENCE.replace(b'1 2 ', b'1 3 '),
        'measured': REFERENCE.replace(b'6.125', b'6.126'),
        'status': REFERENCE.replace(b'15 o', b'15 <'),
        'missing': REFERENCE.replace(b'3 6 8.875 3.5 o\n', b''),
        'order': REFERENCE.replace(
            b'1 2 6.125 15 o\n2 4 7.75 0 <\n', b'2 4 7.75 0 <\n1 2 6.125 15 o\n'
        ),
        'extra': REFERENCE + b'4 8 10 2 o\n',
    }[damage]
    with pytest.raises(AssertionError):
        restore_calculated_reflections(changed, REFERENCE)


def test_fitted_reference_recovery_cannot_replace_any_existing_pin_byte(tmp_path, monkeypatch):
    original = calculated_bytes.HOME
    for name in ['saved-main.json', 'fitted-experiment-main.json']:
        (tmp_path / name).write_bytes((original / name).read_bytes())
    paths = {}
    for rule in ['iucr_19', 'iucr_99']:
        paths[rule] = tmp_path / (rule + '.edi')
        paths[rule].write_bytes(calculated_bytes.reference_experiment(rule))
    output = tmp_path / 'recovered.json'
    freeze(paths, output)
    recovered = json.loads(output.read_text())
    original_record = json.loads((original / 'fitted-experiment-main.json').read_text())
    assert {key: value for key, value in recovered.items() if key != 'experiments'} == {
        key: value for key, value in original_record.items() if key != 'experiments'
    }, 'Recovery retains the exact original case, source and regression-only meaning'
    for rule in paths:
        assert zlib.decompress(
            base64.b64decode(recovered['experiments'][rule], validate=True)
        ) == calculated_bytes.reference_experiment(rule), (
            'Recovery reproduces every original saved byte, independent of compression transport'
        )
    paths['iucr_99'].write_bytes(paths['iucr_99'].read_bytes() + b'\n')
    with pytest.raises(ValueError, match='immutable whole-file hash'):
        freeze(paths, output)
    record = json.loads((tmp_path / 'fitted-experiment-main.json').read_text())
    record['experiments']['iucr_19'] = base64.b64encode(
        zlib.compress(paths['iucr_19'].read_bytes() + b'\n')
    ).decode()
    (tmp_path / 'fitted-experiment-main.json').write_text(json.dumps(record))
    monkeypatch.setattr(calculated_bytes, 'HOME', tmp_path)
    with pytest.raises(AssertionError, match='immutable whole-file hash'):
        calculated_bytes.reference_experiment('iucr_19')
