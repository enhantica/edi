"""Exercise timing-row arithmetic with synthetic samples, never performance claims."""

import csv
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.timing import (
    CHANGES,
    backend_comparisons,
    fit_comparison,
    fit_tab_comparisons,
    measured_median,
    redraw_comparison,
)


def row(renderer='llvmpipe (LLVM 20)', api='OpenGL'):
    return {
        'backend': {'api': api, 'renderer': renderer},
        'changes': {
            change: {'before_ms': [120, 110, 130], 'after_ms': [98, 99, 100]} for change in CHANGES
        },
        'conditions': {'quiet': True, 'load_average': [0.1, 0.2, 0.1], 'logical_cpus': 8},
        'fits': {
            tab: {
                'display_catches_up_ms': [104, 105, 106],
                'fit_waits_for_display_ms': [180, 190, 200],
                'adaptive_ms': [99, 100, 101],
            }
            for tab in ('pattern', 'stacked')
        },
    }


def test_hardware_numbers_cannot_replace_the_no_gpu_row():
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([row('Apple M2', 'Metal')])
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([])


def test_non_opengl_backend_has_no_opengl_renderer_to_report():
    result = backend_comparisons([row('', 'Metal'), row()])[0]
    assert result['fit']['pattern']['backend'] == {
        'api': 'Metal',
        'renderer': '',
        'llvmpipe': False,
        'software': False,
    }, 'A Metal timing keeps its real backend without inventing an OpenGL renderer string'


@pytest.mark.parametrize('slow_backend', ['gpu', 'software'])
def test_each_backend_keeps_its_own_targets_and_identity(slow_backend):
    hardware, software = row('Apple M2', 'Metal'), row()
    if slow_backend == 'gpu':
        hardware['changes']['data']['after_ms'] = [99, 100, 101]
    else:
        software['changes']['data']['after_ms'] = [250, 251, 252]
    software['fits']['pattern']['display_catches_up_ms'] = [105, 106, 107]
    results = backend_comparisons([hardware, software])
    assert [item['redraw']['data']['within_limit'] for item in results] == [
        slow_backend != 'gpu',
        slow_backend != 'software',
    ], 'A fast backend cannot cover another backend exceeding its own operation limit'
    assert [item['redraw']['data']['limit_ms'] for item in results] == [100, 250], (
        'Each backend retains its own amended data-change limit rather than pooling hosts'
    )
    assert [item['fit']['pattern']['within_five_percent'] for item in results] == [True, False], (
        'The inclusive five-percent Pattern fit bound applies independently on each backend'
    )
    for result, source in zip(results, [hardware, software], strict=True):
        for gate in [*result['redraw'].values(), *result['fit'].values()]:
            assert gate['backend']['renderer'] == source['backend']['renderer'], (
                'Every timing gate retains the observed renderer rather than pooling hosts'
            )
            assert gate['backend']['api'] == source['backend']['api'], (
                'Every timing gate retains its observed graphics API'
            )


@pytest.mark.parametrize(
    'backend',
    [
        {},
        {'api': 'OpenGL', 'renderer': ''},
        {'api': '', 'renderer': 'llvmpipe'},
        {'api': 'Software', 'renderer': 'llvmpipe'},
    ],
)
def test_timing_gates_refuse_missing_or_mislabelled_backend(backend):
    with pytest.raises(ValueError, match=r'(observed graphics API|llvmpipe OpenGL)'):
        redraw_comparison([1, 2, 3], [1, 2, 3], backend=backend, change='data')
    with pytest.raises(ValueError, match=r'(observed graphics API|llvmpipe OpenGL)'):
        fit_comparison([1, 2, 3], [1, 2, 3], backend=backend, tab='pattern')


def test_software_row_cannot_omit_either_timing_gate():
    for field in ('changes', 'fits', 'conditions'):
        incomplete = row()
        del incomplete[field]
        with pytest.raises(KeyError):
            backend_comparisons([incomplete])


@pytest.mark.parametrize('field', ['after_ms', 'adaptive_ms'])
@pytest.mark.parametrize('samples', [[1, 2], [1, float('nan'), 3], [1, 0, 3]])
def test_software_case_requires_repeated_real_samples(field, samples):
    incomplete = row()
    if field == 'adaptive_ms':
        incomplete['fits']['pattern'][field] = samples
    else:
        incomplete['changes']['data'][field] = samples
    with pytest.raises(ValueError, match='repeated finite positive live samples'):
        backend_comparisons([incomplete])


@pytest.mark.parametrize('tab', ['pattern', 'stacked'])
def test_each_backend_requires_both_fit_tabs(tab):
    incomplete = row()
    del incomplete['fits'][tab]
    with pytest.raises(ValueError, match='require both Pattern and Stacked tabs'):
        backend_comparisons([incomplete])


