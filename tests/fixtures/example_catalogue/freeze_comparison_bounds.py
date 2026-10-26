"""Freeze the pre-disposition uncertainty bounds without reading the record under test."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
BASE = '16b8cca9'
SINGLE_CRYSTAL_BASE = 'fe080a38'


def main():
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
        'scope': (
            'Unchanged comparison bounds before the October 24 minor-phase disposition; '
            'these are tolerance-policy retention pins, never calculated correctness values'
        ),
        'cases': cases,
    }
    (HERE / 'comparison-bounds.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
