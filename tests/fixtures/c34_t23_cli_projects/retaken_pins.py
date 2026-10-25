"""Retain old seed checks after four exact source regression-pin changes.

These are source-byte witnesses, not independent scientific references.
The catalogue rework replaces these four pins when it merges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BEFORE = 'b761fdf6'
AFTER = '90e17741'
UPSTREAM = 'b339d832'
SEEDS = frozenset({'ncaf-wish-2bank-s3', 'ncaf-wish-3bank-s5', 'si-sepd-s2', 'si-sepd-s5'})


def content_id(raw):
    return hashlib.sha1(
        b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False
    ).hexdigest()


def retained_pin_bytes(project_id, raw):
    rows = json.loads((HERE / 'retaken-pins.json').read_text())['seeds']
    assert set(rows) == SEEDS, 'The temporary pin adaptation covers exactly four named seeds'
    row = rows[project_id]
    before, after = (row[key].encode() for key in ('before_text', 'after_text'))
    assert content_id(before) == row['before_blob'], (
        'The archived prior regression pin must retain its complete source identity'
    )
    assert content_id(after) == row['after_blob'], (
        'The re-taken regression pin must retain its complete reviewed source identity'
    )
    assert raw == after, 'A re-taken pin must equal every reviewed source byte'
    old, new = json.loads(before), json.loads(after)
    changes = []

    def compare(left, right, trail=()):
        if isinstance(left, dict):
            assert isinstance(right, dict) and left.keys() == right.keys(), (
                'Re-taken pins must retain every quantity, run and field'
            )
            for key in left:
                compare(left[key], right[key], (*trail, key))
        elif isinstance(left, list):
            assert isinstance(right, list) and len(left) == len(right), (
                'Re-taken pins must retain every ordered source item'
            )
            for index, (a, b) in enumerate(zip(left, right, strict=True)):
                compare(a, b, (*trail, index))
        elif left != right:
            assert trail[-2:] in {
                ('reduced_chi_square', 'value'),
                ('rwp', 'value'),
            }, 'Only the reviewed fit regression values may change'
            parent = old
            for key in trail[:-1]:
                parent = parent[key]
            assert parent['kind'] == 'regression-pin', (
                'The seed adaptation must never change an independent reference value'
            )
            changes.append('/'.join(map(str, trail)))

    compare(old, new)
    assert sorted(changes) == row['changed_values'], (
        'The source adaptation must change exactly the independently reviewed value paths'
    )
    return before


def changed_paths(left, right, trail=()):
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        return [
            path for key in left for path in changed_paths(left[key], right[key], (*trail, key))
        ]
    return [] if left == right else ['/'.join(map(str, trail))]


def source_bytes(commit, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + path])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', required=True)
    parser.parse_args()
    projects = json.loads((HERE / 'project-ids.json').read_text())['source_to_project']
    result = {}
    for seed in sorted(SEEDS):
        path = 'docs/user/cli/' + projects[seed] + '/expected.json'

        before, after = source_bytes(BEFORE, path), source_bytes(AFTER, path)
        assert after == source_bytes(UPSTREAM, path), (
            'The temporary source pins must be byte-identical to the reviewed upstream commit'
        )
        old, new = json.loads(before), json.loads(after)
        changes = changed_paths(old, new)
        result[seed] = {
            'path': path,
            'before_blob': content_id(before),
            'after_blob': content_id(after),
            'before_text': before.decode(),
            'after_text': after.decode(),
            'changed_values': sorted(changes),
        }
    destination = HERE / 'retaken-pins.json'
    destination.write_text(
        json.dumps(
            {
                'claim': 'Exact source regression pins; no independent correctness claim',
                'before': BEFORE,
                'after': AFTER,
                'upstream': UPSTREAM,
                'replacement': 'The catalogue rework replaces these four pins when it merges.',
                'seeds': result,
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )
    for seed, row in result.items():
        retained_pin_bytes(seed, row['after_text'].encode())


if __name__ == '__main__':
    main()