@pytest.mark.parametrize('tab', ['pattern', 'stacked'])
def test_a_fast_tab_cannot_hide_the_other_tabs_overhead(tab):
    measured = row()
    measured['fits'][tab]['display_catches_up_ms'] = [130, 140, 150]
    comparisons = backend_comparisons([measured])[0]['fit']
    for name, comparison in comparisons.items():
        assert comparison['tab'] == name, 'Each fit result must keep the actual tab identity'
        assert comparison['within_five_percent'] == (name != tab), (
            'Display catches up must meet its ratio on each tab without pooling fast and slow tabs'
        )


def test_frozen_baseline_regression_pin_keeps_pattern_and_stacked_separate():
    path = (
        Path(__file__).resolve().parents[3]
        / 'docs/dev/design/scan-view-timings/baseline/medians.tsv'
    )
    fits = {tab: {'every_pattern_ms': [], 'adaptive_ms': []} for tab in ('pattern', 'stacked')}
    with path.open() as stream:
        for sample in csv.DictReader(stream, delimiter='\t'):
            for tab in fits:
                for mode, field in (('every', 'every_pattern_ms'), ('adaptive', 'adaptive_ms')):
                    if sample['step'] == f'perf-fit-{mode}-{tab}' and sample['measure'] == 'fit':
                        fits[tab][field].append(float(sample['value_ms']))
    ratios = {
        tab: measured_median(samples['every_pattern_ms']) / measured_median(samples['adaptive_ms'])
        for tab, samples in fits.items()
    }
    assert ratios['pattern'] == pytest.approx(53850 / 22372), (
        'The frozen software-OpenGL Pattern regression pin reports the legacy fit-waits mode'
    )
    assert ratios['stacked'] == pytest.approx(16684 / 17127), (
        'The frozen Stacked regression pin reports the legacy fit-waits mode separately'
    )


@pytest.mark.parametrize('missing', ['display_catches_up_ms', 'fit_waits_for_display_ms'])
def test_both_every_pattern_choices_have_distinct_live_receipts(missing):
    fits = row()['fits']
    del fits['pattern'][missing]
    with pytest.raises(ValueError, match='distinguish display catches up and fit waits'):
        fit_tab_comparisons(fits, backend=row()['backend'])


def test_legacy_every_pattern_samples_cannot_be_relabelled_as_catchup():
    fits = row()['fits']
    samples = fits['pattern']
    samples['every_pattern_ms'] = samples.pop('display_catches_up_ms')
    with pytest.raises(ValueError, match='distinguish display catches up and fit waits'):
        fit_tab_comparisons(fits, backend=row()['backend'])


def test_fit_waits_is_reported_without_the_catchup_bound():
    fits = row()['fits']
    fits['pattern']['fit_waits_for_display_ms'] = [300, 310, 320]
    result = fit_tab_comparisons(fits, backend=row()['backend'])['pattern']
    assert result['within_five_percent'], 'Only display catches up carries the five-percent bound'
    assert result['fit_waits_ratio'] == pytest.approx(3.1), (
        'The fit-waits overhead is still reported honestly'
    )
    assert result['mode'] == 'display_catches_up', (
        'The bounded result must name the new catch-up mode'
    )


@pytest.mark.parametrize('change', CHANGES)
@pytest.mark.parametrize('software', [False, True], ids=['gpu', 'software'])
@pytest.mark.parametrize('edge', [-0.001, 0, 0.001], ids=['below', 'at', 'above'])
def test_redraw_boundaries_follow_the_committed_operation_policy(change, software, edge):
    backend = row()['backend'] if software else row('Apple M2', 'Metal')['backend']
    limit = {'data': 250, 'zoom': 115}.get(change, 100) if software else 100
    value = limit + edge
    result = redraw_comparison(
        [400, 401, 402], [value - 0.0001, value, value + 0.0001], backend=backend, change=change
    )
    assert result['limit_ms'] == limit and result['inclusive'] is software, (
        'Each operation uses the committed GPU or software bound and boundary convention'
    )
    assert result['within_limit'] == (edge <= 0 if software else edge < 0), (
        'Repeated medians below, at and above each bound obey the amended acceptance rule'
    )
    assert result['change'] == change and result['after_ms'] == pytest.approx(value), (
        'The timing verdict retains its actual operation and measured median'
    )


