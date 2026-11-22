"""Authenticate exact regression-pin retakes before historical input comparisons."""

import functools
import hashlib
import json
from pathlib import Path

from tests.fixtures.path_keys import repository_key

HERE = Path(__file__).parent
COSIO_D20_2K = 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/expected.json'
# The complete edi 69e1206b document after the CoSiO cell length re-save.
COSIO_REPIN_SHA256 = 'c25181322f98ce89f461d9d7ba100a6850c50d80fd33c982d31012c622c9e932'


@functools.cache
def retake_rows():
    return json.loads((HERE / 'retakes.json').read_text())['files']


def matches_retake(name, data, row):
    digest = hashlib.sha256(data).hexdigest()
    return digest == row['after_sha256'] or (name == COSIO_D20_2K and digest == COSIO_REPIN_SHA256)


def previous_bytes(name, data):
    name = repository_key(name)
    row = retake_rows().get(name)
    if row is None:
        return data
    before = row['before_text'].encode()
    if hashlib.sha256(before).hexdigest() != row['before_sha256']:
        raise ValueError('The retained source must match its complete frozen byte identity')
    if data == before:
        return data
    if not matches_retake(name, data, row):
        raise ValueError('The stop-default retake requires every current document byte')
    old, current = json.loads(before), json.loads(data)

    def restore(previous, updated):
        if isinstance(previous, dict):
            if previous.keys() != updated.keys():
                raise ValueError('A stop-default retake must retain every reference field')
            if previous.get('kind') == 'regression-pin':
                updated['value'] = previous['value']
            for key, value in previous.items():
                restore(value, updated[key])
        elif isinstance(previous, list):
            if len(previous) != len(updated):
                raise ValueError('A stop-default retake must retain the entire input inventory')
            for old_value, new_value in zip(previous, updated, strict=True):
                restore(old_value, new_value)
        elif previous != updated:
            raise ValueError('Only regression values may change; references and bounds stay exact')

    restore(old, current)
    return before


def composed_bytes(name, data):
    name = repository_key(name)
    row = retake_rows().get(name)
    if row is not None and matches_retake(name, data, row):
        return previous_bytes(name, data)
    return data
