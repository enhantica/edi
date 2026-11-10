#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Move or check the crysta commit edi builds (edi ADR-0083).

  crysta_sdk_pin.py <40-hex sha>    write it as CRYSTA_COMMIT in pixi.toml
  crysta_sdk_pin.py --check         is a single, well-formed commit pinned?

edi's CI builds the pinned commit's SDK itself (.github/workflows/crysta-sdk.yml), so moving the
pin is the whole update: nothing has to be published by crysta first.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crysta_sdk  # THE pin reader, beside this file

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(r'(?m)^CRYSTA_COMMIT *= *"[0-9a-f]{40}" *$')


def pin(argv: list[str], path: Path) -> str:
    """Pin a commit, or check the pin; the line to print. Refuses by raising."""
    text = path.read_text(encoding='utf-8')
    if len(LINE.findall(text)) != 1:
        crysta_sdk.refuse('pixi.toml must pin exactly one CRYSTA_COMMIT line')
    if argv == ['--check']:
        return f'crysta-sdk-pin: edi builds crysta {crysta_sdk.pinned(text)}'
    if len(argv) != 1 or not re.fullmatch(r'[0-9a-f]{40}', argv[0]):
        crysta_sdk.refuse(f'usage: crysta_sdk_pin.py <40-hex sha> | --check (got {argv})')
    path.write_text(LINE.sub(f'CRYSTA_COMMIT = "{argv[0]}"', text), encoding='utf-8')
    return f'crysta-sdk-pin: pinned crysta {argv[0]}'


def main(argv: list[str]) -> int:
    """Pin or check; a refusal exits 1."""
    try:
        line = pin(argv, ROOT / 'pixi.toml')
    except crysta_sdk.RefusedError as refusal:
        print(f'crysta-sdk-pin: REFUSED — {refusal}', file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