@pytest.mark.parametrize('change', CHANGES)
def test_fast_operations_cannot_hide_one_slow_operation(change):
    samples = row()
    limit = {'data': 250, 'zoom': 115}.get(change, 100)
    samples['changes'][change]['after_ms'] = [limit, limit + 1, limit + 2]
    result = backend_comparisons([samples])[0]['redraw']
    assert {name for name, timing in result.items() if not timing['within_limit']} == {change}, (
        'Every change has its own timing verdict so fast pan or select cannot mask a slow redraw'
    )


@pytest.mark.parametrize('change', CHANGES)
def test_timing_row_cannot_omit_a_change(change):
    samples = row()
    del samples['changes'][change]
    with pytest.raises(ValueError, match='require every data, zoom, pan, restyle and select'):
        backend_comparisons([samples])


def test_timing_row_refuses_an_unidentified_or_extra_change():
    samples = row()
    samples['changes']['other'] = samples['changes']['data']
    with pytest.raises(ValueError, match='require every data, zoom, pan, restyle and select'):
        backend_comparisons([samples])
    with pytest.raises(ValueError, match='must name data, zoom, pan, restyle or select'):
        redraw_comparison([1, 2, 3], [1, 2, 3], backend=row()['backend'], change='other')


@pytest.mark.parametrize(
    'conditions',
    [
        {},
        {'quiet': False, 'load_average': [0, 0, 0], 'logical_cpus': 8},
        {'quiet': 'true', 'load_average': [0, 0, 0], 'logical_cpus': 8},
        {'quiet': True, 'logical_cpus': 8},
        {'quiet': True, 'load_average': [0, 0, 0]},
        {'quiet': True, 'load_average': [0, 0, 0], 'logical_cpus': True},
        {'quiet': True, 'load_average': [0, 0, 0], 'logical_cpus': 0},
        {'quiet': True, 'load_average': [0, 0], 'logical_cpus': 8},
        {'quiet': True, 'load_average': [0, float('nan'), 0], 'logical_cpus': 8},
        {'quiet': True, 'load_average': [0, -1, 0], 'logical_cpus': 8},
    ],
)
def test_timing_verdict_requires_quiet_confirmation_and_stated_load(conditions):
    samples = row()
    samples['conditions'] = conditions
    with pytest.raises(ValueError, match='quiet-machine confirmation, CPU count and stated load'):
        backend_comparisons([samples])


def test_timing_results_keep_the_declared_measurement_conditions():
    samples = row()
    result = backend_comparisons([samples])[0]
    assert result['conditions'] == samples['conditions'], (
        'A timing result retains the quiet declaration, measured load and available CPU count'
    )


@pytest.mark.parametrize(
    ('api', 'renderer'),
    [
        ('Software', ''),
        ('OpenGL', 'softpipe'),
        ('OpenGL', 'SwiftShader'),
        ('Vulkan', 'lavapipe'),
        ('OpenGL', 'Microsoft Basic Render Driver'),
    ],
)
def test_other_cpu_renderers_cannot_inherit_the_gpu_data_bound(api, renderer):
    result = redraw_comparison(
        [300, 301, 302], [249, 250, 251], backend={'api': api, 'renderer': renderer}, change='data'
    )
    assert result['within_limit'] and result['backend']['software'], (
        'Actual CPU rendering uses the inclusive software data bound even outside llvmpipe'
    )
    assert result['limit_ms'] == 250, 'The committed software data ceiling is 250 milliseconds'


def test_cpu_load_can_be_stated_without_a_posix_load_average():
    samples = row()
    samples['conditions'] = {'quiet': True, 'logical_cpus': 8, 'cpu_busy_percent': 1.5}
    result = backend_comparisons([samples])[0]
    assert result['conditions'] == samples['conditions'], (
        'A host without POSIX load averages may retain measured CPU busy percent with its units'
    )


@pytest.mark.parametrize('busy', [True, -1, 101, float('nan')])
def test_timing_conditions_refuse_invalid_cpu_busy_percent(busy):
    samples = row()
    samples['conditions'] = {'quiet': True, 'logical_cpus': 8, 'cpu_busy_percent': busy}
    with pytest.raises(ValueError, match='quiet-machine confirmation, CPU count and stated load'):
        backend_comparisons([samples])


def test_timing_conditions_refuse_conflicting_load_units():
    samples = row()
    samples['conditions']['cpu_busy_percent'] = 1.5
    with pytest.raises(ValueError, match='quiet-machine confirmation, CPU count and stated load'):
        backend_comparisons([samples])


@pytest.mark.parametrize('conditions', [None, [], 'quiet'])
def test_timing_conditions_require_a_structured_record(conditions):
    samples = row()
    samples['conditions'] = conditions
    with pytest.raises(TypeError, match='quiet-machine confirmation, CPU count and stated load'):
        backend_comparisons([samples])
