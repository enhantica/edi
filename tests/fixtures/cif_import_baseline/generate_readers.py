"""Capture labelled reader regression pins from the pre-import main model."""

import gzip
import importlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures import cif_import_cases as case


def normalized(text):
    cells = case.columns(text)
    return {
        tag: values
        for tag, values in cells.items()
        if not re.match(
            r'_(?:experiment_type_(?:dimensionality|polarisation)|instrument_(?:name|facility))$',
            tag,
        )
    }


def generate():
    rows = []
    api = importlib.import_module(case.API)
    paths = subprocess.check_output(
        [shutil.which('git'), 'ls-files', '--', '*.edi', '*.cif', '*.CIF'],
        cwd=case.ROOT,
        text=True,
    ).splitlines()
    for relative in paths:
        if relative.startswith(('tests/unit/', 'tests/integration/', 'tests/system/')):
            continue
        path = case.ROOT / relative
        if 'structures' in path.parts:
            kinds = ['structure']
        elif 'experiments' in path.parts:
            kinds = ['experiment']
        elif path.suffix.lower() == '.cif':
            kinds = ['structure', 'experiment']
        else:
            continue
        for kind in kinds:
            try:  # noqa: PLW0717 - capture only successful baseline reads
                factory = api.StructureFactory if kind == 'structure' else api.ExperimentFactory
                obj = factory.from_cif_path(path)
                project = case.attach(api, kind, obj)
                with tempfile.TemporaryDirectory() as scratch:
                    saved = Path(scratch) / 'saved'
                    project.save_as(saved)
                    folder = saved / ('structures' if kind == 'structure' else 'experiments')
                    files = list(folder.glob('*.edi'))
                    if len(files) != 1:
                        raise RuntimeError  # noqa: TRY301 - refuse ambiguous observer output
                    text = files[0].read_text()
                rows.append({'path': relative, 'kind': kind, 'values': normalized(text)})
            except (ValueError, RuntimeError):
                pass
    payload = {
        'label': 'Regression pins of main readers, not independent physical references',
        'baseline': subprocess.check_output(
            [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=case.ROOT, text=True
        ).strip(),
        'rows': rows,
    }
    Path(__file__).with_name('readers-before.json.gz').write_bytes(
        gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0)
    )


if __name__ == '__main__':
    generate()
