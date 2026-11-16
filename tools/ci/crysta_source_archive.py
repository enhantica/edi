# SPDX-License-Identifier: BSD-3-Clause
"""Append source receipts and extract SDK source archives using native Python paths."""

import argparse
import os
import posixpath
import shutil
import sys
import tarfile
from pathlib import Path

RECEIPT = 'runner-source-objects.json'


def append_receipt(archive: Path, receipt: Path) -> None:
    """Add exactly one producer-owned receipt to the uncompressed Git archive."""
    with tarfile.open(archive, 'a') as output:
        if RECEIPT in output.getnames():
            raise ValueError('Source archive already contains a source-object receipt')
        output.add(receipt, arcname=RECEIPT)


def extract(archive: Path, destination: Path) -> None:
    """Extract the source with the same data filter as the SDK reader."""
    with tarfile.open(archive) as source:
        members = source.getmembers()
        # Windows cannot follow a link whose target is spelled with '/', and a tree walk over
        # one fails, so there each link becomes a copy of the file it names.
        links = [member for member in members if member.issym()] if os.name == 'nt' else []
        source.extractall(destination, [m for m in members if m not in links], filter='data')
        for link in links:
            folder = posixpath.dirname(link.name)
            target = posixpath.normpath(posixpath.join(folder, link.linkname))
            if target.startswith('../') or posixpath.isabs(target):
                raise ValueError(f'{link.name} links outside the source: {link.linkname}')
            copy = destination / link.name
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(destination / target, copy)


def main() -> int:
    """Run the common source archive operation without a shell archive operand."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    append = commands.add_parser('append')
    append.add_argument('archive', type=Path)
    append.add_argument('receipt', type=Path)
    unpack = commands.add_parser('extract')
    unpack.add_argument('archive', type=Path)
    unpack.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'append':
            append_receipt(args.archive, args.receipt)
        else:
            extract(args.archive, args.destination)
    except (OSError, ValueError, tarfile.TarError) as error:
        print('source-archive: REFUSED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
