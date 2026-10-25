"""Paired live timings; samples must come from the committed native baseline route."""

import math
from statistics import median


def measured_median(samples):
    values = list(samples)
    if len(values) < 3 or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError('A timing comparison needs repeated finite positive live samples')
    return median(values)


def redraw_comparison(before, after):
    """Return the measured medians and the packet's absolute redraw result, in ms."""
    old, new = measured_median(before), measured_median(after)
    return {'before_ms': old, 'after_ms': new, 'under_100_ms': new < 100}


def fit_comparison(every_pattern, adaptive):
    """Compare the paired project's two real app update modes on the same machine."""
    ratio = measured_median(every_pattern) / measured_median(adaptive)
    return {'ratio': ratio, 'within_five_percent': ratio <= 1.05}


def slider_comparison(before_fit, after_fit, baseline_noise_ms):
    """Use the committed repeatability measurement, never an invented noise margin."""
    if not math.isfinite(baseline_noise_ms) or baseline_noise_ms < 0:
        raise ValueError('Slider repeatability must be a finite measured noise interval')
    before, after = measured_median(before_fit), measured_median(after_fit)
    return {
        'before_ms': before,
        'after_ms': after,
        'within_noise': abs(after - before) <= baseline_noise_ms,
    }
