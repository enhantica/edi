"""Native newline transport leaves scientific and opaque bytes fully observable."""

import copy
import hashlib
import os

import pytest

from tests.fixtures.fittability.saved_reference import fingerprints, historical_solver_record
from tests.fixtures.project_categories.historical_bytes import (
    native_edi_bytes,
    require_saved_spacing,
)


@pytest.mark.parametrize('separator', ['\n', '\r\n'])
@pytest.mark.parametrize('damage', ['none', 'value', 'comment', 'extra-blank', 'opaque'])
def test_saved_byte_caller_only_projects_native_edi_newlines(
    tmp_path, monkeypatch, separator, damage
):
    data = b'data_example\n_cell.length_a 4.125\n\n# retained comment\n_atom_site.label Ca\n'
    source = data.replace(b'\n', separator.encode())
    monkeypatch.setattr(os, 'linesep', separator)
    assert native_edi_bytes(source) == data, 'Saved byte caller only projects native edi newlines.'
    directory = tmp_path / 'saved'
    directory.mkdir()
    (directory / 'project.edi').write_bytes(source)
    (directory / 'opaque.dat').write_bytes(b'1\r\n2\n')
    expected = {
        'project.edi': hashlib.sha256(data).hexdigest(),
        'opaque.dat': hashlib.sha256(b'1\r\n2\n').hexdigest(),
    }
    assert fingerprints(directory, order_reference=expected) == expected, (
        'Saved byte caller only projects native edi newlines.'
    )
    if damage == 'none':
        return
    if damage == 'opaque':
        (directory / 'opaque.dat').write_bytes(b'1\n2\n')
    else:
        source = source.replace(
            *{
                'value': (b'4.125', b'4.25'),
                'comment': (b'retained comment', b'changed comment'),
                'extra-blank': (separator.encode() * 2, separator.encode() * 3),
            }[damage]
        )
        (directory / 'project.edi').write_bytes(source)
    assert fingerprints(directory, order_reference=expected) != expected, (
        'Saved byte caller only projects native edi newlines.'
    )
    if damage == 'extra-blank':
        with pytest.raises(AssertionError, match='no blank inside scalar categories'):
            require_saved_spacing(source)


@pytest.mark.parametrize(
    'damage',
    ['none', 'descent', 'rule', 'iterations', 'value', 'shift', 'missing', 'duplicate', 'science'],
)
def test_historical_fit_record_checks_live_diagnostics_without_replacing_original_values(damage):
    old = (
        b'_fit_result.descent ladder\n_fit_result.iterations 5\n'
        b'_fit_result.objective_value 16751\n'
    )
    additions = (
        b'_minimizer.descent ladder\n_minimizer.stop_rules "chi_square_change"\n'
        b'_fit_result.stopping_rule chi_square_change\n'
        b'_fit_result.stopping_value 0.0000000000033344\n_fit_result.last_shift_su 0.000026342\n'
    )
    observed = {
        'descent': 'ladder',
        'stop_rules': 'chi_square_change',
        'iterations': 5,
        'stopping_rule': 'chi_square_change',
        'stopping_value': 3.3343951915630797e-12,
        'last_shift_su': 2.6342026378706392e-5,
    }
    data = old + additions
    assert historical_solver_record(data, observed) == old, (
        'Historical fit record checks live diagnostics without replacing original values.'
    )
    if damage == 'none':
        return
    if damage in {'descent', 'rule'}:
        observed = copy.deepcopy(observed)
        observed['descent' if damage == 'descent' else 'stopping_rule'] = 'changed'
    elif damage == 'iterations':
        data = data.replace(b'iterations 5', b'iterations 4')
    elif damage == 'value':
        data = data.replace(b'0.0000000000033344', b'0.0001')
    elif damage == 'shift':
        data = data.replace(b'0.000026342', b'nan')
    elif damage == 'missing':
        data = data.replace(b'_fit_result.stopping_rule chi_square_change\n', b'')
    elif damage == 'duplicate':
        data += b'_fit_result.stopping_rule chi_square_change\n'
    else:
        data = data.replace(b'objective_value 16751', b'objective_value 16752')
        assert historical_solver_record(data, observed) != old, (
            'Historical fit record checks live diagnostics without replacing original values.'
        )
        return
    with pytest.raises(AssertionError):
        historical_solver_record(data, observed)
