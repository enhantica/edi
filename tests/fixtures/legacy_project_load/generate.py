"""Generate current-format load fixtures with assigned nontrivial start states.

Old spellings are introduced only in disposable copies by the acceptance actors.
No fitting engine supplies the numerical constants or fixture identities.
"""

import hashlib
import json
import shlex
import shutil
from pathlib import Path


def main():
    root = Path(__file__).parent
    manifest = {
        'producer': 'generate.py; ids from loop_parameter_ids, assigned closed-form starts',
        'inputs_are_regression_witnesses': True,
        'projects': {},
    }
    for kind in ('line-segment', 'polynomial', 'chebyshev'):
        source = root.parent / 'loop_parameter_ids' / kind
        destination = root / kind
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        tokens = shlex.split((source / 'experiments/bank.edi').read_text(), comments=True)
        start = tokens.index('_background.id')
        end = start
        while end < len(tokens) and tokens[end].startswith('_'):
            end += 1
        width = end - start
        rows = []
        while end < len(tokens) and not tokens[end].startswith(('_', 'loop_', 'data_')):
            rows.append(tokens[end])
            end += width
        states = []
        starts = []
        for index, identity in enumerate(rows):
            value, uncertainty = 1.25 + index * 0.375, 0.03125 * (index + 1)
            starts.append([value, uncertainty])
            states.append(f'bank.background.{identity} {value} {uncertainty} .')
        path = destination / 'analysis/analysis.edi'
        path.write_text(
            path.read_text() + '\nloop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
            '_fit_parameter.start_uncertainty\n_fit_parameter.start_tied\n'
            + '\n'.join(states)
            + '\n'
        )
        manifest['projects'][kind] = {'starts': starts}
    invalid = root / 'invalid'
    invalid.mkdir(exist_ok=True)
    # A current-schema but incomplete project still exercises all failed-load routes.
    (invalid / 'project.edi').write_text('_edi.schema_version 3\n')
    manifest['files'] = {
        file.relative_to(root).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for category in ('line-segment', 'polynomial', 'chebyshev', 'invalid')
        for file in (root / category).rglob('*.edi')
    }
    (root / 'reference.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
