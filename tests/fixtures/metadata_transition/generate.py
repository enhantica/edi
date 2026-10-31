"""Archive metadata-only input transitions without changing historical oracles."""

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
FIELDS = re.compile(
    rb'_(?:metadata\.(?:purpose|dimensionality|polarisation|instrument|facility)|experiment_type\.(?:dimensionality|polarisation)|instrument\.(?:name|facility))\s'
)


def scientific(data):
    return [line for line in data.splitlines() if line.strip() and not FIELDS.match(line)]


def main():
    rows = {}
    rejected = []
    names = subprocess.check_output(
        ['git', 'diff', '--name-only', 'cea60541', 'HEAD', '--', '*.edi'], cwd=ROOT, text=True
    ).splitlines()
    with zipfile.ZipFile(HERE / 'sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        held = set()
        for name in names:
            old = subprocess.run(
                ['git', 'show', 'cea60541:' + name], cwd=ROOT, capture_output=True, check=False
            )
            path = ROOT / name
            if old.returncode or not path.is_file():
                continue
            before, after = old.stdout, path.read_bytes()
            if scientific(before) != scientific(after):
                rejected.append(name)
                continue
            b, a = (hashlib.sha256(data).hexdigest() for data in (before, after))
            rows[name] = {'before_sha256': b, 'after_sha256': a}
            if b not in held:
                info = zipfile.ZipInfo(b, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, before)
                held.add(b)
    (HERE / 'sources.json').write_text(
        json.dumps(
            {
                'authority': 'ADR-0054',
                'claim': 'Exact input bytes; historical scientific oracles unchanged',
                'files': rows,
            },
            indent=2,
        )
        + '\n'
    )
    print('archived', len(rows), 'non-metadata changes', len(rejected))
    print('\n'.join(rejected))


if __name__ == '__main__':
    main()
