"""Adapt frozen source witnesses only across independently archived descriptions.

No app, writer or calculation supplies an expectation. The existing source-only
archive proves complete before/after bytes and refuses changes outside declared
description/type fields. Every scientific, dataset, ordering and display witness
in the old oracle is retained.
"""

import copy
import hashlib
import json
from pathlib import Path

from tests.fixtures.table_display import metadata_bytes

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def update_fields(previous, before, after):
    old, new = metadata_bytes.records(before), metadata_bytes.records(after)
    assert {key: previous[key] for key in old} == old, (
        'Frozen descriptive values must agree with the independently archived old source'
    )
    assert not (previous.keys() & metadata_bytes.FIELDS) - old.keys(), (
        'Frozen descriptive witnesses must not introduce an undeclared old field'
    )
    retained = {key: value for key, value in previous.items() if key not in old}
    return {**retained, **new}


def adapt(oracle, display, replacements):
    oracle, display = copy.deepcopy(oracle), copy.deepcopy(display)

    def source(name, expected):
        if name not in replacements:
            return expected, None
        before, after = replacements[name]
        metadata_bytes.records(before)
        metadata_bytes.records(after)
        assert metadata_bytes.remainder(before) == metadata_bytes.remainder(after), (
            'Descriptive oracle adaptation must retain every non-descriptive source byte'
        )
        if expected == digest(after):
            return expected, (after, after)
        assert expected == digest(before), (
            'A source hash adaptation must start at the exact independently frozen bytes'
        )
        return digest(after), (before, after)

    for row in oracle['corpus']:
        name = row['project'] + '/experiments/' + row['experiment'] + '.edi'
        row['sha256'], pair = source(name, row['sha256'])
        if pair is not None:
            row['scalars'] = update_fields(row['scalars'], *pair)
    for project in oracle['projects']:
        for relative, previous in project['files'].items():
            name = project['path'] + '/' + relative
            project['files'][relative], pair = source(name, previous)
            if pair is not None and relative in {'project.edi', 'analysis/analysis.edi'}:
                group = 'metadata' if relative == 'project.edi' else 'analysis'
                project[group] = update_fields(project[group], *pair)
    for name, previous in display['sources'].items():
        display['sources'][name], _ = source(name, previous)
    return oracle, display


def read(path):
    return json.loads(path.read_text().split('var frozen = ', 1)[1].removesuffix(';\n'))


def generate():
    pins = json.loads((metadata_bytes.HERE / 'metadata-inputs.json').read_text())['files']
    replacements = {}
    for name in pins:
        before, after = metadata_bytes.pair(name)
        assert (ROOT / name).read_bytes() == after, (
            'Descriptive fixture generation must observe the entire archived current input'
        )
        replacements[name] = before, after
    oracle, display = adapt(
        read(HERE / 'oracle.js'), read(HERE / 'display_oracle.js'), replacements
    )
    for name, data in [('oracle.js', oracle), ('display_oracle.js', display)]:
        (HERE / name).write_text(
            '// Independent source oracle; descriptive updates use adapt_descriptive_inputs.py.\n'
            'var frozen = '
            + json.dumps(data, indent=2, ensure_ascii=name == 'display_oracle.js')
            + ';\n'
        )


if __name__ == '__main__':
    generate()
