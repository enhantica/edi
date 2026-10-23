"""Freeze the owner's keep-all catalogue identity, never RGB correctness values."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVISION = '3b84a607'


def main():
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', REVISION, '--', 'data/colormaps'],
        cwd=ROOT,
        text=True,
    ).splitlines()
    maps = sorted(Path(name).stem for name in names if name.endswith('.tsv'))
    if len(maps) != 28:
        raise ValueError('The owner-approved keep-all inventory must name exactly 28 maps')
    target = ROOT / 'tests/fixtures/scan_views/offered.json'
    target.write_text(
        json.dumps(
            {
                'authority': 'owner decision 3b42802d3',
                'inventory_revision': REVISION,
                'reference_kind': (
                    'owner-authorized existing-name regression pin; RGB tables are independent'
                ),
                'maps': maps,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
