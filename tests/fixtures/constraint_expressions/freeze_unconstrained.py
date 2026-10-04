"""Freeze a labelled writer regression pin from the pre-feature native build."""

import hashlib
import importlib
import json
import re
import runpy
import sys
import tempfile
from pathlib import Path


def snapshot(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if not path.is_file():
            continue
        content = path.read_bytes()
        if path.name == 'project.edi':
            content = re.sub(
                rb'(?m)^(_metadata\.(?:created|last_modified)\s+).+$', rb'\1<CLOCK>', content
            )
        result[path.relative_to(root).as_posix()] = hashlib.sha256(content).hexdigest()
    return result


if __name__ == '__main__':
    fixture = Path(__file__).resolve().parent
    engine = importlib.import_module(sys.argv[1])
    materialize = runpy.run_path(str(fixture / 'project.py'))['materialize']
    with tempfile.TemporaryDirectory(prefix='constraint-writer-') as scratch:
        project = engine.Project.load(materialize(Path(scratch) / 'input'))
        project.save_as(Path(scratch) / 'saved')
        result = snapshot(Path(scratch) / 'saved')
    (fixture / 'unconstrained_regression.json').write_text(json.dumps(result, indent=2) + '\n')
