"""Reverse the exact default-variant key rename before unchanged historical byte gates."""

import hashlib
import json
from pathlib import Path


def restore_variant_name(relative, raw):
    rows = json.loads(Path(__file__).with_name('variant-name-projection.json').read_text())[
        'files'
    ]
    row = rows.get(str(relative))
    if row is None:
        return raw
    assert hashlib.sha256(raw).hexdigest() == row['after_sha256'], (
        'The variant rename must first authenticate every current source byte'
    )
    assert raw.count(b'"fast-descent-and-ladder"') == 1, (
        'The variant rename must change exactly one canonical default key'
    )
    old = raw.replace(b'"fast-descent-and-ladder"', b'"multistart-prune"')
    assert hashlib.sha256(old).hexdigest() == row['before_sha256'], (
        'Reversing the variant rename must retain every historical quantity and tolerance byte'
    )
    return old
