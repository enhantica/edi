"Author the app's Becker-Coppens fitting reference with the independent engine."

import hashlib
import json
import math
from pathlib import Path

import crysta

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_fit/project'


def main():
    project = crysta.Project.load(SOURCE)
    result = project.analysis.fit()
    structure = project.structures[0]
    experiment = project.experiments[0]
    record = json.loads((HERE / 'example-fits.json').read_text())
    target = json.loads(json.dumps(record['cases']['tb2ti2o7']))
    target['source_engine'] = 'crysta ' + crysta.__build_commit__
    target['kind'] = 'independent-engine-reference'
    target['source_sha256'] = {
        p.relative_to(SOURCE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(SOURCE.rglob('*.edi'))
    }
    target['reduced_chi_square'] = result.reduced_chi_square
    for parameter in target['parameters']:
        kind = parameter['kind']
        if kind == 'coordinate':
            atom = next(a for a in structure.atom_sites if a.id == parameter['atom'])
            source = getattr(atom, 'fract_' + parameter['component'])
            factor = 1
        elif kind == 'beta':
            tensor = next(t for t in structure.atom_site_aniso if t.id == parameter['atom'])
            source = getattr(tensor, 'adp_' + parameter['component'])
            a, b = (int(c) - 1 for c in parameter['component'])
            lengths = [
                structure.cell.length_a.value,
                structure.cell.length_b.value,
                structure.cell.length_c.value,
            ]

            factor = 2 * math.pi * math.pi / (lengths[a] * lengths[b])
        else:
            source = experiment.linked_structure.scale
            factor = 1
        parameter['value'] = source.value * factor
        parameter['su'] = source.uncertainty * factor
    record['cases']['tb2ti2o7_becker_coppens'] = target
    (HERE / 'example-fits.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
