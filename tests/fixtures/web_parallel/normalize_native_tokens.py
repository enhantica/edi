"""Remove NumPy scalar repr wrappers from frozen native tokens without changing values."""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRAPPED = re.compile(r'np\.float64\(([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\)')


def digest(scientific):
    return hashlib.sha256(json.dumps(scientific, sort_keys=True).encode()).hexdigest()


def normalize(case):
    path = HERE / (case + '-native.json')
    source = json.loads(path.read_text())
    if 'token_encoding' in source:
        return
    previous = digest(source['scientific'])
    changes = []
    for document, rows in source['scientific'].items():
        for row_index, row in enumerate(rows):
            for column, token in enumerate(row):
                matched = WRAPPED.fullmatch(token)
                if matched:
                    value = matched[1]
                    changes.append([document, row_index, column, token, value])
                    row[column] = value
    if not changes:
        return
    source['token_encoding'] = {
        'rule': 'Remove only np.float64(...) around a finite decimal; retain its exact digits',
        'previous_scientific_sha256': previous,
        'changes': changes,
    }
    conditioning_path = HERE / (case + '-conditioning.json')
    conditioning = json.loads(conditioning_path.read_text())
    if conditioning['scientific_sha256'] != previous:
        message = 'The unchanged native conditioning must belong to the original scientific bytes'
        raise RuntimeError(message)
    conditioning['scientific_sha256'] = digest(source['scientific'])
    path.write_text(json.dumps(source, indent=2) + '\n')
    conditioning_path.write_text(json.dumps(conditioning, indent=2) + '\n')
    print(case, len(changes), 'representation-only tokens normalized')


if __name__ == '__main__':
    for case in ['lbco', 'ncaf']:
        normalize(case)
