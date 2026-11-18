"""Exact input-only spelling transition; saved-output pins are unchanged."""

import hashlib
import json
import re
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).parent


def archived_before(row):
    with zipfile.ZipFile(HERE / 'source-uncertainties.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'The uncertainty spelling transition retains its complete prior source'
    )
    return before


def previous_bytes(name, data):
    row = json.loads((HERE / 'source-uncertainties.json').read_text()).get(name)
    if row is None:
        return data
    assert hashlib.sha256(data).hexdigest() in {row['before_sha256'], row['after_sha256']}, (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    return archived_before(row)


def previous_content(data):
    digest = hashlib.sha256(data).hexdigest()
    for row in json.loads((HERE / 'source-uncertainties.json').read_text()).values():
        if digest == row['after_sha256']:
            return archived_before(row)
    return data


def reader_values(name, expected, source):
    """Project only the archived input-only free-marker sweep to its saved numeric rule."""
    from tests.fixtures.cif_import_cases import columns  # noqa: PLC0415
    from tests.fixtures.project_save.reference import six_digits  # noqa: PLC0415

    row = json.loads((HERE / 'source-uncertainties.json').read_text()).get(name)
    if row is None or hashlib.sha256(source).hexdigest() == row['before_sha256']:
        return expected
    before = previous_bytes(name, source)
    old, new = columns(before.decode()), columns(source.decode())
    assert old.keys() == new.keys(), 'The free-marker sweep retains every source column'
    result = {tag: list(values) for tag, values in expected.items()}
    for tag in old:
        assert len(old[tag]) == len(new[tag]), 'The free-marker sweep retains every source row'
        for index, (original, current) in enumerate(zip(old[tag], new[tag], strict=True)):
            if original == current:
                continue
            value = re.fullmatch(
                r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\(\d+\)', original
            )
            assert value is not None and current == value[1] + '()', (
                'Only the archived authored uncertainty digits leave the source token'
            )
            if tag in result:
                assert len(result[tag]) == len(new[tag]), (
                    'A saved reader column retains the exact source row identity'
                )
                pinned = re.fullmatch(
                    r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:\((\d*)\))?',
                    result[tag][index],
                )
                assert pinned is not None, 'An authored free-field transition binds a numeric pin'
                nominal = Decimal(value[1])
                prior = Decimal(pinned[1])
                reported = (
                    nominal.quantize(
                        Decimal(1).scaleb(prior.as_tuple().exponent), rounding=ROUND_HALF_UP
                    )
                    if pinned[2]
                    else Decimal(str(six_digits(value[1])))
                )
                assert prior == reported, (
                    'The frozen nominal must match its independently archived input at its '
                    'declared previous reporting precision'
                )
                result[tag][index] = format(six_digits(value[1]), '.15g') + '()'
    return result
