#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build every case's record and check that each case has all of it (edi ADR-0080).

    python tools/checks/case_records.py            # check; prints each problem
    python tools/checks/case_records.py --json     # the records, as the collection writes them

A case is a registry row with ``user-facing: true`` (ADR-0048). Its record is built from the
registry row, the case's project folder, its ``PROVENANCE.md``, its ``expected.json`` and the
case id, never written by hand, so nothing in it can drift from what it describes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path('docs/user/cli/projects.yml')
CLI_DIR = Path('docs/user/cli')
SCHEMA = 'edi-case/1'
CATALOGUE = Path('app/examples/metadata.json')
TAGS = Path('app/examples/tags.json')


# The tutorial sections in order, each with its Font Awesome icon (the owner, 2026-11-08), as every
# interface groups and marks its tutorials.
SECTIONS = {
    'Getting started': 'rocket',
    'Powder': 'chart-area',
    'Single crystal': 'cube',
    'Simulation': 'calculator',
    'Multiple datasets': 'layer-group',
}


def section(structure_from: str, case_tags: list[dict[str, str]]) -> str:
    """The case's tutorial section, from its record: the case built by hand opens the tutorials."""
    values = {(tag['facet'], tag['value']) for tag in case_tags}
    if structure_from == 'hand':
        return 'Getting started'
    if ('purpose', 'simulation') in values:
        return 'Simulation'
    if any(facet == 'fittingMode' and value != 'single' for facet, value in values):
        return 'Multiple datasets'
    if ('sampleForm', 'single crystal') in values:
        return 'Single crystal'
    return 'Powder'


def tags(root: Path, case: str) -> list[dict[str, str]] | None:
    """The case's tags in the app's order, as its Examples list shows them; None without an entry.

    Each is ``{facet, value, label}``: the facets and labels of ``tags.json``, the values the
    catalogue derives from the case's project (``tools/dev/example_metadata.py``).
    """
    entry = json.loads((root / CATALOGUE).read_text())['examples'].get(case)
    if entry is None:
        return None
    vocabulary = json.loads((root / TAGS).read_text())['tags']
    values = entry.get('values', {})
    return [
        {'facet': facet, 'value': value, 'label': known.get(value, {}).get('label', '')}
        for facet, known in vocabulary.items()
        for value in values.get(facet, [])
    ]


def tutorials(case: str) -> dict[str, str]:
    """Each interface's tutorial of ``case``, named by the case id."""
    return {
        'python': f'docs/user/tutorials/{case}.ipynb',
        'app': case,
        'app_docs': f'website/surfaces/docs/application/tutorials/cases/{case}.md',
        'cli_docs': f'{CLI_DIR}/{case}/index.md',
    }


def diffraction_lib(row: dict) -> dict[str, str] | None:
    """The diffraction-lib tutorial the case has (``same``) or follows the outline of."""
    if 'diffraction-lib' in row:
        return {'tutorial': str(row['diffraction-lib']), 'match': 'same'}
    if 'follows-diffraction-lib' in row:
        return {'tutorial': str(row['follows-diffraction-lib']), 'match': 'follows'}
    return None


def pin(expected: dict) -> dict | None:
    """The case's regression pins: the ``regression-pin`` quantities and where they came from.

    None until ``expected.json`` names the commit its pins came from (``source.pins``).
    """
    source = expected.get('source', {}).get('pins')
    if not isinstance(source, dict):
        return None
    values = {
        name: quantity['value']
        for name, quantity in expected.get('quantities', {}).items()
        if quantity.get('kind') == 'regression-pin'
    }
    return {**source, 'values': values}


def record(root: Path, row: dict, order: int) -> dict:
    case = str(row['id'])
    folder = root / CLI_DIR / case
    project = folder / 'project'
    expected_path = folder / 'expected.json'
    provenance = folder / 'PROVENANCE.md'
    expected = json.loads(expected_path.read_text()) if expected_path.is_file() else {}
    structure_from = 'hand' if row.get('structure-by-hand') is True else 'collection'
    case_tags = tags(root, case)
    return {
        'schema': SCHEMA,
        'id': case,
        'order': order,
        'provenance': provenance.read_text(encoding='utf-8') if provenance.is_file() else None,
        # The page title, '<sample> on <instrument>', and the one-line navigation title,
        # '<short sample name> <code>' (the owner, 2026-11-08).
        'title': str(row.get('title', '')),
        'nav_title': f'{row["short-name"]} {case.split("_", 1)[0]}'
        if row.get('short-name')
        else '',
        'diffraction_lib': diffraction_lib(row),
        'tags': case_tags,
        'structures': [f'{case}-{f.stem}' for f in sorted((project / 'structures').glob('*.edi'))],
        'experiments': [
            f'{case}-{f.stem}' for f in sorted((project / 'experiments').glob('*.edi'))
        ],
        # The measured pattern of each experiment that holds one, as the collection exports it.
        'data': [
            f'{case}-{f.stem}-data'
            for f in sorted((project / 'experiments').glob('*.edi'))
            if '_data.intensity_meas' in f.read_text(errors='replace')
        ],
        # How every interface's tutorial gets its inputs (the owner, 2026-11-08): the structure
        # built by hand or loaded from the collection's CIF; the data from the collection, and for
        # one case also from a file on the user's disk.
        'structure_from': structure_from,
        'data_from': ['collection', 'file']
        if row.get('data-from-file') is True
        else ['collection'],
        'section': section(structure_from, case_tags or []),
        'section_icon': SECTIONS[section(structure_from, case_tags or [])],
        'pin': pin(expected),
        # The interfaces its tutorials cover (owner record 2026-11-09); all three by default.
        'interfaces': interfaces(row),
        'tutorials': tutorials(case),
    }


