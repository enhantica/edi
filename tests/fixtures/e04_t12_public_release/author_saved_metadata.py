"""Adapt saved regression pins only after reproducing their historical bytes.

The old input is supplied at authoring time. A before-save must match every
existing hash. Only comment/metadata edits may distinguish the public input;
all non-project output files remain byte-identical. No physics oracle is made.
"""

import argparse
import contextlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from tests.fixtures.c34_t28_baseline import generate_bytes as reference
from tests.fixtures.e04_t12_public_release.adapt_test_metadata import payload

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    baseline = json.loads((ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json').read_text())
    records = {}
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        historical = scratch / 'historical'
        historical.mkdir()
        raw = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'archive',
            args.revision,
            'docs/user',
        ])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(historical, filter='data')
        for index, (case, expected) in enumerate(baseline['cases'].items()):
            if not case.startswith('repo:'):
                continue
            directory = historical / case.removeprefix('repo:')
            before_hashes = reference.hashes(directory)
            if before_hashes != expected['input_sha256']:
                raise ValueError(
                    'the authoring input must match all historical input pins: ' + case
                )
            before = scratch / ('before-' + str(index))
            saved_before = reference.observe(directory, before, calculator=True)
            if saved_before != expected['saved_sha256']:
                raise ValueError(
                    'the current writer must reproduce the full prior saved oracle: ' + case
                )
            for file in directory.rglob('*'):
                if file.is_file():
                    with contextlib.suppress(UnicodeError):
                        file.write_text(payload(file.read_text(), file.name))
            after = scratch / ('after-' + str(index))
            saved_after = reference.observe(directory, after, calculator=True)
            for name in saved_before:
                if name != 'project.edi' and saved_before[name] != saved_after[name]:
                    raise ValueError(
                        'a descriptive scrub changed a physical output: ' + case + '/' + name
                    )
            records[case] = {
                'input_sha256': reference.hashes(directory),
                'saved_sha256': saved_after,
                'prior_input_sha256': before_hashes,
                'prior_saved_sha256': saved_before,
            }
    (HERE / 'saved-metadata.json').write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
