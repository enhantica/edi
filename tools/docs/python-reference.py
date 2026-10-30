#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Find Python access paths by traversing the bound model and its committed category census."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import edi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    census = json.loads((root / 'data/category-census.json').read_text())
    members = {entry['member'].split('::')[-1] for entry in census['members']}
    excluded = {
        'structure',
        'experiment',
        'parameters',
        'free_parameters',
        'geometry',
        'geom_bond',
        'expanded_atom_sites',
        'atom_sites_cartn_transform',
        'space_group_symop',
        'refln',
        'data',
    }
    references: dict[str, set[str]] = {}
    examples = json.loads((root / 'app/examples/metadata.json').read_text())['examples']
    loaded = []
    for example in examples:
        folder = root / 'docs/user/cli' / example / 'project'
        project = edi.Project.load(folder)
        loaded.append(example)

        def walk(obj, path: str, depth: int = 0) -> None:
            if (
                obj is None
                or depth > 6
                or isinstance(obj, (str, bytes, int, float, bool, edi.Parameter))
            ):
                return
            cls = type(obj)
            if cls.__module__ not in {'edi._edi', 'edi'}:
                return
            for category in census['categories']:
                owner_name = category.get('owner', category.get('row', ''))
                owner = getattr(edi, owner_name, None)
                if not isinstance(owner, type) or not isinstance(obj, owner):
                    continue
                for column in category['columns']:
                    member = column['member'].split('::')[-1]
                    if not hasattr(obj, member):
                        continue
                    value = getattr(obj, member)
                    if callable(value):
                        continue
                    for item in column.get('items', []):
                        uid = category['name'].lstrip('_') + '.' + item
                        references.setdefault(uid, set()).add(path + '.' + member)
            if hasattr(obj, '__len__') and hasattr(obj, '__getitem__'):
                if len(obj):
                    walk(obj[0], path + '[0]', depth + 1)
                return
            for name in sorted(set(dir(obj)) & members - excluded):
                value = getattr(obj, name)
                if not callable(value):
                    walk(value, path + '.' + name, depth + 1)

        walk(project, 'project')
    args.output.write_text(
        json.dumps(
            {
                'edi_build_commit': edi.__build_commit__,
                'examples': loaded,
                'paths': {key: sorted(values) for key, values in sorted(references.items())},
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
