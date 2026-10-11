"""Capture row identities from diffraction-lib; run in its reference environment.

Only reader/backend labels change. Polynomial is viewed as coefficient storage
in the reference's Chebyshev category; no calculation or basis conversion runs.
Declared ids, row order, parameter values and the committed inputs stay intact.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference_checkout', type=Path)
    args = parser.parse_args()
    from easydiffraction import Project  # noqa: PLC0415

    git = shutil.which('git')
    if git is None:
        message = 'The reference revision requires an installed git executable'
        raise RuntimeError(message)
    root = Path(__file__).parent
    result = {
        'reference_revision': subprocess.check_output(
            [git, '-C', str(args.reference_checkout), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'projects': {},
    }
    for kind in ('line-segment', 'polynomial', 'chebyshev'):
        original = root / kind
        with tempfile.TemporaryDirectory() as temporary:
            private = Path(temporary) / 'project'
            shutil.copytree(original, private)
            for path in private.rglob('*.edi'):
                text = path.read_text().replace('_edi.schema_version 3', '_edi.schema_version 1')
                text = text.replace('_calculator.type crysta', '_calculator.type cryspy')
                text = text.replace(
                    '_peak.type cwl-tch-pseudo-voigt', '_peak.type cwl-thompson-cox-hastings'
                )
                print('reference project', kind, path.name, flush=True)
                text = text.replace('_background.type polynomial', '_background.type chebyshev')
                if kind == 'polynomial' and path.parent.name == 'experiments':
                    text = text.replace(
                        '_background.origin 40', '_background.x_min 40\n_background.x_max 72'
                    )
                path.write_text(text)
            project = Project.load(str(private))
            names = sorted(
                p.unique_name
                for p in project.parameters
                if any(
                    '.' + category + '.' in p.unique_name
                    for category in (
                        'background',
                        'preferred_orientation',
                        'linked_structure',
                        'atom_site',
                        'atom_site_aniso',
                    )
                )
            )
        result['projects'][kind] = {
            'names': names,
            'sha256': {
                p.relative_to(original).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(original.rglob('*.edi'))
            },
        }
    (root / 'reference.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
