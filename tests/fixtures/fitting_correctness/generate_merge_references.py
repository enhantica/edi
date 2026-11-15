"""Generate independent merging references from the frozen measured reflection lists."""

import hashlib
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

HOME = Path(__file__).resolve().parent
SOURCE = HOME.parent / 'single_crystal/fullprof.json'
CASES = {'tbti': 'sc-neut-cwl_tbti_basic', 'taurine': 'sc-neut-tof_taurine_basic'}


def orbit(hkl, kind):
    h, k, ell = hkl
    if kind == 'tbti':
        return tuple(sorted(map(abs, hkl)))
    return min((h, k, ell), (-h, k, -ell), (-h, -k, -ell), (h, -k, ell))


def absent(hkl, kind):
    h, k, ell = hkl
    if kind == 'taurine':
        return (h == 0 and ell == 0 and k % 2 != 0) or (k == 0 and ell % 2 != 0)
    if len({coordinate % 2 for coordinate in hkl}) != 1:
        return True
    return 0 in hkl and sum(hkl) % 4 != 0


def merge(rows, kind):
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        groups[orbit(row[:3], kind)].append((index, row))
    output = []
    r_numerator = Decimal(0)
    r_denominator = Decimal(0)
    for key, values in sorted(groups.items()):
        intensities = [Decimal(str(row[3])) for _, row in values]
        sigmas = [Decimal(str(row[4])) for _, row in values]
        weights = [1 / sigma**2 for sigma in sigmas]
        total = sum(weights)
        mean = (
            sum(w * intensity for w, intensity in zip(weights, intensities, strict=True)) / total
        )
        propagated = (1 / total).sqrt()
        n = len(values)
        scatter = (
            (sum((i - mean) ** 2 for i in intensities) / (n * (n - 1))).sqrt()
            if n > 1
            else Decimal(0)
        )
        weighted_scatter = (
            (
                sum(w * (i - mean) ** 2 for w, i in zip(weights, intensities, strict=True))
                / ((n - 1) * total)
            ).sqrt()
            if n > 1
            else Decimal(0)
        )
        if n > 1:
            r_numerator += sum(abs(i - mean) for i in intensities)
            r_denominator += sum(intensities)
        output.append({
            'hkl': list(key),
            'indices': [index for index, _ in values],
            'intensity': str(mean),
            'propagated_su': str(propagated),
            'shelx_scatter_su': str(scatter),
            'weighted_scatter_su': str(weighted_scatter),
            'weighted_merged_su': str(max(propagated, weighted_scatter)),
            'shelx_merged_su': str(max(propagated, scatter)),
        })
    denominator = sum(Decimal(row['intensity']) for row in output)
    return {
        'rows': output,
        'r_int': str(r_numerator / r_denominator) if r_denominator else None,
        'r_sigma_weighted': str(
            sum(Decimal(row['weighted_merged_su']) for row in output) / denominator
        )
        if denominator
        else None,
        'r_sigma_shelx': str(sum(Decimal(row['shelx_merged_su']) for row in output) / denominator)
        if denominator
        else None,
    }


def main():
    source = json.loads(SOURCE.read_text())['cases']
    result = {
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'convention': (
            'SHELX-97 section 2; unweighted rms about the weighted mean divided by sqrt(n-1). '
            'Weighted scatter is retained separately, not chosen for the product.'
        ),
        'cases': {},
    }
    with localcontext() as context:
        context.prec = 50
        for kind, case in CASES.items():
            rows = source[case]['input_rows']
            result['cases'][kind] = {
                'input_rows': rows,
                'systematic_absence_indices': [
                    i for i, row in enumerate(rows) if absent(row[:3], kind)
                ],
                'laue_include_absences': merge(rows, kind),
                'friedel_duplicate_witness': merge(
                    [list(row) for row in rows[:3]]
                    + [
                        [-row[0], -row[1], -row[2], row[3] + 4 * row[4], 2 * row[4], *row[5:]]
                        for row in rows[:3]
                    ],
                    kind,
                ),
                'laue_exclude_absences': merge(
                    [row for row in rows if not absent(row[:3], kind)], kind
                ),
            }
    (HOME / 'merge_reference.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
