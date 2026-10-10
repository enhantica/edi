# SPDX-License-Identifier: BSD-3-Clause
"""Merge the system parts' recorded test durations into one file for the next CI run.

    merge_test_durations.py --recorded R --out OUT PART [PART ...]

Each part (tools/ci/system-tests-part.sh) starts from the recorded durations R and writes them back
with its own tests' new times, so a part's file differs from R only where that part ran a test. The
merge keeps R, takes every entry a part changed or added, and drops tests whose file is gone. A
missing R counts as empty (the first run).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'merge_test_durations: {path} is not a JSON object')
    return {str(k): float(v) for k, v in data.items()}


def merge(
    recorded: dict[str, float], parts: list[dict[str, float]], root: Path
) -> dict[str, float]:
    out = dict(recorded)
    for part in parts:
        out.update({test: s for test, s in part.items() if recorded.get(test) != s})
    return {
        test: seconds
        for test, seconds in sorted(out.items())
        if (root / test.split('::', 1)[0]).is_file()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--recorded', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('parts', type=Path, nargs='+')
    args = parser.parse_args(argv)
    merged = merge(read(args.recorded), [read(p) for p in args.parts], Path.cwd())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'merge_test_durations: {len(merged)} tests recorded in {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
