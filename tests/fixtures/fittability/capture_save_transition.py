"""Capture before/after saved-byte regression pins, retaining the compared bytes."""

import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

import edi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        'saved_reference', fixture / 'saved_reference.py'
    )
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    pins = json.loads((fixture / 'saved-main.json').read_text())
    rows = []
    for name, rules in pins['projects'].items():
        for rule in rules:
            print(name, rule, flush=True)
            with tempfile.TemporaryDirectory() as folder:
                scratch = Path(folder)
                try:
                    project = edi.Project.load(
                        reference.staged(args.root / name, scratch / 'input', rule)
                    )
                    project.save_as(scratch / 'saved')
                except (ValueError, RuntimeError, OSError) as error:
                    rows.append({'case': name, 'rule': rule, 'refused': str(error)})
                    continue
                hashes = reference.fingerprints(scratch / 'saved')
                if name == 'tests/fixtures/e04_t1/reference/unused-free':
                    relative = 'experiments/dream.edi'
                    raw = (scratch / 'saved' / relative).read_bytes()
                    hashes[relative] = hashlib.sha256(
                        raw.replace(
                            b'_peak.broad_lorentz_gamma_1 0.1\n',
                            b'_peak.broad_lorentz_gamma_1 0.1()\n',
                        )
                    ).hexdigest()
                rows.append({
                    'case': name,
                    'rule': rule,
                    'hashes': hashes,
                    'bytes': {
                        p.relative_to(scratch / 'saved').as_posix(): base64.b64encode(
                            p.read_bytes()
                        ).decode()
                        for p in (scratch / 'saved').rglob('*')
                        if p.is_file()
                    },
                })
    args.output.write_bytes(gzip.compress(json.dumps(rows).encode(), mtime=0))


if __name__ == '__main__':
    main()
