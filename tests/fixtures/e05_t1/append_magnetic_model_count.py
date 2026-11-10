"""Extend the frozen external nuclear selection by the declared magnetic model slots."""

import hashlib
import json
from pathlib import Path

import gemmi

from tests.fixtures.e04_t1.generate import scalars, tables

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
CASE = 'pd-neut-cwl_cosio-d20_2k'
BASE = 'pd-neut-cwl_cosio-d20'


def main():
    path = HERE / 'model_counts.json'
    document = json.loads(path.read_text())
    assert not any(row['id'] == CASE for row in document['cases']), (
        'The magnetic count append must preserve every existing selected-model oracle'
    )
    original = next(row for row in document['cases'] if row['id'] == BASE)
    assert original['n_parameters'] == 60, (
        'The nuclear count retains its frozen external selection'
    )
    project = ROOT / 'docs/user/cli' / CASE / 'project'
    base = ROOT / 'docs/user/cli' / BASE / 'project'
    old_atoms = tables(base / 'structures/cosio.edi')['atom_site']
    new_tables = tables(project / 'structures/cosio.edi')
    atoms = new_tables['atom_site']

    def signature(rows):
        return [(r['id'], r['type_symbol'], r['adp_type']) for r in rows]

    assert signature(atoms) == signature(old_atoms), (
        'The magnetic count projection requires the identical six isotropic nuclear sites'
    )
    experiment = gemmi.cif.read_file(str(project / 'experiments/d20.edi')).sole_block()
    structure = gemmi.cif.read_file(str(project / 'structures/cosio.edi')).sole_block()
    recipe = scalars(project / 'experiments/d20.edi')
    assert recipe['_peak.type'] == 'cwl-tch-pseudo-voigt-fcj', (
        'The declared magnetic example selects the two FCJ model coefficients'
    )
    assert recipe['_absorption.type'] == 'cylinder-hewat', (
        'The declared Hewat cylinder has one active mu_r model slot'
    )
    names = [name for name in original['parameter_names'] if '.background.' not in name]
    names += [
        'd20.background.' + label + '.intensity'
        for label in experiment.find_values('_background.id')
    ]
    names += ['d20.peak.asym_fcj_1', 'd20.peak.asym_fcj_2', 'd20.absorption.mu_r']
    moments = list(structure.find_values('_atom_site_moment.label'))
    assert moments == ['Co1', 'Co2'], (
        'The magnetic model contains exactly its two declared cobalt site moments'
    )
    names += [
        'cosio.atom_site_moment.' + label + '.crystalaxis_' + axis
        for label in moments
        for axis in 'xyz'
    ]
    factors = structure.find([
        '_magnetic_form_factor.type_symbol',
        '_magnetic_form_factor.approximation',
    ])
    assert [tuple(row) for row in factors] == [('Co', 'dipole')], (
        'ADR-0108 selects only C2 for the declared dipole form factor; C4 and C6 are inactive'
    )
    names.append('cosio.magnetic_form_factor.Co.j2_coefficient')
    assert len(names) == len(set(names)) == 72, (
        'The selected count is 60 - 14 background + 16 background + 2 FCJ + mu_r + 6 moments + C2'
    )
    document['cases'].append({
        'id': CASE,
        'n_parameters': len(names),
        'parameter_names': names,
        'experiments': ['d20'],
        'reference_projection': {
            'source_case': BASE,
            'rule': 'Frozen external nuclear selection, identical six isotropic sites; '
            'input-authored 16 background ordinates, FCJ pair and Hewat mu_r; '
            'ADR-0108 two three-component moments and one active dipole C2. '
            'Fixed and symmetry-dependent fields remain model slots, as in the nuclear selection. '
            'No edi/crysta parameter walk, fit or saved output supplies this count.',
            'input_sha256': {
                p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(project.rglob('*.edi'))
            },
        },
    })
    path.write_text(json.dumps(document, indent=2) + '\n')
    print('Appended independently projected magnetic selected-model count:', len(names))


if __name__ == '__main__':
    main()
