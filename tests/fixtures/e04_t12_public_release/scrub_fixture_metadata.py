"""Author-time portable provenance adaptation; never regenerate numeric references.

Run with the pinned Python; --report records every file and archive member digest
before and after. Original upstream digests remain provenance; local byte pins
follow only the exact metadata edits below.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = (
    'tests/fixtures/c09_t6_ncaf_5bank_absorption/key_absent_project/structures/ncaf.edi',
    'tests/fixtures/c09_t6_ncaf_5bank_absorption/type_none_project/structures/ncaf.edi',
    'tests/fixtures/c11_t62/README.md',
    'tests/fixtures/c11_t62/scan-inputs.json',
    'tests/fixtures/c13_t12_ids/README.md',
    'tests/fixtures/c15_t2_polarization/manifest.json',
    'tests/fixtures/c34_t25_fullprof/README.md',
    'tests/fixtures/c34_t25_fullprof/freeze_pearl_authoring.py',
    'tests/fixtures/e02_t2_ncaf_5bank/published_cod_1000236.cif',
    'tests/fixtures/e04_t1/README.md',
    'tests/system/evidence/e09_t58_mixed_priors.json',
    'tests/system/evidence/e09_t58_round10_controls.json',
)


def portable(raw: bytes, name: str) -> bytes:
    text = raw.decode('utf-8')
    # Retain provenance filenames without identifying the author's machine.
    text = re.sub(r'~/r[u]ns/', '<author-runs>/', text)
    text = re.sub(r'/h[o]me/[^/\s]+/Development/github\.com/', '<checkout>/', text)
    text = re.sub(r'/h[o]me/[^/\s]+/Applications/fullprof/fp2k', 'fp2k', text)
    text = re.sub(
        r'file:///h[o]me/[^/\s]+/svn-repositories/[^ ]+',
        'https://www.crystallography.net/cod/1000236.cif@130149',
        text,
    )
    if name.endswith(('.edi', '.cif')):
        before = [line for line in raw.splitlines() if not line.lstrip().startswith(b'#')]
        after = [line for line in text.encode().splitlines() if not line.lstrip().startswith(b'#')]
        if before != after:
            raise RuntimeError('portable metadata cannot change crystallographic records: ' + name)
    return text.encode('utf-8')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    changes = []
    replacements = {}

    def record(name, before, after):
        if before != after:
            changes.append({'path': name, 'before': digest(before), 'after': digest(after)})
            replacements[digest(before)] = digest(after)

    for name in FILES:
        path = ROOT / name
        before = path.read_bytes()
        after = portable(before, name)
        record(name, before, after)
        if before != after:
            path.write_bytes(after)

    name = 'tests/fixtures/c13_t12_ids/baseline.zip'
    path = ROOT / name
    before = path.read_bytes()
    output = io.BytesIO()
    changed = False
    with zipfile.ZipFile(io.BytesIO(before)) as source, zipfile.ZipFile(output, 'w') as target:
        target.comment = source.comment
        for info in source.infolist():
            raw = source.read(info.filename)
            after = (
                portable(raw, info.filename) if info.filename.endswith(('.edi', '.cif')) else raw
            )
            record(name + ':' + info.filename, raw, after)
            changed |= raw != after
            target.writestr(info, after)
    if changed:
        path.write_bytes(output.getvalue())
        record(name, before, output.getvalue())

    # These two manifests pin the affected local bytes. Keep the COD upstream
    # digest unchanged: it names the original reference, before comment scrubbing.
    for name in (
        'tests/fixtures/c09_t6_ncaf_5bank_absorption/manifest.json',
        'tests/fixtures/e02_t2_ncaf_5bank/manifest.json',
    ):
        path = ROOT / name
        before = path.read_bytes()
        doc = json.loads(before)
        for relative, old in doc['files'].items():
            if old in replacements:
                actual = digest((path.parent / relative).read_bytes())
                if actual != replacements[old]:
                    raise RuntimeError(
                        'local fixture pin does not name the adapted bytes: ' + relative
                    )
                doc['files'][relative] = actual
        if 'crysta_cli_oracle' in doc:
            pins = doc['crysta_cli_oracle'].get('project_sha256', {})
            for relative, old in pins.items():
                if old in replacements:
                    pins[relative] = replacements[old]
        after = (json.dumps(doc, indent=2, sort_keys=True) + '\n').encode()
        record(name, before, after)
        if before != after:
            path.write_bytes(after)
    args.report.write_text(
        json.dumps({'kind': 'portable metadata adaptation', 'changes': changes}, indent=2) + '\n'
    )
    print(f'{len(changes)} changed file/member digests; numeric reference bytes retained')


if __name__ == '__main__':
    main()
