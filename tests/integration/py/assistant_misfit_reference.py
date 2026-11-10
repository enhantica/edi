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


def native_peaks(data):
    """Measure connected reflection supports on the original sampled axis."""
    used = population(data)
    if not used:
        return []
    x = data['x']
    net = {i: data['calculated'][i] - data['background'][i] for i in used}
    finite_axis = [i for i, value in enumerate(x) if finite(value)]
    groups = []
    for phase in data['phases']:
        for position in phase['positions']:
            if not finite(position) or not x[used[0]] <= position <= x[used[-1]]:
                continue
            if any(lo <= position <= hi for lo, hi in data.get('excluded', [])):
                continue
            center = min(finite_axis, key=lambda i: abs(x[i] - position))
            if center not in net or net[center] <= 0:
                continue
            threshold = fraction(net[center]) / 10
            edges = [
                -1,
                *(i for i in range(len(x)) if i not in net or net[i] <= threshold),
                len(x),
            ]
            lo = max(i for i in edges if i < center) + 1
            hi = min(i for i in edges if i > center)
            support = set(range(lo, hi))
            members = [(position, phase['phase_id'])]
            separate = []
            for earlier, labels in groups:
                if earlier & support:
                    support.update(earlier)
                    members.extend(labels)
                else:
                    separate.append((earlier, labels))
            groups = [*separate, (support, members)]

    result = []
    for support, members in groups:
        position, phase = members[0]
        observed = peak(data, sorted(support), position, phase)
        if len(members) > 1:
            del observed['position'], observed['phase_id']
            observed['members'] = sorted(members)
        result.append(observed)
    return result


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
