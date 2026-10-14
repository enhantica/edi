"""Compare interval medians with the unchanged ratio bound; exit non-zero on a breach."""

import collections
import statistics
import sys
from pathlib import Path

path, bound = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 1.05
runs = collections.defaultdict(list)
with Path(path).open(encoding='utf-8') as stream:
    for line in stream:
        build, interval, seconds = line.split('\t')
        runs[build, interval].append(float(seconds))
failed = False
print('interval\tbaseline median s\tfixed median s\tratio\tbaseline runs\tfixed runs\tverdict')
for interval in sorted({interval for _, interval in runs}):
    base, fixed = runs.get(('base', interval)), runs.get(('fixed', interval))
    if not base or not fixed:
        print(f'{interval}\tmissing runs')
        failed = True
        continue
    ratio = statistics.median(fixed) / statistics.median(base)
    verdict = 'pass' if ratio <= bound else 'FAIL'
    failed = failed or verdict == 'FAIL'
    print(
        f'{interval}\t{statistics.median(base):.3f}\t{statistics.median(fixed):.3f}\t{ratio:.3f}\t'
        f'{",".join(f"{s:.2f}" for s in base)}\t{",".join(f"{s:.2f}" for s in fixed)}\t{verdict}'
    )
sys.exit(1 if failed else 0)
