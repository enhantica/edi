"""Retain the historical catalogue and record exact new row-membership contexts."""

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    spec = importlib.util.spec_from_file_location(
        'source_scan', ROOT / 'tests/system/py/project_output_source_scan.py'
    )
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    path = ROOT / 'tests/fixtures/project_output/non_project_operations.json'
    rows = [
        row
        for row in json.loads(path.read_text())
        if not row['name'].startswith('Single-crystal row membership:')
    ]
    original = json.dumps(rows, indent=2) + '\n'
    if (
        hashlib.sha256(original.encode()).hexdigest()
        != '7ddd266f8228a6e6c034d5e37d0b392faad08d0a0b4ecee7a0dfdf0ed4979dff'
    ):
        raise ValueError('The complete historical operation catalogue must stay unchanged')
    source_name = 'core/include/edi/model.hpp'
    source = (ROOT / source_name).read_text()
    atoms = scan.cpp_tokens(source)
    allowed = set()
    for row in rows:
        if row['source'] != source_name:
            continue
        context = scan.cpp_tokens(row['context'])
        matches = [
            i + row['offset']
            for i in range(len(atoms) - len(context) + 1)
            if atoms[i : i + len(context)] == context
        ]
        allowed.update(matches[: row['limit']])
    added = []
    for index, atom in scan.cpp_violations(source, sites=True):
        if index in allowed:
            continue
        if atom not in {'link', 'unlink'} or '.row.' not in ''.join(atoms[index - 6 : index]):
            raise ValueError('An unreviewed operation cannot become a membership exception')
        start = max(0, index - 8)
        added.append({
            'name': 'Single-crystal row membership: ' + atom + ' ' + str(index),
            'source': source_name,
            'context': ' '.join(atoms[start : index + 9]),
            'offset': index - start,
            'limit': 1,
        })
    if len(added) != 4:
        raise ValueError('Only the four reviewed membership contexts belong to this extension')
    path.write_text(json.dumps(rows + added, indent=2) + '\n')
    (Path(__file__).parent / 'membership-extensions.json').write_text(
        json.dumps(added, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
