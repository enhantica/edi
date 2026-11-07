"""Snapshot crysta's saved powder reflection loops for the rendered table checks."""

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import crysta

from tests.fixtures.magnetic_pnma.reference import columns

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20']


def reflection_rows(experiment, *, magnetic):
    values = columns(experiment.read_text())
    hkl = zip(*(values['_refln.index_' + axis] for axis in 'hkl'), strict=True)
    keys = ['d_spacing', 'two_theta', 'f_squared_calc']
    if magnetic:
        keys.append('f_m_perp_squared_calc')
    return [
        [' '.join(indices), *map(float, row)]
        for indices, *row in zip(hkl, *(values['_refln.' + key] for key in keys), strict=True)
    ]


if __name__ == '__main__':
    outputs = []
    with TemporaryDirectory() as temporary:
        for example in EXAMPLES:
            source = ROOT / 'docs/user/cli' / example / 'project'
            magnetic = example.endswith('_2k')
            if magnetic:
                source = shutil.copytree(source, Path(temporary) / 'fixed-moment-input')
                shutil.copyfile(
                    Path(__file__).with_name('cosio-2k-reference.edi'),
                    source / 'structures/cosio.edi',
                )
            model = crysta.Project.load(source)
            model.analysis.calculate()
            destination = Path(temporary) / example
            model.save_as(destination)
            rows = reflection_rows(destination / 'experiments/d20.edi', magnetic=magnetic)
            cells = ',\n'.join('    ' + json.dumps(row) for row in rows)
            outputs.append(f'  "{example}": [\n{cells}\n  ]')
    engine = f'  "crysta": {json.dumps(crysta.__build_commit__)}'
    Path(__file__).with_name('reflection-table.json').write_text(
        '{\n' + ',\n'.join([engine, *outputs]) + '\n}\n'
    )
