"""Paired live timings; samples must come from the committed native baseline route."""

import math
from statistics import median


def measured_median(samples):
    values = list(samples)
    if len(values) < 3 or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError('A timing comparison needs repeated finite positive live samples')
    return median(values)


def backend_identity(backend):
    """Keep the observed graphics API and renderer together in every timing row."""
    api, renderer = backend.get('api'), backend.get('renderer')
    if (
        not isinstance(api, str)
        or not api.strip()
        or not isinstance(renderer, str)
        or (api.lower() == 'opengl' and not renderer.strip())
    ):
        raise ValueError('Timing evidence needs the observed graphics API and renderer')
    software = 'llvmpipe' in renderer.lower()
    if software and api.lower() != 'opengl':
        raise ValueError('The no-GPU timing case must use llvmpipe OpenGL')
    return {'api': api, 'renderer': renderer, 'llvmpipe': software}


def redraw_comparison(before, after, *, backend):
    """Return the measured medians and the packet's absolute redraw result, in ms."""
    old, new = measured_median(before), measured_median(after)
    return {
        'backend': backend_identity(backend),
        'before_ms': old,
        'after_ms': new,
        'under_100_ms': new < 100,
    }


def fit_comparison(display_catches_up, adaptive, *, backend, tab):
    """Compare the paired project's two real app update modes on the same machine."""
    if tab not in {'pattern', 'stacked'}:
        raise ValueError('Fit timings must name the Pattern or Stacked tab')
    ratio = measured_median(display_catches_up) / measured_median(adaptive)
    return {
        'backend': backend_identity(backend),
        'tab': tab,
        'mode': 'display_catches_up',
        'ratio': ratio,
        'within_five_percent': ratio <= 1.05,
    }


def fit_tab_comparisons(fits, *, backend):
    """Keep both real chart tabs in the per-backend five-percent comparison."""
    if set(fits) != {'pattern', 'stacked'}:
        raise ValueError('Fit timing gates require both Pattern and Stacked tabs')
    results = {}
    required = {'display_catches_up_ms', 'fit_waits_for_display_ms', 'adaptive_ms'}
    for tab, samples in fits.items():
        if set(samples) != required:
            raise ValueError(
                'Fit timings must distinguish display catches up and fit waits for the display'
            )
        result = fit_comparison(
            samples['display_catches_up_ms'], samples['adaptive_ms'], backend=backend, tab=tab
        )
        result['fit_waits_ratio'] = measured_median(
            samples['fit_waits_for_display_ms']
        ) / measured_median(samples['adaptive_ms'])
        results[tab] = result
    return results


def backend_comparisons(rows):
    """Require software OpenGL alongside any available hardware measurements."""
    results = []
    for row in rows:
        backend = row['backend']
        results.append({
            'redraw': redraw_comparison(row['before_ms'], row['after_ms'], backend=backend),
            'fit': fit_tab_comparisons(row['fits'], backend=backend),
        })
    if not any(row['redraw']['backend']['llvmpipe'] for row in results):
        raise ValueError('Timing gates require a measured llvmpipe OpenGL row')
    return results


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
