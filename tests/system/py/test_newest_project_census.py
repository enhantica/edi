"""Audit committed project headers without tokenizing observation arrays."""

import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _header_tokens(text):
    kept = []
    data = False
    for line in text.splitlines():
        if line.startswith(('loop_', 'data_', '_')):
            if line.startswith('loop_'):
                data = False
            if line.startswith(('_data.', '_pd_meas.', '_refln.')):
                data = True
            elif line.startswith('_'):
                data = False
        if not data:
            kept.append(line)
    return shlex.split('\n'.join(kept), comments=True)


def _committed_edi_files():
    revision = subprocess.check_output(
        [shutil.which('git'), '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    names = subprocess.check_output(
        [shutil.which('git'), '-C', str(ROOT), 'ls-tree', '-r', '--name-only', revision], text=True
    ).splitlines()
    names = [name for name in names if name.endswith('.edi')]
    assert names, 'The committed-project census must prove a nonempty project inventory'
    result = subprocess.run(
        [shutil.which('git'), '-C', str(ROOT), 'cat-file', '--batch'],
        input=''.join(f'{revision}:{name}\n' for name in names).encode(),
        capture_output=True,
        check=True,
    )
    cursor = 0
    for name in names:
        end = result.stdout.index(b'\n', cursor)
        header = result.stdout[cursor:end].split()
        assert len(header) == 3, (
            'The newest-format census must read each actual committed project blob'
        )
        assert header[1] == b'blob', 'Each committed project must resolve to a readable blob'
        size = int(header[2])
        yield name, result.stdout[end + 1 : end + 1 + size].decode()
        cursor = end + size + 2


def _declared_background_ids(bank_tokens):
    declared = set()
    cursor = 0
    while cursor < len(bank_tokens):
        if bank_tokens[cursor] != 'loop_':
            cursor += 1
            continue
        cursor += 1
        columns = []
        while cursor < len(bank_tokens) and bank_tokens[cursor].startswith('_'):
            columns.append(bank_tokens[cursor])
            cursor += 1
        cells = []
        while cursor < len(bank_tokens) and not bank_tokens[cursor].startswith((
            '_',
            'loop_',
            'data_',
        )):
            cells.append(bank_tokens[cursor])
            cursor += 1
        if '_background.id' in columns:
            offset = columns.index('_background.id')
            declared.update(cells[offset :: len(columns)])
    return declared


def test_every_committed_project_file_has_no_retired_positional_reference():
    retired = re.compile(r'background\[\d+\]|(?:linked_structure|preferred_orientation)\.\d+\.')
    problems = []
    files = dict(_committed_edi_files())
    for name, text in files.items():
        problems.extend((name, line) for line in text.splitlines() if retired.search(line))
        tokens = _header_tokens(text)
        if (
            any(field in tokens for field in ('_background.coef', '_background.position'))
            and '_background.id' not in tokens
        ):
            problems.append((name, 'background rows have no declared ids'))
        if '/analysis/' not in name:
            continue
        project = name.split('/analysis/')[0]
        banks = [
            value for path, value in files.items() if path.startswith(project + '/experiments/')
        ]
        blocks = {
            token[5:]
            for bank in banks
            for token in _header_tokens(bank)
            if token.startswith('data_')
        }
        older_bare = {
            f'{block}.{field}'
            for block in blocks
            for field in ('scale', 'march_r', 'march_random_fract')
        }
        problems.extend((name, token) for token in tokens if token in older_bare)
        for bank in banks:
            bank_tokens = _header_tokens(bank)
            block = next(token[5:] for token in bank_tokens if token.startswith('data_'))
            declared = _declared_background_ids(bank_tokens)
            dotted = re.compile(re.escape(block) + r'\.background\.(\d+)\.(?:coef|intensity)$')
            problems.extend(
                (name, token)
                for token in tokens
                if (match := dotted.fullmatch(token)) and match.group(1) not in declared
            )
    assert not problems, (
        'Every committed project must use current parameter names and declared row ids: '
        + repr(problems[:12])
    )
