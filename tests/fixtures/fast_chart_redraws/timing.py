"""Paired live timings; samples must come from the committed native baseline route."""

import math
from statistics import median

CHANGES = ('data', 'zoom', 'pan', 'restyle', 'select')


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
    cpu_renderer = any(
        name in renderer.lower()
        for name in (
            'llvmpipe',
            'softpipe',
            'swrast',
            'software rasterizer',
            'swiftshader',
            'lavapipe',
            'microsoft basic render',
        )
    )
    return {
        'api': api,
        'renderer': renderer,
        'llvmpipe': software,
        'software': api.lower() == 'software' or cpu_renderer,
    }


def redraw_comparison(before, after, *, backend, change):
    """Apply the committed 2026-10-26 operation/backend bound to repeated medians."""
    if change not in CHANGES:
        raise ValueError('A redraw timing must name data, zoom, pan, restyle or select')
    old, new = measured_median(before), measured_median(after)
    observed = backend_identity(backend)
    inclusive = observed['software']
    limit = {'data': 250, 'zoom': 115}.get(change, 100) if inclusive else 100
    return {
        'backend': observed,
        'change': change,
        'before_ms': old,
        'after_ms': new,
        'limit_ms': limit,
        'inclusive': inclusive,
        'within_limit': new <= limit if inclusive else new < limit,
    }


def redraw_changes(changes, *, backend):
    if set(changes) != set(CHANGES):
        raise ValueError(
            'Redraw timing rows require every data, zoom, pan, restyle and select change'
        )
    return {
        change: redraw_comparison(
            changes[change]['before_ms'],
            changes[change]['after_ms'],
            backend=backend,
            change=change,
        )
        for change in CHANGES
    }


def measurement_conditions(conditions):
    error = 'A timing verdict requires quiet-machine confirmation, CPU count and stated load'
    if not isinstance(conditions, dict):
        raise TypeError(error)
    load = conditions.get('load_average')
    busy = conditions.get('cpu_busy_percent')
    cpus = conditions.get('logical_cpus')
    valid_cpus = type(cpus) is int and cpus > 0
    valid_average = (
        isinstance(load, list)
        and len(load) == 3
        and all(
            type(value) in {int, float} and math.isfinite(value) and value >= 0 for value in load
        )
    )
    valid_busy = type(busy) in {int, float} and math.isfinite(busy) and 0 <= busy <= 100
    one_measure = (load is None) != (busy is None)
    if conditions.get('quiet') is not True or not valid_cpus or not one_measure:
        raise ValueError(error)
    if not (valid_average or valid_busy):
        raise ValueError(error)
    result = {'quiet': True, 'logical_cpus': cpus}
    result.update({'load_average': list(load)} if valid_average else {'cpu_busy_percent': busy})
    return result


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
            'backend': backend_identity(backend),
            'conditions': measurement_conditions(row['conditions']),
            'redraw': redraw_changes(row['changes'], backend=backend),
            'fit': fit_tab_comparisons(row['fits'], backend=backend),
        })
    if not any(row['backend']['llvmpipe'] for row in results):
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
