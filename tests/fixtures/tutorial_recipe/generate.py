"""Freeze declared docs recipes and their source custody; never read the built-in manifest."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests.fixtures.tutorial_recipe.reference import boundary_contracts  # noqa: E402

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
    sys.path.insert(0, str(ROOT / 'tools/docs'))
    from app_tutorial_plan import (  # noqa: PLC0415 - only full recipe regeneration loads production planning
        free_lists,
        plan,
    )

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
                path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            },
        }
    for recipe in output.values():
        recipe['boundaries'] = boundary_contracts(recipe)
    return output


def refresh_page_custody(document, root=ROOT):
    """Refresh published-page transport and derived input checks; preserve every frozen action."""
    output = copy.deepcopy(document)
    for case, recipe in output.items():
        page = 'website/surfaces/docs/cli/tutorials/cases/' + case + '.md'
        for relative, digest in recipe['sources'].items():
            path = root / relative
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Recipe custody refuses an external source: ' + relative)
            current = hashlib.sha256(path.read_bytes()).hexdigest()
            if current != digest and relative != page:
                raise ValueError(
                    'Only page transport may change; review the recipe source: ' + relative
                )
            recipe['sources'][relative] = current
        recipe['boundaries'] = boundary_contracts(recipe)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-page-custody', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).with_name('recipes.json')
    document = (
        refresh_page_custody(json.loads(path.read_text()))
        if args.refresh_page_custody
        else build()
    )
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')
