"""Project the frozen isotropic model count onto its exclusion example."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = 'sc-neut-cwl_tb2ti2o7-heidi_basic'
CASE = 'sc-neut-cwl_tb2ti2o7-heidi_exclusions'


def main():
    old, new = (ROOT / 'docs/user/cli' / name / 'project' for name in (BASE, CASE))
    for relative in ('structures/tb2ti2o7.edi', 'analysis/analysis.edi'):
        if (old / relative).read_bytes() != (new / relative).read_bytes():
            raise ValueError(
                'The model-count projection requires identical structure and analysis'
            )
    before = (old / 'experiments/heidi.edi').read_text()
    after = (new / 'experiments/heidi.edi').read_text()
    start = after.index('_reflns.merge none\n')
    end = after.index('loop_\n_linked_structure.structure_id', start)
    if after[:start] + after[end:] != before:
        raise ValueError('Only reflection admission declarations may extend the selected model')
    path = Path(__file__).with_name('model_counts.json')
    manifest = json.loads(path.read_text())
    if any(row['id'] == CASE for row in manifest['cases']):
        raise ValueError('The count append cannot replace an existing external witness')
    row = copy.deepcopy(next(row for row in manifest['cases'] if row['id'] == BASE))
    row['id'] = CASE
    row['reference_projection'] = {
        'source_case': BASE,
        'rule': (
            'Identical selected model and free flags; admission declarations add no parameters.'
        ),
    }
    manifest['cases'].append(row)
    path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
