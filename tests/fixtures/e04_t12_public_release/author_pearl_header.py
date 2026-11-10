"""Re-author the PEARL FullProf runs after a descriptive data-header edit.

This is an authoring command only. The engine output is committed; acceptance
never invokes FullProf. The measured numeric data rows are retained exactly.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fp2k', type=Path, required=True)
    args = parser.parse_args()
    record_path = HERE / 'pearl-header.json'
    previous = json.loads(record_path.read_text())['files'] if record_path.exists() else {}
    records = {}
    for tier, stem in (('verification', 'scale-fit'), ('fitting', 'full-fit')):
        home = ROOT / 'knowledge' / tier / 'fullprof/pd-neut-tof_ceo2-pearl_polynomial'
        data = home / 'Ceo2_PEARL.dat'
        before = data.read_bytes()
        after = re.sub(rb' \([CE]\d{2}-T\d+[a-z]?\)', b'', before)
        if before.splitlines()[4:] != after.splitlines()[4:]:
            raise ValueError('the PEARL numeric input must be byte unchanged')
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp)
            for path in home.iterdir():
                if path.is_file():
                    shutil.copy2(path, scratch / path.name)
            (scratch / data.name).write_bytes(after)
            (scratch / (stem + '.dat')).write_bytes(after)
            shutil.copyfile(home / (stem + '.inp'), scratch / (stem + '.pcr'))
            result = subprocess.run(
                [str(args.fp2k), stem, stem],
                cwd=scratch,
                capture_output=True,
                check=False,
                timeout=25,
            )
            if result.returncode != 0 or not (scratch / (stem + '.out')).is_file():
                raise RuntimeError(
                    'FullProf did not author the expected output: '
                    + result.stderr.decode(errors='replace')
                )
            if (
                b'Convergence reached at this CYCLE'
                not in (scratch / (stem + '.out')).read_bytes()
            ):
                raise RuntimeError('the authoring fit must converge before output is committed')
            data.write_bytes(after)
            output = home / (stem + '.out')
            old_output = output.read_bytes()
            output.write_bytes((scratch / (stem + '.out')).read_bytes())
            records[data.relative_to(ROOT).as_posix()] = {
                'before_sha256': previous.get(data.relative_to(ROOT).as_posix(), {}).get(
                    'before_sha256', hashlib.sha256(before).hexdigest()
                ),
                'after_sha256': hashlib.sha256(after).hexdigest(),
            }
            records[output.relative_to(ROOT).as_posix()] = {
                'before_sha256': previous.get(output.relative_to(ROOT).as_posix(), {}).get(
                    'before_sha256', hashlib.sha256(old_output).hexdigest()
                ),
                'after_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            }
    for tier in ('verification', 'fitting'):
        provenance = (
            ROOT / 'knowledge' / tier / 'fullprof/pd-neut-tof_ceo2-pearl_polynomial/PROVENANCE.md'
        )
        text = provenance.read_text()
        for entry in records.values():
            text = text.replace(entry['before_sha256'], entry['after_sha256'])
        provenance.write_text(text)
    (HERE / 'pearl-header.json').write_text(
        json.dumps(
            {
                'engine': 'FullProf.2k 8.40',
                'executable_sha256': hashlib.sha256(args.fp2k.read_bytes()).hexdigest(),
                'command': ['fp2k', '<scale-fit-or-full-fit>', '<scale-fit-or-full-fit>'],
                'claim': (
                    'Only header text changed; original measured numeric input is byte unchanged.'
                ),
                'files': records,
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
