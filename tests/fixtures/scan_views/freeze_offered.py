"""Freeze the approved map names independently of the implementation."""

import json
from pathlib import Path


def main():
    target = Path(__file__).with_name('offered.json')
    target.write_text(
        json.dumps(
            {
                'reference_kind': (
                    'Approved map inventory, 2026-10-26; '
                    'published RGB tables are independent'
                ),
                'maps': ['blue-red', 'viridis', 'batlow', 'inferno', 'lapaz', 'greys'],
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
