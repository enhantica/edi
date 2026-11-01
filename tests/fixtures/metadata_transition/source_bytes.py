"""Compare historical oracles through exact, archived metadata migrations."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def previous_bytes(name, data):
    rows = json.loads((HERE / 'sources.json').read_text())['files']
    row = rows.get(str(name))
    if row is None:
        return data
    if hashlib.sha256(data).hexdigest() == row['before_sha256']:
        return data
    assert hashlib.sha256(data).hexdigest() == row['after_sha256'], (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    with zipfile.ZipFile(HERE / 'sources.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'Historical source comparisons retain their independently committed complete input'
    )
    return before


def read_previous(path):
    data = path.read_bytes()
    if not path.is_relative_to(ROOT):
        return data
    return previous_bytes(path.relative_to(ROOT).as_posix(), data)
