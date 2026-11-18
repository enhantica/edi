"""Small and large collection files made independently of the bundle writer."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def generate(folder):
    folder = Path(folder)
    online = folder / 'online'
    (online / 'projects').mkdir(parents=True)
    original = ROOT / 'tests/fixtures/online_sources/easydiffraction/projects/lbco-hrpt.zip'
    shutil.copyfile(original, online / 'projects/small.zip')
    shutil.copyfile(original, online / 'projects/large.zip')
    with zipfile.ZipFile(online / 'projects/large.zip', 'a') as archive:
        archive.writestr('padding.txt', b'x' * 6_000_000, compress_type=zipfile.ZIP_STORED)
    entries = []
    for name in ('small', 'large'):
        path = online / 'projects' / (name + '.zip')
        entries.append({
            'id': (
                'pd-neut-cwl_lbco-hrpt'
                if name == 'small'
                else 'pd-neut-tof_ncaf-wish-5bank_synthetic-100p'
            ),
            'kind': 'project',
            'name': name.title() + ' collection example',
            'files': [
                {
                    'path': 'projects/' + path.name,
                    'format': 'zip',
                    'bytes': path.stat().st_size,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            ],
        })
    (online / 'data').mkdir()
    for name in ('small', 'large'):
        payload = b'17.5 4.25 0.5\n18.25 9.75 1.5\n'
        if name == 'large':
            payload += b'#' + b'x' * 6_000_000 + b'\n'
        path = online / 'data' / (name + '.xye')
        path.write_bytes(payload)
        entries.append({
            'id': name + '-data',
            'kind': 'data',
            'files': [
                {
                    'path': 'data/' + path.name,
                    'format': 'xye',
                    'bytes': len(payload),
                    'sha256': hashlib.sha256(payload).hexdigest(),
                }
            ],
        })
    (online / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': entries})
    )
    bundle = folder / 'bundle'
    shutil.copytree(online, bundle)
    (bundle / 'projects/large.zip').unlink()
    (bundle / 'data/large.xye').unlink()
    return online, bundle
