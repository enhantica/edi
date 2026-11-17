"""Declare a long report table independently of report output."""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--pattern-input', type=Path, default=HERE.parent / 'structure_features' / 'neutron.edi'
    )
    source = parser.parse_args().pattern_input
    text = source.read_text().split('loop_\n_data.two_theta')[0]
    text = text.replace('right 64 6', 'right 176 6')
    rows = [[40 + i, 20 + 7 * i, 2 + i % 5] for i in range(137)]
    text += 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    text += ''.join(' '.join(map(str, row)) + '\n' for row in rows)
    structure = (HERE.parent / 'structure_features/cubic-bonded.edi').read_text()
    omitted = ('O2 ', 'O4 ', 'O5 ', 'O6 ')
    (HERE / 'report-structure.edi').write_text(
        '\n'.join(line for line in structure.splitlines() if not line.startswith(omitted)) + '\n'
    )
    (HERE / 'long-table.edi').write_text(text)
    (HERE / 'table-only.edi').write_text(
        text.replace(
            'loop_\n_linked_structure.structure_id\n_linked_structure.scale\ncosio 0\n', ''
        )
    )
    (HERE / 'reference.json').write_text(
        json.dumps(
            {'claim': 'Explicit integer input rows, no report-derived values', 'rows': rows},
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
