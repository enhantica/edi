"""The retired absorption scalar never conceals a changed active quantity."""

import hashlib
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.fittability.saved_reference import fingerprints
from tests.fixtures.metadata_transition import retired_source_fields


@pytest.mark.parametrize('spelling', ['0', '0.0'])
@pytest.mark.parametrize(
    'damage', ['none', 'nonzero', 'free', 'duplicate', 'emitted', 'type', 'missing', 'active']
)
def test_saved_absorption_restores_only_the_fixed_zero_for_the_original_hash(
    tmp_path, spelling, damage
):
    source, saved = tmp_path / 'source', tmp_path / 'saved'
    original = b'data_bank\n_absorption.type cylinder\n_absorption.abscor1 0.125\n'
    before = original + b'_absorption.abscor2 0\n'
    for directory in (source, saved):
        (directory / 'experiments').mkdir(parents=True)
    input_file = source / 'experiments/bank.edi'
    output_file = saved / 'experiments/bank.edi'
    input_file.write_bytes(original + b'_absorption.abscor2 ' + spelling.encode() + b'\n')
    output_file.write_bytes(original)
    expected = {'experiments/bank.edi': hashlib.sha256(before).hexdigest()}
    assert fingerprints(saved, order_reference=expected, source=source) == expected, (
        'Saved absorption restores only the fixed zero for the original hash.'
    )
    if damage == 'none':
        return
    if damage in {'nonzero', 'free', 'duplicate'}:
        token = {'nonzero': b'0.25', 'free': b'0()', 'duplicate': b'0\n_absorption.abscor2 0'}[
            damage
        ]
        input_file.write_bytes(original + b'_absorption.abscor2 ' + token + b'\n')
    elif damage == 'emitted':
        output_file.write_bytes(before)
    elif damage == 'type':
        output_file.write_bytes(original.replace(b'cylinder', b'none'))
    elif damage == 'missing':
        output_file.write_bytes(original.replace(b'_absorption.abscor1 0.125\n', b''))
    else:
        output_file.write_bytes(original.replace(b'0.125', b'0.25'))
        assert fingerprints(saved, order_reference=expected, source=source) != expected, (
            'Saved absorption restores only the fixed zero for the original hash.'
        )
        return
    with pytest.raises(AssertionError, match=r'retired|cylinder'):
        fingerprints(saved, order_reference=expected, source=source)


@pytest.mark.parametrize('name', tuple(retired_source_fields.rows()))
@pytest.mark.parametrize('name_type', [str, Path])
def test_retired_source_projection_accepts_path_and_string_without_skipping_identity(
    name, name_type
):
    source = retired_source_fields.ROOT / name
    actual = source.read_bytes()
    row = retired_source_fields.rows()[name]
    with zipfile.ZipFile(retired_source_fields.HERE / 'retired-source-fields.zip') as archive:
        expected = archive.read(row['before_sha256'])
    assert retired_source_fields.previous_bytes(name_type(name), actual) == expected, (
        'Retired source projection accepts path and string without skipping identity.'
    )
    with pytest.raises(AssertionError, match='entire independently archived source'):
        retired_source_fields.previous_bytes(name_type(name), actual + b'\n# extra byte\n')
