"""Capture layout metadata while retaining every historical output byte pin."""

import argparse
import collections
import hashlib
import json
import re
import zipfile
from pathlib import Path

from tests.fixtures.project_categories.historical_bytes import layout, units

ROOT = Path(__file__).resolve().parents[3]


def description_value(unit):
    text = unit.decode()
    value = text[len('_metadata.description') :].strip()
    if value.startswith('"'):
        decoded = json.loads(value)
    else:
        lines = text.splitlines()
        if lines[:2] != ['_metadata.description', ';'] or lines[-1] != ';':
            raise ValueError('A description must use the declared semicolon spelling')
        if any(len(line) > 80 or line.startswith(';') for line in lines[2:-1]):
            raise ValueError('Description lines must obey the text-record width and delimiter')
        decoded = '\n'.join(lines[2:-1])
    return '\n\n'.join(' '.join(paragraph.splitlines()) for paragraph in decoded.split('\n\n'))


def text_changes(old, new):
    old_units, new_units = units(old)[1], units(new)[1]
    removed = list((collections.Counter(old_units) - collections.Counter(new_units)).elements())
    added = list((collections.Counter(new_units) - collections.Counter(old_units)).elements())
    if len(removed) != len(added):
        raise ValueError('Text adaptation cannot add or remove a declaration')
    changes = []
    for key, before in removed:
        matches = [after for name, after in added if name == key]
        if len(matches) != 1:
            raise ValueError('Text adaptation requires one matching item')
        after = matches[0]
        if key == b'_metadata.description':
            quoted = before.decode().split(None, 1)[1].strip()
            if not quoted.startswith('"'):
                raise ValueError('Only the recorded quoted description form may be projected')
            value = json.loads(quoted)
            if len(before.decode().rstrip('\n')) <= 80 and '\n' not in value and '"' not in value:
                raise ValueError('The description must meet a declared multiline-format trigger')
            if description_value(before) != description_value(after):
                raise ValueError('Description spelling cannot change its paragraphs')
        elif key == b'_metadata.timestamp':
            if before.count(b'\n\n#') != 1 or before.replace(b'\n\n#', b'\n#', 1) != after:
                raise ValueError('Only the recorded separator before a retained comment may move')
        else:
            raise ValueError('Unexplained payload change: ' + key.decode())
        changes.append({'key': key.decode(), 'before_hex': before.hex(), 'after_hex': after.hex()})
    return changes


def record_text_transitions(record, pins, directory, observed):
    transitions = dict(record.get('text_unit_transitions', {}))
    entries = [
        (group, index, rule, files['project.edi'])
        for group in ['projects', 'fit_projects']
        for index, rules in enumerate(pins[group].values())
        for rule, files in rules.items()
        if 'project.edi' in files
    ]
    for group, index, rule, digest in entries:
        old = (directory / (digest + '.edi')).read_bytes()
        new = (observed / group / str(index) / rule / 'saved/project.edi').read_bytes()
        new = re.sub(
            rb'(?m)^(_metadata\.(?:created|last_modified)[ \t]+)[^\r\n]+', rb'\1<CLOCK>', new
        )
        changes = text_changes(old, new)
        if changes:
            transitions[digest] = changes
    record['text_unit_transitions'] = transitions


def append_pinned_layouts(directory, observed):
    pins_path = ROOT / 'tests/fixtures/fittability/saved-main.json'
    pins = json.loads(pins_path.read_text())
    expected = {
        digest
        for group in ['projects', 'fit_projects']
        for rules in pins[group].values()
        for files in rules.values()
        for name, digest in files.items()
        if name.endswith('.edi')
    }
    target = Path(__file__).with_name('historical-layouts.json')
    record = json.loads(target.read_text())
    entries = list(record['layouts'])
    indices = {json.dumps(row, sort_keys=True): i for i, row in enumerate(entries)}
    pin_indices = dict(record.get('pin_layout_indices', {}))
    found = set()
    for path in sorted(directory.glob('*.edi')):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest not in expected:
            raise ValueError(
                'Every captured file must reproduce an immutable EDI pin: ' + str(path)
            )
        row = layout(data)
        key = json.dumps(row, sort_keys=True)
        if key not in indices:
            indices[key] = len(entries)
            entries.append(row)
        pin_indices[digest] = indices[key]
        found.add(digest)
    if found != expected:
        raise ValueError('Missing historical EDI pins: ' + repr(sorted(expected - found)))
    record['layouts'] = entries
    record['pin_layout_indices'] = pin_indices
    record_text_transitions(record, pins, directory, observed)
    record['fittability_pins_sha256'] = hashlib.sha256(pins_path.read_bytes()).hexdigest()
    target.write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?')
    parser.add_argument('--revision')
    parser.add_argument('--fittability-pinned-files', type=Path)
    parser.add_argument('--observed-saves', type=Path)
    args = parser.parse_args()
    if args.fittability_pinned_files:
        if args.source is not None or args.revision is not None:
            parser.error('Pinned-file capture and inherited-layout capture are separate modes')
        if args.observed_saves is None:
            parser.error('--observed-saves is required with the pinned files')
        append_pinned_layouts(args.fittability_pinned_files, args.observed_saves)
        return
    if args.source is None or args.revision is None:
        parser.error('source and --revision are required for inherited-layout capture')
    inherited = json.loads(args.source.read_text())['layouts']
    documents = [p.read_bytes() for p in (ROOT / 'tests/fixtures').rglob('*.edi')]
    for name in ('c13_t12_ids/baseline.zip', 'table_display/regression-inputs.zip'):
        with zipfile.ZipFile(ROOT / 'tests/fixtures' / name) as archive:
            documents.extend(archive.read(p) for p in archive.namelist() if p.endswith('.edi'))
    entries = [*inherited, *(layout(data) for data in documents)]
    record = {
        'source_revision': args.revision,
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'source': 'frozen category layout reference',
        'layouts': list({json.dumps(row, sort_keys=True): row for row in entries}.values()),
    }
    Path(__file__).with_name('historical-layouts.json').write_text(
        json.dumps(record, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
