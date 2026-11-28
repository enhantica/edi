"""Regenerate GUI expectations from the independent spglib census.

Pass the public crysta fixtures directory holding generate_census.py and reference.py.
No product module is imported. The output is self-contained at test runtime.
"""

import argparse
import json
import math
import sys
from pathlib import Path


def pmmm_origin_allows_moment(operators):
    # In primitive Pmmm every operation fixes the origin. Its rotations are diagonal
    # sign changes, so a surviving axial component must have +1 for every action.
    actions = []
    for operation in operators:
        *coordinates, sign = operation.split(',')
        assert all(
            value in {axis, '-' + axis} for value, axis in zip(coordinates, 'xyz', strict=True)
        ), 'The Pmmm origin oracle requires unshifted diagonal operations'
        diagonal = [(-1 if value.startswith('-') else 1) for value in coordinates]
        actions.append([int(sign) * math.prod(diagonal) * entry for entry in diagonal])
    return any(all(value == 1 for value in column) for column in zip(*actions, strict=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference_directory', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.reference_directory.resolve()))
    from generate_census import census  # noqa: PLC0415 - explicit independent reference

    result = {}
    for tag, k in [('half', ('1/2', '0', '0')), ('third', ('1/3', '0', '0'))]:
        value = census(292, k)
        result[tag] = {
            'cell': value['cell'],
            'nodes': [
                {key: node[key] for key in ['bns', 'row', 'fm', 'domains', 'parents']}
                for node in value['classes']
            ],
        }
    # Hall symbol -P 2 2 (Pmmm), the independent origin in note-longitudinal.
    from spglib import get_spacegroup_type  # noqa: PLC0415 - optional generator dependency

    hall = next(i for i in range(1, 531) if get_spacegroup_type(i).number == 47)
    origin_classes = census(hall, ('0', '0', '0'))['classes']
    result['pmmmOrigin'] = {
        'allowed': sorted(
            node['bns'] for node in origin_classes if pmmm_origin_allows_moment(node['members'][0])
        ),
        'forbidden': sorted(
            node['bns']
            for node in origin_classes
            if not pmmm_origin_allows_moment(node['members'][0])
        ),
    }
    (Path(__file__).parent / 'graph_oracle.js').write_text(
        '.pragma library\nvar expected = ' + json.dumps(result, indent=2) + ';\n'
    )


if __name__ == '__main__':
    main()