INTERFACES = ('app', 'python', 'cli')


def interfaces(row: dict) -> list[str]:
    """The interfaces a case declares (`interfaces: [app]`), or all three."""
    declared = row.get('interfaces')
    return list(INTERFACES) if declared is None else [str(name) for name in declared]


def cases(root: Path) -> list[dict]:
    """The registry rows that are cases, in registry order."""
    rows = yaml.safe_load((root / REGISTRY).read_text(encoding='utf-8'))['projects']
    return [row for row in rows if row.get('user-facing') is True]


def records(root: Path = ROOT) -> list[dict]:
    """Every case's record, in registry order."""
    return [record(root, row, order) for order, row in enumerate(cases(root), start=1)]


# The tutorials this check requires today. The app's built-in tutorials and its pages join when
# the change that adds them lands (ADR-0080 §3).
REQUIRED_TUTORIALS = ('python', 'cli_docs')
REQUIRED_INTERFACE = {'python': 'python', 'cli_docs': 'cli'}


def problems(root: Path = ROOT) -> list[str]:
    """Every case without one of its record's fields or artefacts, named."""
    out = []
    built_records = records(root)
    seen: dict[tuple[str, str], str] = {}
    for built in built_records:
        key = (built['section'], built['nav_title'])
        if built['nav_title'] and key in seen:
            out.append(
                f'{built["id"]}: has the navigation title of {seen[key]} in the section {key[0]}'
            )
        seen.setdefault(key, built['id'])
    for built in built_records:
        case = built['id']
        if not built['provenance']:
            out.append(f'{case}: has no authored PROVENANCE.md disclosure')
        if not built['title'] or not built['nav_title']:
            out.append(f'{case}: {REGISTRY} gives no title or no short-name')
        if built['diffraction_lib'] is None:
            out.append(
                f'{case}: {REGISTRY} gives neither diffraction-lib nor follows-diffraction-lib'
            )
        if not built['tags']:
            out.append(f'{case}: has no tags in {CATALOGUE}')
        else:
            out.extend(
                f'{case}: tag {tag["facet"]} {tag["value"]} has no label in {TAGS}'
                for tag in built['tags']
                if not tag['label']
            )
        if not (root / CLI_DIR / case / 'project' / 'project.edi').is_file():
            out.append(f'{case}: has no example project')
        if not built['structures']:
            out.append(f'{case}: its project has no structure')
        if not built['experiments']:
            out.append(f'{case}: its project has no experiment')
        unknown = sorted(set(built['interfaces']) - set(INTERFACES))
        if unknown or not built['interfaces']:
            out.append(f'{case}: {REGISTRY} declares interfaces {built["interfaces"]}')
        # Only a declared interface's tutorial is required; a missing one elsewhere is by design.
        out.extend(
            f'{case}: {built["tutorials"][kind]} is missing'
            for kind in REQUIRED_TUTORIALS
            if REQUIRED_INTERFACE[kind] in built['interfaces']
            and not (root / built['tutorials'][kind]).is_file()
        )
    # The app's Examples list is the catalogue: exactly the cases, tagged from the one registry.
    # The source, facility and instrument are never tags (owner record 2026-11-09).
    listed = list(json.loads((root / CATALOGUE).read_text())['examples'])
    ids = [built['id'] for built in built_records]
    out.extend(
        f'{CATALOGUE}: lists {extra}, which is not a case' for extra in listed if extra not in ids
    )
    out.extend(f'{CATALOGUE}: does not list the case {case}' for case in ids if case not in listed)
    facets = json.loads((root / TAGS).read_text())['tags']
    out.extend(
        f'{TAGS}: {facet} is a tag facet, but it is never a tag'
        for facet in ('source', 'facilities', 'instruments')
        if facet in facets
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='the edi tree (default: this one)')
    parser.add_argument('--json', action='store_true', help='print the records')
    args = parser.parse_args(argv)
    if args.json:
        print(json.dumps(records(args.root), ensure_ascii=False, indent=1))
        return 0
    found = problems(args.root)
    for problem in found:
        print(problem, file=sys.stderr)
    print(f'case records: {len(records(args.root))} cases, {len(found)} problem(s)')
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
