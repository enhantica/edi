"""Re-pin only default-dependent CLI regression fields; keep every reference and bound."""

import argparse
import json
from pathlib import Path

from tools.checks import cli_projects as runner

ROOT = Path(__file__).resolve().parents[3]


def adapt(case):
    path = ROOT / 'docs/user/cli' / case / 'expected.json'
    document = json.loads(path.read_text())
    original_deviations = runner._deviations
    original_conditions = runner.declare_conditions
    original_json_loads = runner.json.loads
    updates = []

    def old_conditions(project, conditions):
        analysis = project / 'analysis/analysis.edi'
        if '_minimizer.chi_square_tolerance ' not in analysis.read_text():
            conditions = {'chi_square_tolerance': '1e-6', **conditions}
        original_conditions(project, conditions)

    runner.declare_conditions = old_conditions
    old_errors = runner.run_project(ROOT, case)
    runner.declare_conditions = original_conditions
    if old_errors:
        raise ValueError(f'{case}: former-stop control misses old pins: {old_errors}')

    def pin(name, spec, measured):
        errors = original_deviations(name, spec, measured)
        if errors and spec['kind'] == 'regression-pin':
            updates.append({'field': name, 'before': spec['value'], 'after': measured})
            spec['value'] = measured
            return original_deviations(name, spec, measured)
        return errors

    # The runner owns variant preparation and scan reporting; use its real measurement
    # boundary and retain the exact document objects it compares.
    runner.json.loads = lambda raw, *a, **kw: (
        document if raw == path.read_text() else original_json_loads(raw, *a, **kw)
    )
    runner._deviations = pin
    try:
        errors = runner.run_project(ROOT, case)
    finally:
        runner._deviations = original_deviations
        runner.json.loads = original_json_loads
    if errors:
        raise ValueError(
            f'{case}: current defaults miss unchanged scientific references: {errors}'
        )
    path.write_text(json.dumps(document, indent=2) + '\n')
    return {'case': case, 'old_stop_control': 'green', 'changed_regression_fields': updates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', nargs='+')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    receipt = []
    for case in args.cases:
        print(case, flush=True)
        receipt.append(adapt(case))
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
