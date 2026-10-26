"""Append LBCO's unchanged model topology from the frozen external selection."""

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    sys.path.insert(0, str(ROOT / 'tests/fixtures/e04_t1'))
    reference = importlib.import_module('generate')
    name = 'pd-neut-cwl_lbco-hrpt_cif-import'
    old_name = 'pd-neut-cwl_lbco-hrpt_start-2'
    old = ROOT / 'docs/user/cli' / old_name / 'project'
    new = ROOT / 'docs/user/cli' / name / 'project'
    for relative in ('experiments/hrpt.edi', 'analysis/analysis.edi'):
        if (new / relative).read_bytes() != (old / relative).read_bytes():
            raise ValueError(
                'The external model-topology projection requires unchanged experiment and analysis'
            )
    atom = reference.tables(new / 'structures/lbco.cif')['atom_site']
    if [(r['id'], r['type_symbol'], r['adp_type']) for r in atom] != [
        ('La', 'La', 'Biso'),
        ('Ba', 'Ba', 'Biso'),
        ('Co', 'Co', 'Biso'),
        ('O', 'O', 'Biso'),
    ]:
        raise ValueError('The external model selection requires the same four isotropic sites')
    if reference.scalars(new / 'structures/lbco.cif')['_space_group.name_h_m'] != 'P m -3 m':
        raise ValueError('The topology projection requires the same cubic space group')
    path = Path(__file__).with_name('model_counts.json')
    document = json.loads(path.read_text())
    if any(row['id'] == name for row in document['cases']):
        raise ValueError('The independent model-count append cannot replace a row')
    row = copy.deepcopy(next(row for row in document['cases'] if row['id'] == old_name))
    row['id'] = name
    row['reference_projection'] = {
        'source_case': old_name,
        'rule': 'The selected model includes fixed parameters. The same six cell parameters, '
        'four isotropic sites and byte-identical experiment/analysis retain exactly '
        'the frozen external parameter names; values and free flags do not change the topology.',
        'cif_sha256': hashlib.sha256((new / 'structures/lbco.cif').read_bytes()).hexdigest(),
    }
    document['cases'].append(row)
    path.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
