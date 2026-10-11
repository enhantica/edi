"""Project stored keys onto the retained ordinal writer regression witnesses.

Before mapping a single key, require the saved keys to equal the supplied input
in row order. Every separator, column, numerical value and other byte survives.
Only line-segment background and exclusion rows changed identity ownership.
"""

import re
import shlex
import shutil

from tests.fixtures.cwl_family.historical import current_tokens


def rows(data):
    data = current_tokens(data)
    lines = data.splitlines(keepends=True)
    groups = {}
    offset = 0
    index = 0
    while index < len(lines):
        if lines[index].strip() != b'loop_':
            offset += len(lines[index])
            index += 1
            continue
        offset += len(lines[index])
        index += 1
        tags = []
        while index < len(lines) and lines[index].strip().startswith(b'_'):
            tag = lines[index].strip()
            if len(tag.split()) != 1:
                break
            tags.append(tag)
            offset += len(lines[index])
            index += 1
        category = next(
            (
                kind
                for kind, value in (
                    ('background', b'_background.position'),
                    ('excluded_region', b'_excluded_region.start'),
                )
                if value in tags
            ),
            None,
        )
        if category is None:
            continue
        key = ('_' + category + '.id').encode()
        assert key in tags and category not in groups, (
            'Stored-key mapping requires exactly one declared identity column per category'
        )
        column = tags.index(key)
        values = []
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                offset += len(line)
                index += 1
                continue
            if line.lstrip().startswith((b'_', b'loop_', b'data_', b'#')):
                break
            cells = list(re.finditer(rb"'[^']*'|\"[^\"]*\"|\S+", line))
            assert len(cells) == len(tags), (
                'Stored-key mapping must reach complete rows without dropping any scientific cell'
            )
            cell = cells[column]
            decoded = shlex.split(cell[0].decode())
            assert len(decoded) == 1, 'A stored row key must decode to exactly one supplied value'
            values.append((decoded[0], offset + cell.start(), offset + cell.end()))
            offset += len(line)
            index += 1
        groups[category] = values
    return data, groups


def ordinal_copy(source, saved, destination):
    shutil.copytree(saved, destination)
    for path in (saved / 'experiments').glob('*.edi'):
        input_path = source / 'experiments' / path.name
        assert input_path.is_file(), 'A saved stored-key witness must retain its input experiment'
        _, supplied = rows(input_path.read_bytes())
        data, written = rows(path.read_bytes())
        for category, entries in written.items():
            expected = [entry[0] for entry in supplied.get(category, ())]
            assert [entry[0] for entry in entries] == expected, (
                'Every saved stored key must equal its supplied input key in unchanged row order'
            )
        assert written.keys() == supplied.keys(), (
            'Stored-key mapping cannot add or remove an input row category'
        )
        edits = [
            (start, end, str(index).encode())
            for entries in written.values()
            for index, (_, start, end) in enumerate(entries, 1)
        ]
        for start, end, value in sorted(edits, reverse=True):
            data = data[:start] + value + data[end:]
        (destination / 'experiments' / path.name).write_bytes(data)
    return destination
