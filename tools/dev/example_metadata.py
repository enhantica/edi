#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate/check the Examples presentation index from committed project records.

The app-only descriptive tags stay in carried project.edi files during save; supported
experiment axes and fitting mode belong to their ordinary native categories.
"""
from pathlib import Path
import argparse
import json
import re
import shlex

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'app/examples/metadata.json'


def scalars(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('_'):
            tokens = shlex.split(line, comments=True)
            if len(tokens) == 2:
                if tokens[0] in result:
                    raise ValueError(f'{path}: duplicate scalar {tokens[0]}')
                result[tokens[0]] = '' if tokens[1] in ('?', '.') else tokens[1]
    return result


def generate():
    ids = re.findall(r'^  - id: (.+)$', (ROOT / 'docs/user/cli/projects.yml').read_text(), re.M)
    ids.append('pd-xray-cwl_lif')
    entries = {}
    for example_id in ids:
        base = 'app/examples' if example_id == 'pd-xray-cwl_lif' else 'docs/user/cli'
        project = ROOT / base / example_id / 'project'
        record = project / 'project.edi'
        analysis = project / 'analysis/analysis.edi'
        metadata = scalars(record)
        sample, origin = metadata['_metadata.title'].rsplit(' · ', 1)
        experiments = sorted((project / 'experiments').glob('*.edi'))
        axes = {'sampleForm': 'sample_form', 'beamMode': 'beam_mode', 'probe': 'radiation_probe', 'scatteringType': 'scattering_type'}
        values = {key: sorted({scalars(p)['_experiment_type.' + field] for p in experiments}) for key, field in axes.items()}
        values.update(purpose=[metadata['_metadata.purpose']], fittingMode=[scalars(analysis)['_fitting_mode.type']],
                      facilities=[metadata['_metadata.facility']], instruments=[metadata['_metadata.instrument']],
                      dimensionality=[metadata['_metadata.dimensionality']])
        values['polarisation'] = [metadata['_metadata.polarisation']] if values['probe'] == ['neutron'] else ['__not_applicable__']
        sources = [record, analysis, *experiments, *sorted((project / 'structures').glob('*.edi'))]
        entries[example_id] = {'samples': sample.split(' / '), 'origin': origin, 'detail': metadata['_metadata.description'],
                              'values': values, 'searchAliases': [example_id, metadata['_metadata.title'], metadata['_metadata.description']],
                              'sources': [str(p.relative_to(ROOT)) for p in sources]}
    return {'schema': 1, 'examples': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = generate()
    if args.check:
        if json.loads(CATALOG.read_text()) != generated:
            parser.exit(1, 'Example metadata differs from its source project records; run tools/dev/example_metadata.py\n')
        print('Example metadata matches all bundled source project records')
    else:
        CATALOG.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
