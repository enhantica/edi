#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Content identity of the selected installed SDK, independent of restored mtimes (ADR-0017)."""

from __future__ import annotations

import hashlib
import stat
import sys
from pathlib import Path


def identity(prefix: Path) -> str:
    digest = hashlib.sha256(b'edi-sdk-content/1\0')

    def visit(path: Path, relative: str, ancestors: frozenset[Path]) -> None:
        resolved = path.resolve(strict=True)
        mode = path.stat().st_mode
        if stat.S_ISDIR(mode):
            if resolved in ancestors:
                raise ValueError(f'SDK directory cycle: {path}')
            digest.update(b'd\0' + relative.encode() + b'\0')
            for child in sorted(path.iterdir()):
                visit(child, f'{relative}/{child.name}', ancestors | {resolved})
        elif stat.S_ISREG(mode):
            digest.update(b'f\0' + relative.encode() + b'\0')
            content = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    content.update(chunk)
            digest.update(content.digest())
        else:
            raise ValueError(f'Nonregular SDK entry: {path}')

    if not prefix.is_dir():
        raise ValueError(f'SDK prefix is not a directory: {prefix}')
    visit(prefix, '', frozenset())
    return digest.hexdigest()


if __name__ == '__main__':
    try:
        print(identity(Path(sys.argv[1])))
    except (OSError, ValueError, IndexError) as error:
        sys.exit(f'SDK content identity refused: {error}')
