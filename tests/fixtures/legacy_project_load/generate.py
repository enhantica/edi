"""Save small background-row witnesses using the sealed pre-id engine.

Run with the producer's Python and explicit edi extension directory. Saved bytes
are regression inputs, not numerical oracles; start values are assigned constants.
"""

import hashlib
import json
import shutil
from pathlib import Path


def main():
    import edi  # noqa: PLC0415

    root = Path(__file__).parent
    manifest = {
        'producer': 'edi b301b6f2, sealed pre-loop-id extension; SDK a1e0ba6d',
        'inputs_are_regression_witnesses': True,
        'projects': {},
    }
    for kind in ('line-segment', 'polynomial', 'chebyshev'):
        source = root.parent / 'loop_parameter_ids' / kind
        project = edi.Project.load(source)
        bank = project.experiments['bank']
        parameters = (
            [row.intensity for row in bank.background]
            if kind == 'line-segment'
            else [row.coef for row in bank.background_terms]
        )
        starts = []
        for index, parameter in enumerate(parameters):
            value, uncertainty = 1.25 + index * 0.375, 0.03125 * (index + 1)
            parameter.start_value = value
            parameter.start_uncertainty = uncertainty
            starts.append([value, uncertainty])
        destination = root / kind
        if destination.exists():
            shutil.rmtree(destination)
        project.save_as(destination)
        manifest['projects'][kind] = {'starts': starts}
    invalid = root / 'invalid'
    invalid.mkdir(exist_ok=True)
    (invalid / 'project.edi').write_text('_edi.schema_version 999\n')
    manifest['files'] = {
        file.relative_to(root).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for category in ('line-segment', 'polynomial', 'chebyshev', 'invalid')
        for file in (root / category).rglob('*.edi')
    }
    (root / 'reference.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
