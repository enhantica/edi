"""Project the checked unity column onto the retained pre-column byte pins."""

import re

COLUMN = b'_linked_structure.weight_fraction\n'
TOKEN = re.compile(rb"'[^']*'|\"[^\"]*\"|[^\s]+")
LOOP = re.compile(rb'(?m)^loop_\n((?:_linked_structure\.[^\n]+\n)+)((?:[^\n]+\n)+)')


def historical_single_fraction(name, data):
    if not (name.startswith('experiments/') and name.endswith('.edi')):
        return data

    def restore(match):
        headers = match[1].splitlines(keepends=True)
        rows = match[2].splitlines(keepends=True)
        tags = [tag.strip() for tag in headers]
        cells = [TOKEN.findall(row) for row in rows]
        assert all(len(row) == len(tags) for row in cells), (
            'Unity-column adaptation requires every original linked row and column'
        )
        enabled = (
            tags.index(b'_linked_structure.enabled')
            if b'_linked_structure.enabled' in tags
            else None
        )
        active = [enabled is None or row[enabled] == b'true' for row in cells]
        if sum(active) > 1:
            return match[0]
        assert headers.count(COLUMN) == 1, 'Exactly one fraction column must be written'
        assert headers[-1] == COLUMN, (
            'Before: no fraction column; after: exactly one trailing unity column is required'
        )
        assert tags[:-1] == [b'_linked_structure.structure_id', b'_linked_structure.scale'] + (
            [b'_linked_structure.enabled'] if enabled is not None else []
        ), 'Unity-column adaptation must retain exactly the original linked columns in order'
        output = []
        for row, fields, participating in zip(rows, cells, active, strict=True):
            wanted = b'1.0' if participating else b'.'
            assert fields[-1] == wanted, (
                'Single enabled links save exactly 1.0 without uncertainty; disabled links save .'
            )
            suffix = b' ' + wanted + b'\n'
            assert row.endswith(suffix), (
                'Unity-column adaptation removes only the canonical new cell separator'
            )
            output.append(row[: -len(suffix)] + b'\n')
        return b'loop_\n' + b''.join(headers[:-1] + output)

    result = LOOP.sub(restore, data)
    assert data.count(COLUMN) == len(LOOP.findall(data)), (
        'Every saved linked loop must carry the fraction column, without orphan declarations'
    )
    return result
