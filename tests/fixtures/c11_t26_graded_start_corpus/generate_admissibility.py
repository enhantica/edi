"""Generate the  start-admissibility oracle through crysta's CLI refusal path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / 'examples'
OUTPUT = Path(__file__).with_name('admissibility.json')
PARENTS = (
    'refine-ncaf-wish-5bank',
    'refine-ncaf-wish-2bank',
    'refine-si-sepd',
    'refine-lbco-hrpt',
    'refine-cosio-d20',
)
VARIANTS = tuple(f'{parent}-s{index}' for parent in PARENTS for index in range(1, 6))


def _edi_input_sha256(project: Path) -> str:
    digest = hashlib.sha256()
    inputs = sorted(project.rglob('*.edi'))
    if not inputs:
        raise ValueError(f'{project}: expected at least one .edi input')
    for path in inputs:
        digest.update(path.relative_to(project).as_posix().encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--crysta', type=Path, required=True)
    parser.add_argument('--crysta-commit', required=True)
    parser.add_argument('--variant', action='append', choices=VARIANTS)
    args = parser.parse_args()
    selected = args.variant or list(VARIANTS)

    records = {}
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding='utf-8'))
        if existing.get('engine', {}).get('commit') == args.crysta_commit:
            records.update(existing.get('variants', {}))

    for variant in selected:
        project = EXAMPLES / variant
        completed = subprocess.run(
            [str(args.crysta), 'fit', str(project), '--max-iter', '0'],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, 'OMP_NUM_THREADS': '1'},
        )
        records[variant] = {
            'accepted': completed.returncode == 0,
            'edi_input_sha256': _edi_input_sha256(project),
            'message': completed.stderr.strip(),
        }

    document = {
        'schema': '-crysta-start-admissibility-v1',
        'engine': {
            'commit': args.crysta_commit,
            'invocation': 'OMP_NUM_THREADS=1 crysta fit <variant> --max-iter 0',
        },
        'variants': dict(sorted(records.items())),
    }
    OUTPUT.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    refused = [variant for variant in selected if not records[variant]['accepted']]
    if refused:
        print(f'crysta refused: {refused}')
        return 1
    print(f'crysta accepted {len(selected)} variant(s); oracle has {len(records)} record(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
