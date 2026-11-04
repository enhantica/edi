#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate/check the Examples presentation index from committed project records.

The project record gives the title and description; the experiment axes, the description
(dimensionality, polarisation, instrument and facility, ADR-0054) and the fitting mode
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


def structure_values(structures: list[Path]) -> list[str]:
    """Every example has a crystal structure; one with moments is magnetic too."""
    magnetic = any(
        re.search(r'^_atom_site_moment\.', p.read_text(encoding='utf-8'), re.MULTILINE)
        for p in structures
    )
    return ['crystal', 'magnetic'] if magnetic else ['crystal']


def example_ids() -> list[str]:
    """The catalogue cases and the declared app-only examples (ADR-0048), in registry order."""
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text(encoding='utf-8'))
    return [
        row['id'] for row in registry['projects'] if row.get('user-facing') or row.get('app-only')
    ]


def generate() -> dict[str, object]:
    entries = {}
    for example_id in example_ids():
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
        structures = sorted((project / 'structures').glob('*.edi'))
        values['structure'] = structure_values(structures)
        sources = [record, analysis, *experiments, *structures]
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


# The Examples list order: powder before single crystal, simulations before fits, sequential
# fits after the others, and within each group the technique in this order.
TECHNIQUES = ('neut-cwl', 'neut-tof', 'xray-cwl', 'neut-xray-cwl')


def order_key(example_id: str, values: dict[str, list[str]]) -> tuple[int, int, int, int]:
    technique = example_id.split('_', 1)[0].split('-', 1)[1]
    if technique not in TECHNIQUES:
        raise ValueError(f'{example_id}: technique {technique!r} has no place in TECHNIQUES')
    return (
        values['sampleForm'] != ['powder'],
        values['purpose'] != ['simulation'],
        values['fittingMode'] == ['sequential'],
        TECHNIQUES.index(technique),
    )


def order_problems(examples: dict[str, dict[str, object]]) -> list[str]:
    """The examples listed out of the declared order, each against the one before it."""
    problems = []
    previous = None
    for example_id, entry in examples.items():
        key = order_key(example_id, entry['values'])
        if previous is not None and key < previous[1]:
            problems.append(f'{example_id} is listed after {previous[0]}')
        previous = (example_id, key)
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = generate()
    problems = order_problems(generated['examples'])
    if problems:
        parser.exit(
            1,
            'Examples out of order; move their rows in docs/user/cli/projects.yml:\n  '
            + '\n  '.join(problems)
            + '\n',
        )
    if args.check:
        committed = json.loads(CATALOG.read_text())
        if committed != generated or list(committed['examples']) != list(generated['examples']):
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
