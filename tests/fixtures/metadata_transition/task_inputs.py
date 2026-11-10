"""Reverse only complete source pairs for declared stop rules and scan widths."""

import functools
import hashlib
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).parent


@functools.cache
def rows():
    return json.loads((HERE / 'task-inputs.json').read_text())['files']


def archived(digest):
    with zipfile.ZipFile(HERE / 'task-inputs.zip') as archive:
        data = archive.read(digest)
    assert hashlib.sha256(data).hexdigest() == digest, (
        'A task input transition must retain its complete independently committed source'
    )
    return data


def previous_bytes(name, data):
    row = rows().get(str(name))
    if row is None:
        return data
    assert hashlib.sha256(data).hexdigest() == row['after_sha256'], (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    return archived(row['before_sha256'])


def previous_content(data):
    digest = hashlib.sha256(data).hexdigest()
    matching = {row['before_sha256'] for row in rows().values() if row['after_sha256'] == digest}
    assert len(matching) <= 1, 'One complete task input cannot have ambiguous historical origins'
    return archived(matching.pop()) if matching else data


def saved_analysis(data, source):
    """Check the declared or legacy stop rule before retaining older saved-byte pins."""
    path = Path(source) / 'analysis/analysis.edi'
    original = path.read_bytes() if path.is_file() else b''
    declared = re.findall(rb'(?m)^_minimizer\.stop_rule[ \t]+([^\r\n]+)', original)
    assert len(declared) <= 1, 'The input stop rule is a unique scalar declaration'
    expected = declared[0].strip() if declared else b'chi_square'
    assert expected in {b'chi_square', b'chi_square_change', b'shift_su'}, (
        'The byte adapter admits only declared stop rules'
    )
    pattern = rb'(?m)^_minimizer\.stop_rule[ \t]+([^\r\n]+)\r?\n'
    actual = re.findall(pattern, data)
    if not actual and expected == b'chi_square':
        return data  # The implicit legacy value keeps its original omitted spelling.
    assert actual == [expected], (
        'The saved stop rule must equal its explicit input or the legacy chi-square default'
    )
    return re.sub(pattern, b'', data)


def saved_experiment(data, source):
    """Check the new fixed scan width before retaining its old complete byte witness."""
    root = HERE.resolve().parents[2]
    source = Path(source)
    if not source.is_relative_to(root):
        return data
    name = source.relative_to(root).as_posix()
    row = rows().get(name)
    if row is None or row['source_commit'] != 'b9bdbf9a2':
        return data
    previous_bytes(name, source.read_bytes())
    old, new = (archived(row[key]) for key in ('before_sha256', 'after_sha256'))
    pattern = rb'(?m)^_peak\.broad_lorentz_y[^\r\n]+\r?\n'
    before, after = (re.findall(pattern, text) for text in (old, new))
    assert len(before) == len(after) == 1 and re.findall(pattern, data) == after, (
        'The written scan width must retain its exact declared fixed value and free state'
    )
    return re.sub(pattern, lambda _: before[0], data)
