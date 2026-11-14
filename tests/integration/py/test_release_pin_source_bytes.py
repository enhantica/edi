"""Historical byte inventories remain exact across a committed regression retake."""

import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.metadata_transition import pin_sources
from tests.fixtures.metadata_transition import release_pin_bytes as source

ROOT = Path(__file__).resolve().parents[3]


def test_complete_release_source_pairs_retain_their_archived_byte_identities():
    rows = source.rows()
    assert rows and source.LATER_INPUT_CASE not in rows, (
        'Complete release source pairs retain their archived byte identities.'
    )
    with zipfile.ZipFile(source.HERE / 'release-pins.zip') as archive:
        assert set(archive.namelist()) == {
            row[key] for row in rows.values() for key in ('before_sha256', 'after_sha256')
        }, 'Complete release source pairs retain their archived byte identities.'
        for name, row in rows.items():
            before = archive.read(row['before_sha256'])
            after = archive.read(row['after_sha256'])
            assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
                'Complete release source pairs retain their archived byte identities.'
            )
            assert hashlib.sha256(after).hexdigest() == row['after_sha256'], (
                'Complete release source pairs retain their archived byte identities.'
            )
            assert pin_sources.previous_bytes(name, (ROOT / name).read_bytes()) == after, (
                'Complete release source pairs retain their archived byte identities.'
            )
            assert source.previous_bytes(name, after) == before, (
                'Complete release source pairs retain their archived byte identities.'
            )
            assert source.previous_bytes(name, before) == before, (
                'Complete release source pairs retain their archived byte identities.'
            )
            source.validate(json.loads(before), json.loads(after), name)
            for damaged in (after + b'\n', after[:-1], after.replace(b'"value"', b'"foreign"', 1)):
                with pytest.raises(AssertionError, match='every committed source byte'):
                    source.previous_bytes(name, damaged)
    assert source.previous_bytes('unmapped/expected.json', b'foreign') == b'foreign', (
        'Complete release source pairs retain their archived byte identities.'
    )


@pytest.mark.parametrize('name', sorted(source.rows()))
def test_rebinding_a_source_hash_cannot_launder_reference_changes(monkeypatch, name):
    rows = source.rows()
    row = rows[name]
    with zipfile.ZipFile(source.HERE / 'release-pins.zip') as archive:
        after = json.loads(archive.read(row['after_sha256']))
    for trail, reference in source.references(after).items():
        for field in ('value', 'kind', 'tol_abs', 'tol_rel'):
            if field not in reference:
                continue
            mutated = copy.deepcopy(after)
            current = mutated
            for key in trail:
                current = current[key]
            current[field] = 'altered'
            raw = json.dumps(mutated).encode()
            mapping = {**rows, name: {**row, 'after_sha256': hashlib.sha256(raw).hexdigest()}}
            with monkeypatch.context() as scoped:
                scoped.setattr(source, 'rows', lambda mapping=mapping: mapping)
                with pytest.raises(AssertionError):
                    source.previous_bytes(name, raw)


def test_iteration_classification_exception_is_bound_to_its_exact_source():
    name = source.ITERATION_CASE
    row = source.rows()[name]
    with zipfile.ZipFile(source.HERE / 'release-pins.zip') as archive:
        before = json.loads(archive.read(row['before_sha256']))
        after = json.loads(archive.read(row['after_sha256']))
    source.validate(before, after, name)
    with pytest.raises(AssertionError):
        source.validate(before, after, 'another/expected.json')
    for field in ('value', 'kind', 'tol_abs', 'tol_rel'):
        mutated = copy.deepcopy(after)
        mutated['edi']['quantities']['iterations'][field] = 'altered'
        with pytest.raises(AssertionError):
            source.validate(before, mutated, name)
    mutated = copy.deepcopy(after)
    mutated['edi']['source'] += ' altered'
    with pytest.raises(AssertionError):
        source.validate(before, mutated, name)
