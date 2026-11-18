"""Freeze a saved-project regression pin from a separately supplied native app."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    output = here / ('compact-project' if args.compact else 'project')
    if output.exists():
        parser.error(
            'The reference output already exists; existing golden bytes are never overwritten'
        )
    result = subprocess.run(
        [
            str(args.runner.resolve()),
            '-input',
            str(here / ('tst_generate_compact.qml' if args.compact else 'tst_generate.qml')),
            'LegacySavedProjectGenerator::test_generate',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    print(result.stdout + result.stderr)
    if (
        result.returncode != 0
        or f'edi_app_tests: built at {args.expected_revision}\n' not in result.stdout
        or '0 failed' not in result.stdout
        or 'SKIP' in result.stdout
    ):
        raise SystemExit('The separately supplied reference app did not complete its real save')
    files = sorted(path for path in output.rglob('*') if path.is_file())
    if not files:
        raise SystemExit('The reference app produced no saved-project files')
    record = {
        'claim': 'Saved-project byte-retention regression pin, not a numerical correctness oracle',
        'input': 'ui_input.js' if args.compact else 'docs/user/cli/pd-neut-cwl_cosio-d20/project',
        'generator': 'generate.py with the pre-feature app; see the magnetic structures ADR',
        'files': {
            path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        },
    }
    (here / ('compact-reference.json' if args.compact else 'reference.json')).write_text(
        json.dumps(record, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
