"""Bind older retained fixtures to the exact committed stricter stop-rule retake."""

import argparse
import hashlib
import json
from pathlib import Path

from tests.fixtures.example_catalogue.capture_adaptations import committed, reference_rows

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
AFTER = '198fa5775'


def require_pin_values_only(old, new, path=(), *, original=None):
    original = old if original is None else original
    if isinstance(old, dict) and isinstance(new, dict):
        assert old.keys() == new.keys(), 'A retained re-pin must preserve its complete schema'
        for key in old:
            require_pin_values_only(old[key], new[key], (*path, key), original=original)
    elif old != new:
        owner = original
        for key in path[:-1]:
            owner = owner[key]
        assert path[-1] == 'value' and owner.get('kind') == 'regression-pin', (
            'Only explicitly labelled regression values may change in a retained stop-rule pin'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', required=True)
    selected = set(parser.parse_args().only)
    target = HERE / 'retention-adaptations.json'
    document = json.loads(target.read_text())
    inventory = json.loads((HERE / 'retained-projects.json').read_text())
    assert selected <= {row['id'] for row in inventory['projects']}, (
        'Every scoped stop-rule transition must name a retained original fixture'
    )
    count = 0
    for case in inventory['projects']:
        if case['id'] not in selected:
            continue
        path = 'docs/user/cli/' + case['id'] + '/expected.json'
        original = committed(inventory['source'], path)
        assert hashlib.sha256(original).hexdigest() == case['sha256']['expected.json'], (
            'The adaptation must bind the exact immutable retained expected file'
        )
        after = committed(AFTER, path)
        row = document['files'].get(path)
        assert (ROOT / path).read_bytes() == after, (
            'The source replacement must still equal the committed stricter stop-rule retake'
        )
        if after == original:
            if row is not None:
                del document['files'][path]
                count += 1
            continue  # Exact original bytes need no reversal through an intermediate pin.
        if (
            row is not None
            and row['before_sha256'] == case['sha256']['expected.json']
            and row['after_sha256'] == hashlib.sha256(after).hexdigest()
        ):
            continue
        old, new = json.loads(original), json.loads(after)
        assert reference_rows(old) == reference_rows(new), (
            'Retained stop-rule transitions preserve every independent reference and tolerance: '
            + path
        )
        require_pin_values_only(old, new)
        document['files'][path] = {
            'source_commit': AFTER,
            'reason': 'Stricter Shift/s.u. retake; original retained regression values only',
            'before_sha256': hashlib.sha256(original).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before': original.decode(),
            'after': after.decode(),
        }
        count += 1
    target.write_text(json.dumps(document, indent=2) + '\n')
    print('Exact immutable retained stop-rule endpoints advanced:', count)


if __name__ == '__main__':
    main()
