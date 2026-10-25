"""Exercise timing-row arithmetic with synthetic samples, never performance claims."""

import csv
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.timing import (
    backend_comparisons,
    fit_comparison,
    fit_tab_comparisons,
    redraw_comparison,
)


def row(renderer='llvmpipe (LLVM 20)', api='OpenGL'):
    return {
        'backend': {'api': api, 'renderer': renderer},
        'before_ms': [120, 110, 130],
        'after_ms': [98, 99, 100],
        'fits': {
            tab: {'every_pattern_ms': [104, 105, 106], 'adaptive_ms': [99, 100, 101]}
            for tab in ('pattern', 'stacked')
        },
    }


def test_hardware_numbers_cannot_replace_the_no_gpu_row():
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([row('Apple M2', 'Metal')])
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([])


def test_each_backend_keeps_its_own_targets_and_identity():
    software = row()
    software['after_ms'] = [99, 100, 101]
    software['fits']['pattern']['every_pattern_ms'] = [105, 106, 107]
    results = backend_comparisons([row('Apple M2', 'Metal'), software])
    assert [item['redraw']['under_100_ms'] for item in results] == [True, False], (
        'The strict redraw bound applies independently to software and hardware renderers'
    )
    assert [item['fit']['pattern']['within_five_percent'] for item in results] == [True, False], (
        'The inclusive five-percent Pattern fit bound applies independently on each backend'
    )
    for result, source in zip(results, [row('Apple M2', 'Metal'), software], strict=True):
        for gate in [result['redraw'], *result['fit'].values()]:
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
        redraw_comparison([1, 2, 3], [1, 2, 3], backend=backend)
    with pytest.raises(ValueError, match=r'(observed graphics API|llvmpipe OpenGL)'):
        fit_comparison([1, 2, 3], [1, 2, 3], backend=backend, tab='pattern')


def test_software_row_cannot_omit_either_timing_gate():
    for field in ('before_ms', 'after_ms', 'fits'):
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
        incomplete[field] = samples
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
    measured['fits'][tab]['every_pattern_ms'] = [130, 140, 150]
    comparisons = backend_comparisons([measured])[0]['fit']
    for name, comparison in comparisons.items():
        assert comparison['tab'] == name, 'Each fit result must keep the actual tab identity'
        assert comparison['within_five_percent'] == (name != tab), (
            'Every pattern must meet its ratio on each tab without pooling fast and slow tabs'
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
    results = fit_tab_comparisons(fits, backend=row()['backend'])
    assert results['pattern']['ratio'] == pytest.approx(53850 / 22372), (
        'The frozen software-OpenGL Pattern regression pin uses all repeated baseline fits'
    )
    assert results['stacked']['ratio'] == pytest.approx(16684 / 17127), (
        'The frozen software-OpenGL Stacked regression pin stays separate from Pattern'
    )
    assert (
        not results['pattern']['within_five_percent'] and results['stacked']['within_five_percent']
    ), 'The committed baseline exposes the Pattern overhead despite a fast Stacked fit'
