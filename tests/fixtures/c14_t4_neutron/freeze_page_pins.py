"""Freeze pre-migration regression bounds and independent FullProf artifact digests.

Run deliberately from edi: python tests/fixtures/c14_t4_neutron/freeze_page_pins.py.
The source is the committed kickoff tree, never a migrated page under test.
"""

import ast
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = 'retained pre-migration page archive'
PAGES = [
    'pd-neut-cwl_LaB6_basic',
    'pd-neut-cwl_LaB6_absorption',
    'pd-neut-cwl_LaB6_fcj-asymmetry',
    'pd-neut-cwl_LaB6_11B',
    'pd-neut-cwl_LBCO_basic',
    'pd-neut-cwl_PbSO4_basic',
    'pd-neut-cwl_PbSO4_beba-asymmetry',
    'pd-neut-cwl_Y2O3_isotropic-adp',
    'pd-neut-tof_Fe_pseudo-voigt',
]


def frozen(path):
    with zipfile.ZipFile(
        ROOT / 'tests/fixtures/e04_t12_public_release/history/pages.zip'
    ) as archive:
        return archive.read(path)


def main():
    rows = {}
    for page in PAGES:
        tree = ast.parse(frozen(f'docs/dev/verification/{page}.py'))
        constants = {
            n.targets[0].id: n.value.value
            for n in tree.body
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Constant)
        }
        bounds = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and ast.unparse(n.func).endswith('.AgreementTolerances')
        ]
        if not bounds:
            raise ValueError('expected one pre-migration agreement pin per page: ' + page)
        directory = constants['FULLPROF_PROJECT_DIR']
        names = [
            v for k, v in constants.items() if k.endswith(('_PRF_FILE', '_BAC_FILE', '_SUM_FILE'))
        ]
        rows[page] = {
            'tolerances': [
                {kw.arg: ast.literal_eval(kw.value) for kw in n.keywords}
                for n in sorted(bounds, key=lambda n: n.lineno)
            ],
            'reference_directory': directory,
            'files': {
                name: hashlib.sha256(
                    frozen(f'knowledge/verification/fullprof/{directory}/{name}')
                ).hexdigest()
                for name in names
            },
        }
    (Path(__file__).parent / 'page_pins.json').write_text(
        json.dumps(
            {
                'base': BASE,
                'classification': (
                    'Existing page bounds are regression pins; '
                    'FullProf files are independent references'
                ),
                'pages': rows,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
