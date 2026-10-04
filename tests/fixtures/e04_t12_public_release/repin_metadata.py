"""Re-pin descriptive-only fixture edits against an explicit committed pre-edit tree.

No scientific values or product outputs are regenerated. Every changed input must
be exactly the lexical process-prose adaptation of its retained original bytes.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from adapt_test_metadata import payload

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def public_source_labels(revision, previous):
    """Keep every observation and upstream pin while replacing only a source URL's label."""
    for relative, keys in [
        ('tests/fixtures/c11_t4_cw_selection/manifest.json', ('provenance', 'repository')),
        ('tests/fixtures/c34_t23_cli_projects/source-objects.json', ('source',)),
    ]:
        before = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'show',
            revision + ':' + relative,
        ])
        prior = hashlib.sha256(before).hexdigest()
        retained = previous.get(relative, {})
        expected = json.loads(before)
        parent = expected
        for key in keys[:-1]:
            parent = parent[key]
        if parent[keys[-1]] != 'https://github.com/enhantica/c' + 'rysta':
            raise ValueError('only the declared producer source URL may receive a public label')
        parent[keys[-1]] = 'crysta'
        after = (json.dumps(expected, indent=2) + '\n').encode()
        current = hashlib.sha256(after).hexdigest()
        if retained and retained['after_sha256'] not in {prior, current}:
            raise ValueError('the source-label revision must reproduce the retained adaptation')
        if (ROOT / relative).read_bytes() != after:
            raise ValueError('the source-label edit changed fields beyond descriptive provenance')
        previous[relative] = {
            'before_sha256': retained.get('before_sha256', prior),
            'after_sha256': current,
        }
    (HERE / 'fixture-metadata.json').write_text(
        json.dumps(previous, indent=2, sort_keys=True) + '\n'
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--public-source-labels', action='store_true')
    args = parser.parse_args()
    record_path = HERE / 'fixture-metadata.json'
    previous = json.loads(record_path.read_text()) if record_path.exists() else {}
    if args.public_source_labels:
        public_source_labels(args.revision, previous)
        return
    records = {}

    def identity(relative, expected=None):
        path = ROOT / relative
        before = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'show',
            args.revision + ':' + relative,
        ])
        after = path.read_bytes()
        prior = hashlib.sha256(before).hexdigest()
        retained = previous.get(relative, {})
        if retained and retained['before_sha256'] != prior:
            raise ValueError(
                'the explicit authoring revision must retain the original fixture identity'
            )
        if expected is not None and expected not in {prior, retained.get('after_sha256')}:
            raise ValueError(
                'original fixture must reproduce its independent pre-edit pin: ' + relative
            )
        if payload(before.decode(), relative).encode() != after:
            raise ValueError(
                'fixture changes exceed lexical descriptive-only adaptation: ' + relative
            )
        current = hashlib.sha256(after).hexdigest()
        records[relative] = {'before_sha256': prior, 'after_sha256': current}
        return current

    def update(relative, fields):
        path = ROOT / relative
        doc = json.loads(path.read_text())
        for keys, target in fields:
            parent = doc
            for key in keys[:-1]:
                parent = parent[key]
            parent[keys[-1]] = identity(target, parent[keys[-1]])
        path.write_text(json.dumps(doc, indent=2) + '\n')

    for directory in ('c09_t12_silicon_fit', 'c12_t3_space_group_code'):
        fields = [
            (
                ('silicon', 'structure_sha256'),
                'tests/fixtures/c12_t3_space_group_code/si_origin_2.edi',
            )
        ]
        if directory == 'c09_t12_silicon_fit':
            fields.append((
                ('provenance', 'generator_sha256'),
                'tests/fixtures/c09_t12_silicon_fit/direct_crysta_oracle.cpp',
            ))
        update('tests/fixtures/' + directory + '/oracle.json', fields)
    relative = 'tests/fixtures/e02_t2_ncaf_5bank/manifest.json'
    doc = json.loads((ROOT / relative).read_text())
    update(
        relative,
        [(('files', name), 'tests/fixtures/e02_t2_ncaf_5bank/' + name) for name in doc['files']],
    )
    identity(
        'tests/fixtures/c11_t4_cw_selection/manifest.json',
        '6633f325680b478194eccc76335f55e59b64c84b5d7043561b18ee106f40e095',
    )
    (HERE / 'fixture-metadata.json').write_text(
        json.dumps(records, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
