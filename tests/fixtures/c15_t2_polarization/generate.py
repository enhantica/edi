"""Author-time only: freeze upstream bytes and run the independent FullProf oracle once.

Usage: python generate.py /path/to/diffraction-lib /absolute/path/to/fp2k
No acceptance test imports or runs this generator.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = Path(sys.argv[1])
FP2K = Path(sys.argv[2]).resolve()
REVISION = '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf'
PREFIX = 'docs/docs/verification/fullprof/pd-xray-cwl_lif/'
STEM = 'lif_single_polarized'
GIT = shutil.which('git')
if GIT is None:
    message = ' generator requires git'
    raise RuntimeError(message)
manifest = {
    'upstream': 'https://github.com/easyscience/diffraction-lib',
    'sha': REVISION,
    'files': {},
    'K': 0.5,
    'Cthm': 0.8,
    'monochromator_twotheta_deg': 26.5650511771,
}
for suffix in ('pcr', 'dat', 'prf', 'sum', 'bac'):
    name = STEM + '.' + suffix
    raw = subprocess.check_output([
        GIT,
        '-C',
        str(UPSTREAM),
        'show',
        REVISION + ':' + PREFIX + name,
    ])
    (ROOT / name).write_bytes(raw)
    manifest['files'][name] = hashlib.sha256(raw).hexdigest()
rows = (ROOT / (STEM + '.prf')).read_text().split('BEGIN', 1)[1].split('END', 1)[0]
(ROOT / 'reference.tsv').write_text(
    ''.join(
        line.split()[0] + '\t' + line.split()[2] + '\n'
        for line in rows.splitlines()
        if line.strip()
    )
)
with tempfile.TemporaryDirectory(prefix='-fullprof-') as temp:
    work = Path(temp)
    for suffix in ('pcr', 'dat'):
        shutil.copyfile(ROOT / (STEM + '.' + suffix), work / (STEM + '.' + suffix))
    result = subprocess.run(
        [str(FP2K)],
        input=STEM + '\n\n\n',
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    output = ROOT / 'author-run'
    output.mkdir(exist_ok=True)
    (output / 'fp2k.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    manifest['author_run'] = {
        'executable': FP2K.name,
        'executable_sha256': hashlib.sha256(FP2K.read_bytes()).hexdigest(),
        'command': "printf 'lif_single_polarized\\n\\n\\n' | " + FP2K.name,
        'files': {},
    }
    for suffix in ('prf', 'sum'):
        name = STEM + '.' + suffix
        raw = (work / name).read_bytes()
        (output / name).write_bytes(raw)
        manifest['author_run']['files'][name] = hashlib.sha256(raw).hexdigest()
(ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
