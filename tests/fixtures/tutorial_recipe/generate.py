"""Freeze declared docs recipes and their source custody; never read the built-in manifest."""

import hashlib
import json
import sys
from pathlib import Path

from reference import boundary_contracts

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/docs'))
from app_tutorial_plan import free_lists, plan  # noqa: E402

CASES = [
    'pd-neut-cwl_lbco-hrpt',
    'pd-neut-cwl_cosio-d20',
    'pd-neut-cwl_cosio-d20_2k',
    'pd-neut-cwl_lmo-echidna',
    'pd-neut-tof_ferrite-austenite-beer',
    'pd-xray-cwl_lam7o3-p021',
    'sc-neut-tof_taurine-senju',
    'pd-neut-cwl_y2o3-spodi',
    'pd-neut-tof_si-sepd',
]


def build():
    output = {}
    for case in CASES:
        print('docs recipe', case, flush=True)
        paths = [
            ROOT / 'tools/docs/app_tutorial_plan.py',
            ROOT / 'docs/user/tutorials' / (case + '.py'),
            ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (case + '.md'),
        ]
        paths += sorted((ROOT / 'docs/user/cli' / case / 'project').rglob('analysis*.edi'))
        output[case] = {
            'plan': plan(case),
            'fits': [(title, sorted(paths)) for title, paths in free_lists(case)],
            'sources': {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            },
        }
    for recipe in output.values():
        recipe['boundaries'] = boundary_contracts(recipe)
    return output


if __name__ == '__main__':
    Path(__file__).with_name('recipes.json').write_text(
        json.dumps(build(), indent=2, ensure_ascii=False) + '\n'
    )
