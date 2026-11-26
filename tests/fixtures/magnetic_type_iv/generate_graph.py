"""Regenerate GUI expectations from the independent spglib census.

Pass the public crysta fixtures directory holding generate_census.py and reference.py.
No product module is imported. The output is self-contained at test runtime.
"""

import argparse
import json
import sys
from pathlib import Path


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
    (Path(__file__).parent / 'graph_oracle.js').write_text(
        '.pragma library\nvar expected = ' + json.dumps(result, indent=2) + ';\n'
    )


if __name__ == '__main__':
    main()
