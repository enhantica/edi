"""Retain old fit-state byte witnesses across the declared row-id migration.

Only fit-state key tokens change. Input ids and row order determine each key;
all numerical cells, separators and other bytes remain under the old hash.
"""

import re
import shlex


def _loops(data):
    lines = data.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        if lines[index].strip() != b'loop_':
            index += 1
            continue
        index += 1
        tags = []
        while index < len(lines) and lines[index].strip().startswith(b'_'):
            tags.append(lines[index].strip().decode())
            index += 1
        rows = []
        while index < len(lines) and not lines[index].lstrip().startswith((
            b'_',
            b'loop_',
            b'data_',
        )):
            line = lines[index]
            if line.strip() and not line.lstrip().startswith(b'#'):
                values = shlex.split(line.decode(), comments=True)
                assert len(values) == len(tags), (
                    'Historical fit-state mapping requires complete input rows'
                )
                rows.append(dict(zip(tags, values, strict=True)))
            index += 1
        yield tags, rows


def _identity_pairs(source):
    pairs = {}
    for path in (source / 'experiments').glob('*.edi'):
        data = path.read_bytes()
        block = next(
            token[5:] for token in shlex.split(data.decode()) if token.startswith('data_')
        )
        for tags, rows in _loops(data):
            if '_background.position' in tags or '_background.coef' in tags:
                for index, row in enumerate(rows):
                    identity = row.get('_background.id', str(index + 1))
                    pairs[f'{block}.background[{index}]'] = f'{block}.background.{identity}'
            if '_linked_structure.structure_id' in tags and len(rows) == 1:
                for field in ('scale', 'march_r', 'march_random_fract'):
                    pairs[f'{block}.{field}'] = (
                        f'{block}.' + rows[0]['_linked_structure.structure_id'] + f'.{field}'
                    )
    return pairs


def historical_fit_ids(source, saved):
    original = source / 'analysis/analysis.edi'
    if not original.is_file():
        return saved
    source_keys = [
        row['_fit_parameter.id']
        for tags, rows in _loops(original.read_bytes())
        if '_fit_parameter.id' in tags
        for row in rows
    ]
    if not source_keys:
        return saved
    pairs = _identity_pairs(source)
    historical = {current: previous for previous, current in pairs.items()}
    old_keys = [historical.get(key, key) for key in source_keys]
    new_keys = [pairs.get(key, key) for key in source_keys]
    assert len(set(new_keys)) == len(new_keys), (
        'Every archived fit-state key must retain a distinct input-derived identity'
    )
    reverse = dict(zip(new_keys, old_keys, strict=True))
    lines = saved.splitlines(keepends=True)
    held = False
    seen = []
    for index, line in enumerate(lines):
        if line.strip() == b'_fit_parameter.id':
            assert not held and not seen, 'Only one fit-state identity loop may be projected'
            held = True
        elif held and line.lstrip().startswith((b'loop_', b'data_')):
            held = False
        elif held and line.strip() and not line.lstrip().startswith((b'_', b'#')):
            match = re.match(rb"(?:'[^']*'|\"[^\"]*\"|\S+)", line)
            assert match, 'A fit-state row must retain its key cell'
            key = shlex.split(match[0].decode())[0]
            seen.append(key)
            assert key in reverse, 'Saved fit-state identities must come from the complete input'
            lines[index] = reverse[key].encode() + line[match.end() :]
    assert seen == new_keys, (
        'Saved fit-state keys must match every input-derived id in unchanged row order'
    )
    return b''.join(lines)
