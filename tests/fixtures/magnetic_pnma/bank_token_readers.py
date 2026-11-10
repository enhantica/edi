"""Bank only successfully measured token-census nodes with the canonical writer."""

import argparse
from pathlib import Path

from tools.checks import per_pr_runtimes as costs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('fixtures', type=Path)
    args = parser.parse_args()
    text = args.log.read_text()
    if text.splitlines()[-1] != 'measurement-condition.pytest_exit=0':
        raise ValueError('Only an actual successful terminal pytest record can bank costs')
    costs._refuse_parallel_log(args.log, text)
    collected = costs.collect_nodeids()
    existing = costs.MANIFEST.read_text()
    kept = {
        n: v
        for n, v in costs._measured_values_in(existing).items()
        if n in collected or '.py::' not in n
    }
    holes = {
        n: why
        for n, why in costs._unmeasured_reasons(existing).items()
        if n in collected or '.py::' not in n
    }
    observed = costs.parse_durations(text)
    targets = sorted(n for n in collected if n in observed and n not in kept and n not in holes)
    rows, new_holes, shared = costs._focused_rows(args.log, args.fixtures, targets)
    if new_holes:
        raise ValueError('This producer banks successful nodes only: ' + repr(new_holes))
    module_costs = costs._banked_module_costs(existing, collected)
    module_costs.update(shared)
    costs._write_banked(
        {**kept, **rows},
        holes,
        module_costs,
        f'{args.log.name}: {len(rows)} measured token-census nodes',
        collected,
    )


if __name__ == '__main__':
    main()
