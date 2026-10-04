"""Adapt merged descriptive metadata from an explicit committed pre-edit tree.

Keep numeric FullProf artifacts and published element values exact. Re-pin only
local artifacts whose prose changes; upstream source digests remain provenance.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from adapt_test_metadata import payload
from scrub_fixture_metadata import portable

ROOT = Path(__file__).resolve().parents[3]
FILES = (
    'tests/fixtures/c13_t6_background/PROVENANCE.md',
    'tests/fixtures/c13_t6_background/declarations.py',
    'tests/fixtures/c13_t6_background/freeze_cli_bounds.py',
    'tests/fixtures/c13_t6_background/generate.py',
    'tests/fixtures/c13_t6_background/pearl.dat',
    'tests/fixtures/c13_t6_background/project.py',
    'tests/fixtures/e04_t1/README.md',
    'tests/fixtures/e04_t10/README.md',
    'tests/fixtures/e04_t10/generate.py',
    'tests/fixtures/e04_t10/generated.hpp',
    'tests/unit/cpp/test_e04_t10_scene.cpp',
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    changes = {}
    output = ROOT / 'tests/fixtures/e04_t12_public_release/merged-metadata.json'
    previous = json.loads(output.read_text()) if output.exists() else {}

    def original(name):
        return subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'show',
            args.revision + ':' + name,
        ])

    def record(name, before, after):
        current = (ROOT / name).read_bytes()
        retained = previous.get(name, {})
        retained_after = (
            retained.get('after_sha256')
            if retained.get('before_sha256') == digest(before)
            else None
        )
        if current not in {before, after} and digest(current) != retained_after:
            raise ValueError('refusing unrelated uncommitted fixture changes: ' + name)
        if before != after:
            changes[name] = {'before_sha256': digest(before), 'after_sha256': digest(after)}
            (ROOT / name).write_bytes(after)

    for name in FILES:
        before = original(name)
        text = payload(portable(before, name).decode(), name)
        # The generic adapter protects the whole native case declaration. This
        # macro also carries a requirement message, whose prose is not its name.
        text = text.replace(
            '"' + 'E04' + '-T10 accepted scene API is absent on the pre-implementation tree"',
            '"accepted scene API is absent on the pre-implementation tree"',
        )
        if name.endswith('/generate.py') and 'background' in name:
            text = text.replace('{args.fp2k}', '{args.fp2k.name}')
        if name.endswith('.md'):
            text = text.replace('#  independent', '# Independent')
            text = text.replace(
                '\n extends the category', '\nThe background declarations extend the category'
            )
            text = text.replace("crysta's  space-group oracle", "crysta's space-group oracle")
            text = text.replace(
                'specified by  I4 and I5', 'specified by the structure-scene design'
            )
            text = text.replace('<author-runs>/-fullprof-fixed/', '<author-runs>/fullprof-fixed/')
        if name.endswith('.dat'):
            text = text.replace('ralf_to_xydata.py ();', 'ralf_to_xydata.py;')
        after = text.encode()
        if name.endswith('.dat'):
            # Numeric records and all non-header content retain exact bytes.
            def numeric(raw):
                return [line for line in raw.splitlines() if re.match(rb'\s*[+-]?[0-9.]', line)]

            if numeric(before) != numeric(after):
                raise ValueError('descriptive adaptation changed measured observations')
        record(name, before, after)

    name = 'tests/fixtures/c13_t6_background/reference.json'
    before = original(name)
    doc = json.loads(before)
    for row in doc['cases'].values():
        row['command'] = portable(row['command'].encode(), name).decode()
        for filename, pin in row['sha256'].items():
            relative = 'tests/fixtures/c13_t6_background/' + filename
            if digest(original(relative)) != pin:
                raise ValueError(
                    'original artifact does not reproduce its independent pin: ' + filename
                )
            current = (ROOT / relative).read_bytes()
            expected = changes.get(relative, {}).get('after_sha256', pin)
            if digest(current) != expected:
                raise ValueError('artifact changed beyond descriptive adaptation: ' + filename)
            row['sha256'][filename] = expected
    record(name, before, (json.dumps(doc, indent=2) + '\n').encode())
    output.write_text(json.dumps(changes, indent=2, sort_keys=True) + '\n')
    print(f'{len(changes)} descriptive adaptations; original and adapted identities retained')


if __name__ == '__main__':
    main()
