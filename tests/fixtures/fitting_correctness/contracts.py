"""Independent 222/mmm orbits and weighted normal equations, never engine outputs.

222 has identity and the three rotations changing two coordinate signs; adding
inversion gives mmm. I centring requires h+k+l even (International Tables).
SHELXL OMIT applies to the final reduced index, thus to every orbit member.
Merge mean/su: CCSL WTMEAN; Rint: repeated input observations; R-sigma: cctbx.
"""

import json
from pathlib import Path

from tests.fixtures.fitting_correctness.admission import exclusion, merged, region, stage

INDEX_ROWS = [
    (1, 2, 3, 10, 1),
    (1, 2, 3, 16, 2),
    (-1, -2, 3, 28, 3),
    (-1, -2, -3, 45, 1),
    (1, 2, -3, 52, 2),
    (1, 2, 4, 70, 1),
    (1, 3, 3, 90, 3),
    (2, 2, 3, 110, 2),
]
RICH_ROWS = [
    (1, 1, 2, 10, 1),
    (-1, -1, 2, 14, 2),
    (-1, -1, -2, 26, 1.5),
    (2, 1, 1, 40, 1),
    (-2, -1, 1, 44, 2),
    (-2, -1, -1, 50, 3),
    (2, 2, 2, 1, 1),
    (4, 0, 0, 10000, 1),
    (-4, 0, 0, 20000, 2),
    (1, 1, 1, 90, 1),
    (3, 1, 2, 100000, 1),
    (4, 2, 0, 70, 1),
    (4, 4, 0, 80, 2),
]
DECLARATIONS = (
    '_reflns.merge laue_class\n_reflns.absences exclude\n'
    + exclusion(4, 0, 0)
    + region('d_spacing', 1.60, 1.61)
)


def orbit(hkl, mode, *, centrosymmetric=False):
    h, k, ell = hkl
    proper = {(h, k, ell), (h, -k, -ell), (-h, k, -ell), (-h, -k, ell)}
    return (
        proper | {tuple(-v for v in row) for row in proper}
        if (mode == 'laue_class' or centrosymmetric)
        else proper
    )


def partition(rows, mode, *, centrosymmetric=False, omit=None):
    groups = {}
    excluded = []
    omitted = (
        set()
        if omit is None
        else (
            {tuple(omit)} if mode == 'none' else orbit(omit, mode, centrosymmetric=centrosymmetric)
        )
    )
    for i, row in enumerate(rows):
        hkl = tuple(row[:3])
        if hkl in omitted:
            excluded.append(i)
            continue
        key = i if mode == 'none' else min(orbit(hkl, mode, centrosymmetric=centrosymmetric))
        groups.setdefault(key, []).append(i)
    return list(groups.values()), excluded


def summary(rows, groups, *, excluded=(), absent=(), cutoff=None, mode='laue_class'):
    reduced, rint, _ = merged(rows, groups)
    used_indices = [
        i for i, (mean, su) in enumerate(reduced) if cutoff is None or mean > cutoff * su
    ]
    used = [reduced[i] for i in used_indices]
    weights = [su**-2 for _, su in used]
    # Origin Ni at (0,0,0) and the I-centring translation (1/2,1/2,1/2):
    # F²(hkl) = b² [1 + (-1)^(h+k+l)]². An included absence has C=0,
    # so it stays in the residual but adds nothing to either scale sum.
    calculated = [1.03**2 * (1 + (-1) ** sum(rows[groups[i][0]][:3])) ** 2 for i in used_indices]
    scale = sum(
        w * mean * calc for w, (mean, _), calc in zip(weights, used, calculated, strict=True)
    ) / sum(w * calc**2 for w, calc in zip(weights, calculated, strict=True))
    return {
        'measured': len(rows),
        'unique': len(groups),
        'used': len(used),
        'excluded': len(excluded),
        'absent': len(absent),
        'mode': mode,
        'rint': rint if mode != 'none' else None,
        'rsigma': sum(row[1] for row in used) / sum(row[0] for row in used),
        'scale': scale,
        'groups': groups,
        'reduced': reduced,
    }


def rich_reference(rows=None):
    rows = RICH_ROWS if rows is None else rows
    return summary(
        rows, [[0, 1, 2], [3, 4, 5], [6], [11], [12]], excluded=[7, 8, 10], absent=[9], cutoff=2
    )


def generate():
    directory = Path(__file__).parent
    other_groups, _ = partition(RICH_ROWS, 'point_group')
    other = summary(RICH_ROWS, other_groups, mode='point_group', absent=[9], cutoff=2)
    replacement = [(*row[:3], row[3] * 1.7, row[4]) for row in RICH_ROWS]
    expected = {
        'bank': rich_reference(),
        'other': other,
        'replacement': rich_reference(replacement),
    }
    (directory / 'admission_reference.json').write_text(json.dumps(expected, indent=2) + '\n')
    stage(
        directory / 'admission_project',
        rows=RICH_ROWS,
        group='I 2 2 2',
        declarations=DECLARATIONS,
        cutoff=2,
    )
    (directory / 'admission_project/reference.json').write_text(
        json.dumps(expected, indent=2) + '\n'
    )


if __name__ == '__main__':
    generate()
