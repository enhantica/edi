"""Forward immutable saved-byte witnesses through the decimal uncertainty rule.

No engine is imported. The original hash must match an archived saved file,
possibly with the already declared calculator and geometry adaptations.
"""

import hashlib
import json
import re
import zipfile
from functools import cache
from pathlib import Path

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.report_units.iucr_reference import saved_record

ROOT = Path(__file__).resolve().parents[3]
GEOMETRY = b'_geom.min_bond_distance_cutoff 0\n_geom.bond_distance_inc 0.25\n'


def build_projections():
    result = {}
    with zipfile.ZipFile(ROOT / 'tests/fixtures/c13_t12_ids/baseline.zip') as archive:
        for name in archive.namelist():
            if '/saved/' not in name or not name.endswith('.edi'):
                continue
            original = original_tokens(archive.read(name))
            variants = {original, original.replace(b'_calculator.type crysta\n\n', b'')}
            if '/structures/' in name and b'_geom.' not in original:
                variants |= {
                    value.replace(b'loop_\n', GEOMETRY + b'\nloop_\n', 1) for value in variants
                }
            if name.endswith('/structures/ncaf.edi'):
                variants |= {without_follower_brackets(value) for value in variants}
            for value in variants:
                result[hashlib.sha256(value).hexdigest()] = hashlib.sha256(
                    saved_record(value)
                ).hexdigest()
    with zipfile.ZipFile(Path(__file__).with_name('iucr-fullprof-before.zip')) as archive:
        for name in archive.namelist():
            original = archive.read(name)
            result[hashlib.sha256(original).hexdigest()] = hashlib.sha256(
                saved_record(original)
            ).hexdigest()
    return result


def projection_sources():
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            'tests/fixtures/c13_t12_ids/baseline.zip',
            'tests/fixtures/report_units/iucr-fullprof-before.zip',
            'tests/fixtures/report_units/iucr_reference.py',
        )
    }


@cache
def projections():
    record = json.loads((ROOT / 'tests/fixtures/project_save/saved-projections.json').read_text())
    assert record['sources'] == projection_sources(), (
        'Saved-byte projections bind immutable archives and the independent decimal reference'
    )
    return record['projections']


def rounded_pins(expected):
    """Keep every historical path and hash; project only hash-proven saved tokens."""
    mapping = projections()
    return {name: mapping.get(digest, digest) for name, digest in expected.items()}


def without_follower_brackets(data):
    lines = []
    for original_line in data.splitlines(keepends=True):
        line = original_line
        cells = list(re.finditer(rb'\S+', line))
        if cells and cells[0][0] in {b'Al1', b'Na1', b'F3'}:
            leader = cells[2][0].split(b'(')[0]
            for cell in reversed(cells[3:5]):
                if cell[0].split(b'(')[0] == leader:
                    line = line[: cell.start()] + leader + line[cell.end() :]
        lines.append(line)
    return b''.join(lines)
