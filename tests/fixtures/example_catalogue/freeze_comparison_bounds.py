"""Freeze the pre-disposition uncertainty bounds without reading the record under test."""

import argparse
import json
import subprocess
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
BASE = '16b8cca9'
SINGLE_CRYSTAL_BASE = 'fe080a38'
LMO_BASE = '134e7506e'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lmo-machine', type=Path, required=True)
    args = parser.parse_args()
    machine = dict(
        line.split('=', 1) for line in args.lmo_machine.read_text().splitlines() if '=' in line
    )
    lmo_uncertainties = {}
    cases = {}
    for row in json.loads((HERE / 'catalogue-selection.json').read_text())['cases']:
        case = row['id']
        if case.endswith('_simulation'):
            continue
        name = f'docs/user/cli/{case}/expected.json'
        base = SINGLE_CRYSTAL_BASE if row['group'] == 'Single crystal' else BASE
        record = json.loads(subprocess.check_output(['git', 'show', base + ':' + name], cwd=ROOT))
        groups = {'default': record['quantities']}
        groups.update({
            key: value['quantities'] for key, value in record.get('variants', {}).items()
        })
        if case == 'pd-neut-cwl_lmo-echidna':
            # Keep the two-sigma rule for the asymmetry-off model.
            original = groups['default']
            groups = {
                'default': {
                    key: value for key, value in original.items() if not key.startswith('param.')
                },
                'asymmetry-off': {key: value for key, value in original.items() if key != 'rwp'},
            }
            decided = json.loads(
                subprocess.check_output(['git', 'show', LMO_BASE + ':' + name], cwd=ROOT)
            )['variants']['asymmetry-off']['quantities']
            for key, spec in decided.items():
                if not key.startswith('param.'):
                    continue
                sigma = machine[key.removesuffix('.value') + '.uncertainty']
                assert Decimal(sigma) * 2 == Decimal(str(spec['tol_abs'])), (
                    'Each LMO bound equals exactly twice the independently checked same-model s.u.'
                )
                assert spec['kind'] == 'reference' and spec['tol_rel'] is None, (
                    'LMO retains FullProf values and absolute two-sigma bounds in this model'
                )
                lmo_uncertainties[key] = sigma
                groups['asymmetry-off'][key] = spec
        cases[case] = {
            group: {
                name: {key: spec[key] for key in ('tol_abs', 'tol_rel')}
                for name, spec in values.items()
            }
            for group, values in groups.items()
        }
    output = {
        'source_commit': subprocess.check_output(
            ['git', 'rev-parse', BASE], cwd=ROOT, text=True
        ).strip(),
        'single_crystal_source_commit': subprocess.check_output(
            ['git', 'rev-parse', SINGLE_CRYSTAL_BASE], cwd=ROOT, text=True
        ).strip(),
        'single_crystal_scope': (
            'Tolerance-policy retention pins from the first committed single-crystal comparisons; '
            'numerical correctness remains bound to the external FullProf outputs, not these pins'
        ),
        'lmo_disposition': (
            'crysta uses a continuous FCJ integral distinct from FullProf: LMO shared-value '
            'bounds use the unchanged two-edi-s.u. rule for asymmetry-off; '
            'all other bounds remain frozen'
        ),
        'lmo_bound_derivation': {
            'source_commit': subprocess.check_output(
                ['git', 'rev-parse', LMO_BASE], cwd=ROOT, text=True
            ).strip(),
            'model': 'asymmetry-off',
            'sigma_multiple': 2,
            'uncertainties': lmo_uncertainties,
        },
        'scope': (
            'Unchanged comparison bounds before the October 24 minor-phase disposition; '
            'these are tolerance-policy retention pins, never calculated correctness values'
        ),
        'cases': cases,
    }
    (HERE / 'comparison-bounds.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
