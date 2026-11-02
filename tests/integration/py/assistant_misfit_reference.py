"""Closed-form weighted sums and moments over captured or authored columns."""

import math
from fractions import Fraction


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def population(data):
    return [
        i
        for i, (x, m, c, s) in enumerate(
            zip(data['x'], data['measured'], data['calculated'], data['sigma'], strict=True)
        )
        if all(map(finite, (x, m, c, s)))
        and s > 0
        and not any(lo <= x <= hi for lo, hi in data.get('excluded', []))
    ]


def fraction(value):
    return Fraction(float(value))


def weighted(data, indices, against='calculated'):
    values = [
        (fraction(data['measured'][i]) - fraction(data[against][i])) / fraction(data['sigma'][i])
        for i in indices
    ]
    if not values:
        return None
    return float(sum(values) / len(values)), math.sqrt(
        float(sum(v * v for v in values) / len(values))
    )


def peak(data, indices, position, phase):
    residual = [
        (fraction(data['measured'][i]) - fraction(data['calculated'][i]))
        / fraction(data['sigma'][i])
        for i in indices
    ]
    observed = [
        max(Fraction(), fraction(data['measured'][i]) - fraction(data['background'][i]))
        for i in indices
    ]
    calculated = [
        max(Fraction(), fraction(data['calculated'][i]) - fraction(data['background'][i]))
        for i in indices
    ]
    xs = [fraction(data['x'][i]) for i in indices]
    osum, csum = sum(observed), sum(calculated)
    result = {
        'position': position,
        'phase_id': phase,
        'weighted_square_sum': float(sum(v * v for v in residual)),
        'intensity_ratio': float(osum / csum),
    }
    if osum and csum:
        oc = sum(w * x for w, x in zip(observed, xs, strict=True)) / osum
        cc = sum(w * x for w, x in zip(calculated, xs, strict=True)) / csum
        ov = sum(w * (x - oc) ** 2 for w, x in zip(observed, xs, strict=True)) / osum
        cv = sum(w * (x - cc) ** 2 for w, x in zip(calculated, xs, strict=True)) / csum
        result['centroid_shift'] = float(oc - cc)
        if cv:
            result['width_ratio'] = math.sqrt(float(ov / cv))
    return result


def native_windows(data):
    """Contiguous tenth-height support, calculated separately from the app helper."""
    used = population(data)
    net = [data['calculated'][i] - data['background'][i] for i in used]
    supports = {}
    for phase in data['phases']:
        for position in phase['positions']:
            if not finite(position) or not data['x'][used[0]] <= position <= data['x'][used[-1]]:
                continue
            center = min(range(len(used)), key=lambda k: abs(data['x'][used[k]] - position))
            if net[center] <= 0:
                continue
            separators = (
                [-1]
                + [k for k, value in enumerate(net) if value <= net[center] / 10]
                + [len(used)]
            )
            lo = max(k for k in separators if k < center) + 1
            hi = min(k for k in separators if k > center)
            supports.setdefault(lo, (used[lo:hi], position, phase['phase_id']))
    return list(supports.values())


def synthetic():
    """Six separate authored five-row peaks; no window comes from the subject."""
    n = 72
    data = {
        'dataset_id': 'two-phase',
        'axis_kind': 'data.twotheta',
        'current': True,
        'x': [3.25 + i / 8 for i in range(n)],
        'sigma': [1.75 + (i % 5) / 8 for i in range(n)],
        'background': [17.125 + (i % 7) / 4 for i in range(n)],
        'excluded': [],
    }
    data['calculated'] = data['background'].copy()
    data['measured'] = [b + (0.25 if i % 2 else -0.25) for i, b in enumerate(data['background'])]
    windows = []
    phases = {'alpha': [], 'beta': []}
    for j, center in enumerate((7, 17, 27, 37, 47, 57)):
        indices = list(range(center - 2, center + 3))
        phase = 'alpha' if j < 3 else 'beta'
        phases[phase].append(data['x'][center])
        for i, calc, meas in zip(indices, (1, 2, 5, 2, 1), (0.75, 1.25, 4, 3.5, 0.5), strict=True):
            data['calculated'][i] += calc * (j + 1)
            data['measured'][i] += meas * (j + 1) * (1 + j / 8)
        windows.append((indices, data['x'][center], phase))
    data['phases'] = [{'phase_id': key, 'positions': values} for key, values in phases.items()]
    return data, windows
