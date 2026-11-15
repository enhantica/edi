"""File-boundary inputs and independent weighted normal equations."""

import shlex

import numpy as np

from tests.fixtures.fitting_correctness.project import materialize

MERGE_ROWS = [
    (1, 0, 0, 10, 1),
    (-1, 0, 0, 14, 2),
    (0, 1, 0, 25, 3),
    (0, -1, 0, 40, 1),
    (0, 0, 1, -2, 2),
    (0, 0, -1, 2, 2),
]


def stage(root, *, rows=None, declarations='', group='P 1', tof=False, cutoff=None):
    root = materialize(root)
    structure = root / 'structures/phase.edi'
    structure.write_text(structure.read_text().replace('"P 1"', f'"{group}"'))
    code = {'P 21/c': 'b1', 'F d -3 m': '2'}.get(group)
    if code:
        structure.write_text(structure.read_text() + f'\n_space_group.coord_system_code {code}\n')
    path = root / 'experiments/bank.edi'
    text = path.read_text().split('loop_\n_refln.index_h')[0]
    text = text.replace('phase 2.3\n', 'phase 2.3()\n')
    if tof:
        text = text.replace('"constant wavelength"', '"time-of-flight"')
        text = text.replace('_instrument.setup_wavelength 0.8\n', '')
    text += (
        declarations + '\nloop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n'
        '_refln.intensity_meas\n_refln.intensity_meas_su\n'
    )
    if tof:
        text += '_refln.wavelength\n'
    for row in rows if rows is not None else MERGE_ROWS:
        text += ' '.join(map(str, row)) + (' 0.8' if tof and len(row) == 5 else '') + '\n'
    path.write_text(text)
    if cutoff is not None:
        analysis = root / 'analysis/analysis.edi'
        analysis.write_text(analysis.read_text() + f'\n_refine_ls.threshold_sigma {cutoff}\n')
    return root


def exclusion(h, k, ell):
    return (
        'loop_\n_excluded_reflection.id\n_excluded_reflection.index_h\n'
        '_excluded_reflection.index_k\n_excluded_reflection.index_l\n'
        f'1 {h} {k} {ell}\n'
    )


def region(axis, start, end):
    return (
        'loop_\n_excluded_region.id\n_excluded_region.start\n'
        f'_excluded_region.end\n_excluded_region.axis\n1 {start} {end} {axis}\n'
    )


def merged(rows, groups):
    results = []
    numerator = denominator = 0.0
    for group in groups:
        values = np.array([rows[index][3] for index in group], dtype=float)
        sigma = np.array([rows[index][4] for index in group], dtype=float)
        weights = sigma**-2
        mean = np.dot(weights, values) / weights.sum()
        propagated = 1 / np.sqrt(weights.sum())
        scatter = (
            np.sqrt(np.dot(weights, (values - mean) ** 2) / ((len(group) - 1) * weights.sum()))
            if len(group) > 1
            else 0
        )
        results.append((mean, max(propagated, scatter)))
        if len(group) > 1:
            numerator += np.abs(values - mean).sum()
            denominator += values.sum()
    r_int = numerator / denominator if denominator else None
    r_sigma = sum(sigma for _, sigma in results) / sum(mean for mean, _ in results)
    return results, r_int, r_sigma


def scalar(text, tag):
    values = [shlex.split(line)[1] for line in text.splitlines() if line.startswith(tag + ' ')]
    if len(values) != 1:
        message = f'The saved calculation must report exactly one {tag}: {values}'
        raise AssertionError(message)
    return float(values[0])


def column(text, tag):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line != 'loop_':
            continue
        cursor = index + 1
        headers = []
        while cursor < len(lines) and lines[cursor].startswith('_'):
            headers.append(lines[cursor])
            cursor += 1
        if tag not in headers:
            continue
        rows = []
        while (
            cursor < len(lines)
            and lines[cursor].strip()
            and not lines[cursor].startswith(('_', 'loop_', 'data_'))
        ):
            tokens = shlex.split(lines[cursor])
            if tokens and not tokens[0].startswith('#'):
                rows.append(tokens[headers.index(tag)])
            cursor += 1
        return rows
    message = f'The saved reflection table must carry {tag}'
    raise AssertionError(message)
