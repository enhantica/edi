"""Canonicalize free flags on the three x,x,x sites in the NCAF fixtures."""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITES = {'Al1', 'Na1', 'F3'}


def canonicalize(text):
    result = []
    seen = set()
    for original_line in text.splitlines(keepends=True):
        line = original_line
        tokens = list(re.finditer(r'\S+', line))
        if tokens and tokens[0][0] in SITES:
            name = tokens[0][0]
            if name in seen or len(tokens) < 6 or '(' not in tokens[2][0]:
                message = 'NCAF cleanup requires one row per declared site and a free x leader'
                raise ValueError(message)
            seen.add(name)
            coordinates = [re.sub(r'\([^)]*\)', '', tokens[index][0]) for index in (2, 3, 4)]
            if tokens[5][0] != 'a' or len(set(map(Decimal, coordinates))) != 1:
                message = 'NCAF follower cleanup requires an x,x,x site on Wyckoff a'
                raise ValueError(message)
            for index in (4, 3):
                token = tokens[index]
                line = line[: token.start()] + coordinates[index - 2] + line[token.end() :]
        result.append(line)
    if seen != SITES:
        message = 'NCAF follower cleanup must find all three declared sites'
        raise ValueError(message)
    return ''.join(result)


def main():
    fixture = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank'
    structure = fixture / 'project/structures/ncaf.edi'
    before = structure.read_bytes()
    structure.write_text(canonicalize(before.decode()))
    manifest_path = fixture / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files']['project/structures/ncaf.edi'] = hashlib.sha256(
        structure.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(
        'canonical fixture:',
        hashlib.sha256(before).hexdigest(),
        '->',
        manifest['files']['project/structures/ncaf.edi'],
    )


if __name__ == '__main__':
    main()
