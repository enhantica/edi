"""Snapshot crysta's saved powder reflection loops for the rendered table checks."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import crysta

from tests.fixtures.magnetic_pnma.reference import columns

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20']


def reflection_rows(experiment):
    values = columns(experiment.read_text())
    hkl = zip(*(values['_refln.index_' + axis] for axis in 'hkl'), strict=True)
    keys = ['d_spacing', 'two_theta', 'f_squared_calc']
    if '_refln.m_perp_squared_calc' in values:
        keys.append('m_perp_squared_calc')
    return [
        [' '.join(indices), *map(float, row)]
        for indices, *row in zip(hkl, *(values['_refln.' + key] for key in keys), strict=True)
    ]


if __name__ == '__main__':
    outputs = []
    with TemporaryDirectory() as temporary:
        for example in EXAMPLES:
            model = crysta.Project.load(ROOT / 'docs/user/cli' / example / 'project')
            model.analysis.calculate()
            destination = Path(temporary) / example
            model.save_as(destination)
            rows = reflection_rows(destination / 'experiments/d20.edi')
            cells = ',\n'.join('    ' + json.dumps(row) for row in rows)
            outputs.append(f'  "{example}": [\n{cells}\n  ]')
    engine = f'  "crysta": {json.dumps(crysta.__build_commit__)}'
    Path(__file__).with_name('reflection-table.json').write_text(
        '{\n' + ',\n'.join([engine, *outputs]) + '\n}\n'
    )
