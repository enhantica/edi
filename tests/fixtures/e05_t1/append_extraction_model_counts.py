"""Project frozen external model selections onto the two extraction inputs."""

import hashlib
import json
from pathlib import Path

from tests.fixtures.e04_t1.generate import ROOT, scalars, tables

HERE = Path(__file__).resolve().parent
EXAMPLES = (
    (
        'pd-neut-cwl_lbco-hrpt_start-2',
        'pd-neut-cwl_lbco-hrpt_le-bail',
        'lbco',
        'hrpt',
        'le_bail',
        ('hrpt.preferred_orientation.', 'hrpt.absorption.'),
    ),
    (
        'pd-xray-cwl_pbso4-lab',
        'pd-xray-cwl_pbso4-lab_pawley',
        'pbso4',
        'lab',
        'pawley',
        ('pbso4.atom_site.',),
    ),
)


def declarations(project, phase, detector):
    structure = project / 'structures' / f'{phase}.edi'
    experiment = project / 'experiments' / f'{detector}.edi'
    model = scalars(structure)
    settings = scalars(experiment)
    loops = tables(experiment)
    common = {
        'cell_fields': sorted(key for key in model if key.startswith('_cell.')),
        'space_group': model['_space_group.name_h_m'],
        'peak': settings['_peak.type'],
        'peak_and_instrument_fields': sorted(
            key for key in settings if key.startswith(('_peak.', '_instrument.'))
        ),
        'beam': settings['_experiment_type.beam_mode'],
        'probe': settings['_experiment_type.radiation_probe'],
        'background_type': settings['_background.type'],
        'background_fields': [(row.get('id'), sorted(row)) for row in loops['background']],
        'linked_phases': [row['structure_id'] for row in loops['linked_structure']],
    }
    sites = [(row['id'], row['adp_type']) for row in tables(structure).get('atom_site', [])]
    return common, model.get('_structure.calc_method', 'rietveld'), sites, settings, loops


def projected_row(source, case, phase, detector, method, omissions):
    previous = ROOT / 'docs/user/cli' / source['id'] / 'project'
    current = ROOT / case['path']
    old, _, old_sites, old_settings, old_loops = declarations(previous, phase, detector)
    new, declared, new_sites, new_settings, new_loops = declarations(current, phase, detector)
    if old != new or declared != method:
        raise ValueError('Extraction count projection requires the same declared cell and profile')
    if method == 'le_bail':
        if (
            new_sites != old_sites
            or 'preferred_orientation' not in old_loops
            or 'preferred_orientation' in new_loops
            or '_absorption.type' not in old_settings
            or '_absorption.type' in new_settings
        ):
            raise ValueError('Le Bail projection drops the removed orientation and absorption')
    elif not old_sites or new_sites or new_loops['linked_structure'][0]['scale']['free']:
        raise ValueError('Pawley projection requires the atomless input with a fixed scale')

    for relative, digest in case['inputs_sha256'].items():
        if hashlib.sha256((current / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Extraction count input changed: {relative}')

    names = [name for name in source['parameter_names'] if not name.startswith(omissions)]
    return {
        'id': case['id'],
        'n_parameters': len(names),
        'parameter_names': names,
        'experiments': [detector],
        'reference_projection': {
            'source_case': source['id'],
            'removed_prefixes': list(omissions),
            'rule': 'Keep existing cell, linked scale and active experiment slots. Count saved '
            'sites regardless of free flags and exclude intensities generated during a fit.',
        },
    }


def main():
    path = HERE / 'model_counts.json'
    document = json.loads(path.read_text())
    selected = {row['id']: row for row in document['cases']}
    cli = {row['id']: row for row in json.loads((HERE / 'cli.json').read_text())['cases']}
    for previous, added, phase, detector, method, omissions in EXAMPLES:
        if added in selected:
            raise ValueError('The independent count append cannot replace a row')
        document['cases'].append(
            projected_row(selected[previous], cli[added], phase, detector, method, omissions)
        )
    path.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
