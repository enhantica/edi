"""Author comment/description-only public copies of the imported project seeds.

Retain upstream blob identities and record both complete byte digests. The
serialized physical records are checked unchanged before a copy is rewritten.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from itertools import starmap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROCESS = re.compile(
    r'\b(?:[CE]\d{2}-T\d+[a-z]?(?:/T\d+)?|I-\d{4}|ORG-\d{4}|re[l]ay)\b', re.IGNORECASE
)


def physics(data):
    return [
        line for line in data.splitlines() if not line.lstrip().startswith(('#', '_metadata.'))
    ]


def equal(a, b):
    if isinstance(a, str):
        return a == b or public_prose(a) == b
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(starmap(equal, zip(a, b, strict=True)))
    return a == b


def public_prose(text):
    sys.path.insert(0, str(ROOT / 'tools/public-release'))
    from scrub import scrub_prose  # noqa: PLC0415 - authoring-only tool import

    return scrub_prose(text)


def register_expected_metadata(records):
    source = json.loads(
        (ROOT / 'tests/fixtures/c34_t23_cli_projects/source-objects.json').read_text()
    )
    ids = json.loads((ROOT / 'tests/fixtures/c34_t23_cli_projects/project-ids.json').read_text())[
        'source_to_project'
    ]
    for name, paths in source['projects'].items():
        if 'expected.json' not in paths:
            continue
        target = ROOT / 'docs/user/cli' / ids[name] / 'expected.json'
        after = target.read_bytes()
        digest = hashlib.sha1(
            b'blob ' + str(len(after)).encode() + b'\0' + after, usedforsecurity=False
        ).hexdigest()
        if digest == paths['expected.json'] or target.relative_to(ROOT).as_posix() in records:
            continue
        before = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'cat-file',
            'blob',
            paths['expected.json'],
        ])
        if not equal(json.loads(before), json.loads(after)):
            continue  # Existing feature adaptations have their own independent oracles.
        records[target.relative_to(ROOT).as_posix()] = {
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before_blob': paths['expected.json'],
            'after_blob': digest,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register-upstream-copies', action='store_true')
    args = parser.parse_args()
    record_path = HERE / 'project-metadata.json'
    records = json.loads(record_path.read_text()) if record_path.exists() else {}
    for path in sorted((ROOT / 'docs/user/cli').glob('*/project/**/*')):
        if not path.is_file():
            continue
        try:
            before = path.read_text()
        except UnicodeError:
            continue
        if not PROCESS.search(before):
            continue
        lines = []
        for original_line in before.splitlines(keepends=True):
            line = original_line
            if PROCESS.search(line):
                if path.suffix == '.edi' and not line.lstrip().startswith(('#', '_metadata.')):
                    raise ValueError('process tag in a physical record: ' + str(path))
                line = PROCESS.sub('', line)
                line = re.sub(r'\(\s*idea \d+;\s*(edi ADR-[^)]+)\)', r'(\1)', line)
            lines.append(line)
        after = ''.join(lines)
        if path.suffix == '.edi' and physics(before) != physics(after):
            raise ValueError('public metadata adaptation changed physical records')
        name = path.relative_to(ROOT).as_posix()
        records[name] = {
            'before_sha256': hashlib.sha256(before.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(after.encode()).hexdigest(),
            'before_blob': hashlib.sha1(
                b'blob ' + str(len(before.encode())).encode() + b'\0' + before.encode(),
                usedforsecurity=False,
            ).hexdigest(),
            'after_blob': hashlib.sha1(
                b'blob ' + str(len(after.encode())).encode() + b'\0' + after.encode(),
                usedforsecurity=False,
            ).hexdigest(),
        }
        path.write_text(after)
    if args.register_upstream_copies:
        register_expected_metadata(records)
    record_path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
