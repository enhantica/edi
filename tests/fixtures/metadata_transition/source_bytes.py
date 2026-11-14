"""Compare historical oracles through exact, archived metadata migrations."""

import functools
import hashlib
import json
import zipfile
from pathlib import Path

from tests.fixtures.metadata_transition import (
    pin_sources,
    release_pin_bytes,
    retired_source_fields,
    task_inputs,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def previous_bytes(name, data):
    data = pin_sources.previous_bytes(name, data)
    data = release_pin_bytes.previous_bytes(name, data)
    data = retired_source_fields.previous_bytes(name, data)
    data = task_inputs.previous_bytes(name, data)
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


@functools.cache
def archived_content_pairs():
    """Exact input identities also apply when the runner stages a private source copy."""
    rows = json.loads((HERE / 'sources.json').read_text())['files']
    return {row['after_sha256']: row['before_sha256'] for row in rows.values()}


def previous_content(data):
    data = task_inputs.previous_content(data)
    before_hash = archived_content_pairs().get(hashlib.sha256(data).hexdigest())
    if before_hash is None:
        return data
    with zipfile.ZipFile(HERE / 'sources.zip') as archive:
        before = archive.read(before_hash)
    assert hashlib.sha256(before).hexdigest() == before_hash, (
        'A staged input adaptation retains the complete archived pre-migration bytes'
    )
    return before
