"""Exact input-only spelling transition; saved-output pins are unchanged."""

import hashlib
import json
import zipfile
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
