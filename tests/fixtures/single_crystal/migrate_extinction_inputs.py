"""Migrate frozen scientific inputs without changing their numerical target values."""

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def retain_single_radius_path(path, text):
    if not re.search(r'(?m)^_extinction.domain_radius \S+\(\)$', text):
        return
    analysis = path.parents[1] / 'analysis/analysis.edi'
    if analysis.exists() and 'extinction_path' not in analysis.read_text():
        analysis.write_text(
            analysis.read_text() + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
            'crystal_radius experiment.extinction.crystal_radius\n'
            'domain_radius experiment.extinction.domain_radius\n'
            'loop_\n_constraint.id\n_constraint.expression\n'
            "extinction_path 'crystal_radius = domain_radius / 1000'\n"
        )


def main():
    for base in (ROOT / 'tests/fixtures/single_crystal', ROOT / 'tests/fitting'):
        for path in base.rglob('*.edi'):
            text = path.read_text()
            match = re.search(r'(?m)^_extinction.radius (\S+)$', text)
            if match is None:
                retain_single_radius_path(path, text)
                continue
            radius = match[1]
            mosaic = re.search(r'(?m)^_extinction.mosaicity (\S+)$', text)[1]
            r = float(radius.rstrip('()'))
            g = float(mosaic.rstrip('()')) * math.pi / 10800 * 10000
            if r == 0 and g == 0:
                text = re.sub(r'(?m)^_extinction\.(type|model|radius|mosaicity) .*\n', '', text)
                text += '_extinction.type none\n'
            else:
                text = text.replace(
                    '_extinction.type becker-coppens\n', '_extinction.type becker-coppens-mixed\n'
                )
                text = text.replace(
                    '_extinction.model gauss', '_extinction.mosaic_distribution gaussian'
                )
                text = text.replace(
                    '_extinction.model lorentz', '_extinction.mosaic_distribution lorentzian'
                )
                text = text.replace(
                    '_extinction.radius ',
                    f'_extinction.crystal_radius {r / 1000}\n_extinction.domain_radius ',
                )
                text = text.replace(
                    '_extinction.mosaicity ' + mosaic, '_extinction.mosaic_spread ' + str(g)
                )
            retain_single_radius_path(path, text)
            path.write_text(text)
        for path in base.rglob('expected.json'):
            path.write_text(
                path.read_text().replace('param.radius.value', 'param.domain_radius.value')
            )
    inventory = ROOT / 'tests/fixtures/single_crystal/corpus-inventory.json'
    if inventory.exists():
        doc = json.loads(inventory.read_text())
        for path in doc['selected_reference_sha256']:
            doc['selected_reference_sha256'][path] = hashlib.sha256(
                (ROOT / path).read_bytes()
            ).hexdigest()
        inventory.write_text(json.dumps(doc, indent=2) + '\n')


if __name__ == '__main__':
    main()
