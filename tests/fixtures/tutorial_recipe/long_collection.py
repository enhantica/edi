"""Independent long metadata specimens, with ordinary collection parsing and real table models."""

import json
import shutil
from pathlib import Path


def build(destination):
    source = Path(__file__).resolve().parents[1] / 'online_sources/easydiffraction'
    shutil.copytree(source, destination)
    index = destination / 'index.json'
    doc = json.loads(index.read_text())
    for entry in doc['entries']:
        if entry['kind'] in {'structure', 'data'}:
            entry['id'] = entry['kind'] + '-' + 'long-identifier-' * 6 + 'entry'
            entry['name'] = 'Long sample name ' * 15
            entry['description'] = 'Long descriptive collection metadata ' * 12
    index.write_text(json.dumps(doc))
    return destination
