#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate/check the Examples presentation index from committed project records.

The project record gives the title and description; the experiment axes, the description
(dimensionality, polarisation, instrument and facility, ADR-0052) and the fitting mode
come from their ordinary native categories, and the purpose from whether any experiment has
measured data.
"""

import argparse
import json
import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'app/examples/metadata.json'


def scalars(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('_'):
            tokens = shlex.split(line, comments=True)
            if len(tokens) == 2:
                if tokens[0] in result:
                    raise ValueError(f'{path}: duplicate scalar {tokens[0]}')
                result[tokens[0]] = '' if tokens[1] in {'?', '.'} else tokens[1]
    return result


def generate() -> dict[str, object]:
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text(encoding='utf-8'))
    # The catalogue cases and the declared app-only examples (ADR-0048), in registry order.
    ids = [
        row['id'] for row in registry['projects'] if row.get('user-facing') or row.get('app-only')
    ]
    entries = {}
    for example_id in ids:
        project = ROOT / 'docs/user/cli' / example_id / 'project'
        record = project / 'project.edi'
        analysis = project / 'analysis/analysis.edi'
        metadata = scalars(record)
        sample, origin = metadata['_metadata.title'].rsplit(' · ', 1)
        experiments = sorted((project / 'experiments').glob('*.edi'))
        axes = {
            'sampleForm': 'sample_form',
            'beamMode': 'beam_mode',
            'probe': 'radiation_probe',
            'scatteringType': 'scattering_type',
        }
        values = {
            key: sorted({scalars(p)['_experiment_type.' + field] for p in experiments})
            for key, field in axes.items()
        }
        described = [scalars(p) for p in experiments]
        measured = any(
            re.search(r'^_(data|refln)\.', p.read_text(encoding='utf-8'), re.MULTILINE)
            for p in experiments
        )
        values.update(
            purpose=['refinement' if measured else 'simulation'],
            fittingMode=[scalars(analysis)['_fitting_mode.type']],
            facilities=sorted({item.get('_instrument.facility', '') for item in described}),
            instruments=sorted({item.get('_instrument.name', '') for item in described}),
            dimensionality=sorted({
                item.get('_experiment_type.dimensionality') or '1d' for item in described
            }),
        )
        values['polarisation'] = sorted({
            (item.get('_experiment_type.polarisation') or 'unpolarised')
            if item.get('_experiment_type.radiation_probe', 'neutron') == 'neutron'
            else '__not_applicable__'
            for item in described
        })
        sources = [record, analysis, *experiments, *sorted((project / 'structures').glob('*.edi'))]
        entries[example_id] = {
            'samples': sample.split(' / '),
            'origin': origin,
            'detail': metadata['_metadata.description'],
            'values': values,
            'searchAliases': [
                example_id,
                metadata['_metadata.title'],
                metadata['_metadata.description'],
            ],
            'sources': [str(p.relative_to(ROOT)) for p in sources],
        }
    return {'schema': 1, 'examples': entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = generate()
    if args.check:
        if json.loads(CATALOG.read_text()) != generated:
            parser.exit(
                1,
                'Example metadata differs from its source project records; '
                'run tools/dev/example_metadata.py\n',
            )
        print('Example metadata matches all bundled source project records')
    else:
        CATALOG.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
