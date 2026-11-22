"""Compare historical oracles through exact, archived metadata migrations."""

import functools
import hashlib
import io
import json
import zipfile
from pathlib import Path

from tests.fixtures.c06_t8 import seed_updates
from tests.fixtures.metadata_transition import (
    pin_sources,
    release_pin_bytes,
    retired_source_fields,
    task_inputs,
)
from tests.fixtures.path_keys import repository_key
from tests.fixtures.stop_defaults import example_inputs
from tests.fixtures.table_display import source_uncertainties
from tests.fixtures.table_display.source_uncertainties import previous_bytes as uncertainties

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


@functools.cache
def historical_source_rows():
    return json.loads((HERE / 'sources.json').read_text())['files']


@functools.cache
def historical_source_archive():
    # Index the immutable fixture once without retaining a filesystem handle.
    return zipfile.ZipFile(io.BytesIO((HERE / 'sources.zip').read_bytes()))


def previous_bytes(name, data):
    data = uncertainties(repository_key(name), data)
    data = example_inputs.composed_bytes(name, data)
    data = seed_updates.previous_bytes(name, data)
    data = pin_sources.previous_bytes(name, data)
    data = release_pin_bytes.previous_bytes(name, data)
    data = retired_source_fields.previous_bytes(name, data)
    data = task_inputs.previous_bytes(name, data)
    row = historical_source_rows().get(repository_key(name))
    if row is None:
        return data
    if hashlib.sha256(data).hexdigest() == row['before_sha256']:
        return data
    assert hashlib.sha256(data).hexdigest() == row['after_sha256'], (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    before = historical_source_archive().read(row['before_sha256'])
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
    return {row['after_sha256']: row['before_sha256'] for row in historical_source_rows().values()}


def previous_content(data):
    data = source_uncertainties.previous_content(data)
    data = example_inputs.previous_content(data)
    data = task_inputs.previous_content(seed_updates.previous_content(data))
    before_hash = archived_content_pairs().get(hashlib.sha256(data).hexdigest())
    if before_hash is None:
        return data
    before = historical_source_archive().read(before_hash)
    assert hashlib.sha256(before).hexdigest() == before_hash, (
        'A staged input adaptation retains the complete archived pre-migration bytes'
    )
    return before
