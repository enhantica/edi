#!/usr/bin/env python3
"""Generate edi-data's journal-abbreviations.json from JabRef's journal abbreviation lists.

The From web popup shows a structure's reference with the journal's ISO 4 abbreviation
("Phys. Rev. B"); COD answers only with full names, so the app reads this table from the
EasyDiffraction collection and falls back to the full name for a journal it does not hold. The
lists come from https://github.com/JabRef/abbrv.jabref.org (CC0 1.0); the first list naming a
journal wins.

    python tools/data/build_journal_abbreviations.py <edi-data folder> [--lists general,acs,...]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import urllib.request
from pathlib import Path

REPOSITORY = 'https://github.com/JabRef/abbrv.jabref.org'
RAW = 'https://raw.githubusercontent.com/JabRef/abbrv.jabref.org/main/journals/journal_abbreviations_{name}.csv'
# Enough for the journals crystal structures are published in; the life-science and mathematics
# lists would quadruple the file for journals COD rarely cites.
DEFAULT_LISTS = ('general', 'acs', 'geology_physics', 'ieee')
SCHEMA = 'edi-data-journals/1'


def read_list(name: str, folder: Path | None) -> str:
    if folder is not None:
        return (folder / f'journal_abbreviations_{name}.csv').read_text(encoding='utf-8')
    # A fixed https address built from the list's name, never a caller's URL.
    with urllib.request.urlopen(RAW.format(name=name), timeout=60) as answer:  # noqa: S310
        return answer.read().decode('utf-8')


def merge(texts: list[str]) -> dict[str, str]:
    table: dict[str, str] = {}
    keys: set[str] = set()
    for text in texts:
        for row in csv.reader(io.StringIO(text)):
            if len(row) < 2:
                continue
            full, short = row[0].strip(), row[1].strip()
            if not full or not short or full.lower() == short.lower():
                continue
            key = ''.join(c for c in full.lower() if c.isalnum())
            if key in keys:
                continue  # the first list naming a journal wins
            keys.add(key)
            table[full] = short
    return dict(sorted(table.items(), key=lambda item: item[0].lower()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('output', type=Path, help='the edi-data folder')
    parser.add_argument(
        '--lists', default=','.join(DEFAULT_LISTS), help='comma-separated JabRef list names'
    )
    parser.add_argument(
        '--from',
        dest='folder',
        type=Path,
        help='read the CSV files from this folder instead of GitHub',
    )
    args = parser.parse_args()
    lists = [name for name in args.lists.split(',') if name]
    table = merge([read_list(name, args.folder) for name in lists])
    document = {
        'schema': SCHEMA,
        'source': f'{REPOSITORY} (CC0 1.0), lists: {", ".join(lists)}',
        'generated': dt.datetime.now(tz=dt.UTC).date().isoformat(),
        'abbreviations': table,
    }
    target = args.output / 'journal-abbreviations.json'
    target.write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{target}: {len(table)} journals from {len(lists)} list(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
