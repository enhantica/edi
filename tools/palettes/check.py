# SPDX-License-Identifier: BSD-3-Clause
"""Check data/palettes/edi-*.tsv against data/palettes/PROVENANCE.md (edi ADR-0038).

The approved colours are stored, never generated, so this script only reads: each table lists
five measured, five structure and three role colours, every one `#RRGGBB`, and PROVENANCE.md's
stored-values table for the palette lists the same values in the same order. It exits 1 naming
the first difference.

    python tools/palettes/check.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PALETTES = ROOT / 'data' / 'palettes'
# In edi::ColourScheme's order, as cmake/edi_core_sources.cmake embeds them.
NAMES = {
    'edi-natural': 'Edi Natural',
    'edi-coast': 'Edi Coast',
    'edi-garden': 'Edi Garden',
    'edi-studio': 'Edi Studio',
    'edi-contrast': 'Edi Contrast',
}
ROLES = ['measured'] * 5 + ['structure'] * 5 + ['total_calculation', 'background', 'difference']
INDICES = [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 0, 0]
HEX = re.compile(r'#[0-9A-F]{6}')


def table_rows(stem: str) -> list[tuple[str, int, str, str]]:
    lines = (PALETTES / f'{stem}.tsv').read_text(encoding='utf-8').splitlines()
    if lines[0] != 'role\tindex\tlight\tdark':
        raise ValueError(f'{stem}.tsv: the header is not role, index, light, dark')
    rows = []
    for line in lines[1:]:
        role, index, light, dark = line.split('\t')
        rows.append((role, int(index), light, dark))
    return rows


def provenance_rows(text: str, title: str) -> list[tuple[str, int, str, str]]:
    section = text.split(f'\n### {title}\n', 1)[1].split('\n### ', 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 7 and cells[1].isdigit():
            rows.append((cells[0], int(cells[1]), cells[3].strip('`'), cells[5].strip('`')))
    return rows


def main() -> int:
    found = sorted(path.stem for path in PALETTES.glob('*.tsv'))
    if found != sorted(NAMES):
        print(f'data/palettes holds {found}, not the five palettes {sorted(NAMES)}')
        return 1
    provenance = (PALETTES / 'PROVENANCE.md').read_text(encoding='utf-8')
    for stem, title in NAMES.items():
        rows = table_rows(stem)
        if [(role, index) for role, index, _, _ in rows] != list(zip(ROLES, INDICES, strict=True)):
            print(f'{stem}.tsv: not five measured, five structure and three role colours')
            return 1
        for role, index, light, dark in rows:
            if not (HEX.fullmatch(light) and HEX.fullmatch(dark)):
                print(f'{stem}.tsv: {role} {index} is not #RRGGBB in both themes')
                return 1
        if provenance_rows(provenance, title) != rows:
            print(f'{stem}.tsv and PROVENANCE.md list different colours for {title}')
            return 1
    print('data/palettes: five palettes, each equal to PROVENANCE.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
