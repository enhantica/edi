"""Compare a wasm fit record with the independent native CLI reference."""

import math


def compare(record, oracle):
    fields = dict(line.split('=', 1) for line in record.splitlines() if '=' in line)
    for key in ('status', 'converged'):
        if fields.get(key) != oracle[key]:
            raise ValueError(f'wasm fit {key} disagrees with the native CLI')
    expected = {**oracle['parameters'], 'reduced_chi_square': oracle['reduced_chi_square']}
    for key, reference in expected.items():
        try:
            actual = float(fields[key])
        except (KeyError, ValueError) as error:
            raise ValueError(f'wasm fit is missing a numeric native quantity: {key}') from error
        if not math.isfinite(actual) or not math.isclose(
            actual,
            reference,
            rel_tol=oracle['relative_tolerance'],
            abs_tol=oracle['absolute_tolerance'],
        ):
            raise ValueError(f'wasm fit {key} differs from the independent native value')
