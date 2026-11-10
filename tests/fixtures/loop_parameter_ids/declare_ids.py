"""Declare the ids that the previous reader assigned to anonymous background rows.

Only an id column and its one-based ids are inserted. Every supplied numeric
cell, comment, separator and unrelated record remains byte-for-byte unchanged.
"""

import argparse
import shlex
from pathlib import Path


def declare_ids(path):
    lines = path.read_text().splitlines(keepends=True)
    changes = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != 'loop_':
            index += 1
            continue
        start = index + 1
        end = start
        while end < len(lines) and lines[end].strip().startswith('_'):
            end += 1
        tags = [line.strip() for line in lines[start:end]]
        if '_background.id' in tags or not any(
            tag in tags for tag in ('_background.position', '_background.coef')
        ):
            index = end
            continue
        changes.append((start, '_background.id\n'))
        ordinal = 0
        while end < len(lines) and not lines[end].lstrip().startswith(('_', 'loop_', 'data_')):
            if lines[end].strip() and not lines[end].lstrip().startswith('#'):
                if len(shlex.split(lines[end], comments=True)) != len(tags):
                    message = 'Background ids require complete declared input rows: ' + str(path)
                    raise ValueError(message)
                ordinal += 1
                changes.append((end, str(ordinal) + ' '))
            end += 1
        index = end
    for index, prefix in reversed(changes):
        lines[index] = prefix + lines[index]
    if changes:
        path.write_text(''.join(lines))
    return bool(changes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    for path in args.paths:
        declare_ids(path)
