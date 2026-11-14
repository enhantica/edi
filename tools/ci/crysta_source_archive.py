# SPDX-License-Identifier: BSD-3-Clause
"""Append source receipts and extract SDK source archives using native Python paths."""

import argparse
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
        source.extractall(destination, filter='data')


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
