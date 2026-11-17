"""Compose exact seed updates ahead of immutable historical source comparisons."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

from tests.fixtures.c06_t8.variant_name_projection import restore_variant_name
from tests.fixtures.path_keys import repository_key
from tests.fixtures.stop_defaults import retention

HERE = Path(__file__).parent
ROOT = HERE.parents[2]


def previous_bytes(name, data):
    name = repository_key(name)
    data = retention.previous_bytes(name, data)
    data = restore_variant_name(name, data)
    row = json.loads((HERE / 'seed-updates.json').read_text())['files'].get(name)
    if row is None:
        return data
    assert hashlib.sha256(data).hexdigest() == row['current_sha256'], (
        'A seed update first authenticates every current scientific and metadata byte'
    )
    if row['kind'] == 'regression-and-retired-strategy-update':
        history = json.loads(
            (ROOT / 'tests/fixtures/example_catalogue/retention-adaptations.json').read_text()
        )['files']
        old = history[name]['after'].encode()
    elif row['kind'] == 'default-stop-rule-set':
        assert row['effective_rules'] == ['chi_square_change', 'shift_su'], (
            'The default rule set retains the exact effective meaning of the legacy Shift/s.u. '
            'declaration'
        )
        with zipfile.ZipFile(
            ROOT / 'tests/fixtures/metadata_transition/task-inputs.zip'
        ) as archive:
            old = archive.read(row['previous_sha256'])
        assert (
            old.count(b'_minimizer.stop_rule shift_su\n') == 1
            and old.replace(b'_minimizer.stop_rule shift_su\n', b'') == data
        ), 'The stop-rule source stage removes only its one authenticated legacy selector row'
    else:
        assert row['kind'] == 'removed-zero-absorption-scalar', (
            'The seed stage admits only its declared update categories'
        )
        matches = re.findall(rb'(?m)^_absorption\.abscor1[^\n]*\n', data)
        assert len(matches) == 1 and row['removed'] == '_absorption.abscor2 0.0\n', (
            'The historical absorption comparison retains exactly one independently named zero '
            'scalar'
        )
        old = data.replace(matches[0], matches[0] + row['removed'].encode(), 1)
    assert hashlib.sha256(old).hexdigest() == row['previous_sha256'], (
        'The seed stage must restore the complete existing historical byte witness'
    )
    return old


def previous_content(data):
    digest = hashlib.sha256(data).hexdigest()
    rows = json.loads((HERE / 'seed-updates.json').read_text())['files']
    variants = json.loads((HERE / 'variant-name-projection.json').read_text())['files']
    names = {name for name, row in rows.items() if row['current_sha256'] == digest}
    names.update(name for name, row in variants.items() if row['after_sha256'] == digest)
    results = {previous_bytes(name, data) for name in names}
    assert len(results) <= 1, (
        'A complete staged seed input cannot have ambiguous historical origins'
    )
    return results.pop() if results else data
