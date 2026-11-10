# SPDX-License-Identifier: BSD-3-Clause
"""Which experiment types take each setting the Features page's tags name.

The site build checks the Features tags against website/feature_applicability.json, so it never
imports whichever native module happens to be built. This script writes that file from the built
module (`--write`) or compares it (`--check`, part of `pixi run cli-projects`).

    python tools/docs/feature_applicability.py --write | --check
"""

from __future__ import annotations

import argparse
import contextlib
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'website/feature_applicability.json'
sys.path.insert(0, str(ROOT / 'website'))

from render_experiments import feature_code, feature_types  # noqa: E402

KINDS = list(
    itertools.product(
        ('powder', 'single crystal'),
        ('constant wavelength', 'time-of-flight'),
        ('neutron', 'xray'),
    )
)


def code_key(code: dict) -> str:
    """One setting combination as the file names it: `path=value`, sorted, joined by `;`."""
    return ';'.join(f'{path}={value}' for path, value in sorted(code.items()))


def _experiment(edi, kind: tuple[str, str, str]):
    sample_form, beam_mode, probe = kind
    return edi.ExperimentFactory.from_scratch(
        name='probe', sample_form=sample_form, beam_mode=beam_mode, radiation_probe=probe
    )


def _accepts(edi, kind: tuple[str, str, str], code: dict) -> bool:
    experiment = _experiment(edi, kind)
    for path, value in code.items():
        *owners, attribute = path.split('.')
        target = experiment
        try:
            for owner in owners:
                target = getattr(target, owner)
            setattr(target, attribute, value)
        except (AttributeError, ValueError, TypeError):
            return False
    return True


def generate() -> dict:
    """The experiment types edi creates and, per named setting, the types that take it."""
    try:
        import edi  # noqa: PLC0415 - the built module this file records
    except ImportError as error:
        raise SystemExit(
            f'cannot import the built edi module ({error}); rebuild it first'
        ) from error

    kinds = []
    for kind in KINDS:
        with contextlib.suppress(ValueError):
            _experiment(edi, kind)
            kinds.append(kind)
    codes = {code_key(code): code for code in map(feature_code, feature_types()) if code}
    return {
        'types': [list(kind) for kind in kinds],
        'accepts': {
            key: [list(kind) for kind in kinds if _accepts(edi, kind, code)]
            for key, code in sorted(codes.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    # One experiment type per line.
    text = re.sub(
        r'\[\s+("[^"]+"),\s+("[^"]+"),\s+("[^"]+")\s+\]',
        r'[\1, \2, \3]',
        json.dumps(generate(), indent=1, ensure_ascii=False),
    )
    text += '\n'
    if args.write:
        OUTPUT.write_text(text, encoding='utf-8')
        print(f'wrote {OUTPUT.relative_to(ROOT)}')
        return
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding='utf-8') != text:
        raise SystemExit(
            f'{OUTPUT.relative_to(ROOT)} differs from the built module: '
            'run python tools/docs/feature_applicability.py --write'
        )
    print('Features applicability: PASS')


if __name__ == '__main__':
    main()
