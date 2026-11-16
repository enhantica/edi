"""Apply the two later owner additions without rewriting the retained selection.

ADR-0080 and tutorial_cases/contract.json carry the 2026-11-08 TbTi simulation
and 2026-11-09 CoSiO4 HEIDI additions. The retained selection already includes
the magnetic 2.3 K and 213-frame scan adaptations; never apply those twice.
"""

import json
from pathlib import Path


def current_cases():
    directory = Path(__file__).parent
    original = json.loads((directory / 'catalogue-selection.json').read_text())['cases']
    result = []
    for row in original:
        result.append(row)
        if row['id'] == 'pd-neut-cwl_lbco_simulation':
            result.append({
                'id': 'sc-neut-cwl_tb2ti2o7-heidi_simulation',
                'group': 'Calculations without data',
            })
    result.append({'id': 'sc-neut-cwl_cosio-heidi', 'group': 'Single crystal'})
    declared = json.loads((directory.parent / 'tutorial_cases/contract.json').read_text())['cases']
    if [row['id'] for row in result] != declared or len(declared) != len(set(declared)):
        raise ValueError('The historical selection admits only the two declared owner additions')
    return result
