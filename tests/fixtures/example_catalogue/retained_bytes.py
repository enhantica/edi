"""Reverse only whole, committed adaptations before checking the older byte witness."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent


def retained_bytes(relative, data):
    entries = json.loads((HERE / 'retention-adaptations.json').read_text())['files']
    row = entries.get(str(relative))
    if row is None:
        return data
    before, after = row['before'].encode(), row['after'].encode()
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'A retained adaptation must bind its complete original committed input'
    )
    assert hashlib.sha256(after).hexdigest() == row['after_sha256'], (
        'A retained adaptation must bind its complete decided committed replacement'
    )
    assert data == after, (
        'Only the exact committed pin or descriptive adaptation may replace retained bytes'
    )
    return before
