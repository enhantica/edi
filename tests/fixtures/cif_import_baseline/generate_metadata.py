"""Freeze pre-move descriptions and scientific bytes from tracked project files."""

import hashlib
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RETIRED = re.compile(
    r'^_metadata\.(dimensionality|polarisation|instrument|facility|purpose)\b', re.MULTILINE
)
FIELDS = re.compile(
    r'^_(?:experiment_type\.(?:dimensionality|polarisation)|'
    r'instrument\.(?:name|facility))\b[^\n]*\n?',
    re.MULTILINE,
)


def scalars(text):
    found = {}
    for line in text.splitlines():
        if line.startswith('_'):
            words = shlex.split(line, comments=True)
            if len(words) == 2:
                found[words[0]] = words[1]
    return found


def generate():
    rows = []
    paths = subprocess.check_output(
        [shutil.which('git'), 'ls-files', '--', '*.edi'], cwd=ROOT, text=True
    ).splitlines()
    for relative in paths:
        if relative.startswith(('tests/unit/', 'tests/integration/', 'tests/system/')):
            continue
        path = ROOT / relative
        text = path.read_text()
        if path.name != 'project.edi' or not RETIRED.search(text):
            continue
        old = scalars(text)
        experiments = []
        mixed = 'pd-neut-xray-cwl_pbso4-d1a-lab' in relative
        for experiment in sorted((path.parent / 'experiments').glob('*.edi')):
            raw = experiment.read_text()
            values = scalars(raw)
            probe = values.get('_experiment_type.radiation_probe')
            expected = {}
            if any(
                '_metadata.' + name in old
                for name in ['dimensionality', 'polarisation', 'instrument', 'facility']
            ):
                expected = {
                    '_experiment_type.dimensionality': '1d',
                    '_experiment_type.polarisation': 'unpolarised' if probe == 'neutron' else '.',
                    '_instrument.name': old.get('_metadata.instrument', '?'),
                    '_instrument.facility': old.get('_metadata.facility', '?'),
                }
                if mixed:
                    expected['_instrument.name'], expected['_instrument.facility'] = (
                        ('D1A', 'ILL') if experiment.stem == 'd1a' else ('?', '?')
                    )
            experiments.append({
                'path': experiment.relative_to(ROOT).as_posix(),
                'expected': expected,
                'scientific_sha256': hashlib.sha256(FIELDS.sub('', raw).encode()).hexdigest(),
            })
        rows.append({'path': relative, 'legacy_record': text, 'experiments': experiments})
    result = {
        'purpose': (
            'Pre-migration record and scientific-byte regression pins; '
            'conversion expectations follow the experiment description '
            'ADR.'
        ),
        'baseline': subprocess.check_output(
            [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'records': rows,
    }
    catalog = ROOT / 'app/examples/metadata.json'
    if catalog.is_file():
        result['catalogue'] = json.loads(catalog.read_text())
    Path(__file__).with_name('metadata-before.json').write_text(
        json.dumps(result, indent=2) + '\n'
    )


if __name__ == '__main__':
    generate()
