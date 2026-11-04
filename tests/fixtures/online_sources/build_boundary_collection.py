"""Independent collection inputs for ownership, integrity and tutorial gates."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name('easydiffraction')


def build(target, *, include_catalogue=False):
    target = Path(target)
    shutil.copytree(SOURCE, target)
    document = json.loads((target / 'index.json').read_text())
    project = next(e for e in document['entries'] if e['kind'] == 'project')
    alias = json.loads(json.dumps(project))
    alias['id'] = 'pd-neut-cwl_lbco-hrpt'
    if include_catalogue:
        document['entries'].append(alias)
    cif = (target / 'structures/lbco.cif').read_text().replace('3.88', '3.77')
    (target / 'structures/tutorial-lbco.cif').write_text(cif)
    document['entries'].append({
        'id': 'tutorial-lbco',
        'kind': 'structure',
        'name': 'Injected tutorial structure',
        'files': [{'path': 'structures/tutorial-lbco.cif', 'format': 'cif'}],
    })
    pattern = '21.5 117.25 0.75\n22.75 131.75 1.25\n25.125 123.5 1.5\n'
    (target / 'data/tutorial-hrpt.xye').write_text(pattern)
    document['entries'].append({
        'id': 'tutorial-hrpt',
        'kind': 'data',
        'name': 'Injected tutorial pattern',
        'radiation': 'neutron',
        'technique': 'powder constant wavelength',
        'files': [{'path': 'data/tutorial-hrpt.xye', 'format': 'xye'}],
    })
    for entry in document['entries']:
        for file in entry['files']:
            data = (target / file['path']).read_bytes()
            file['bytes'] = len(data)
            file['sha256'] = hashlib.sha256(data).hexdigest()
    (target / 'index.json').write_text(json.dumps(document))
    return target
