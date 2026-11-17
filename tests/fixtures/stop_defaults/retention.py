"""Authenticate exact regression-pin retakes before historical input comparisons."""

import hashlib
import json
from pathlib import Path

from tests.fixtures.path_keys import repository_key

HERE = Path(__file__).parent


def previous_bytes(name, data):
    row = json.loads((HERE / 'retakes.json').read_text())['files'].get(repository_key(name))
    if row is None:
        return data
    before = row['before_text'].encode()
    if hashlib.sha256(before).hexdigest() != row['before_sha256']:
        raise ValueError('The retained source must match its complete frozen byte identity')
    if data == before:
        return data
    if hashlib.sha256(data).hexdigest() != row['after_sha256']:
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
    row = json.loads((HERE / 'retakes.json').read_text())['files'].get(repository_key(name))
    if row is not None and hashlib.sha256(data).hexdigest() == row['after_sha256']:
        return previous_bytes(name, data)
    return data
