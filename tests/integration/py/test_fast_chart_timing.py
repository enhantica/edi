"""Exercise timing-row arithmetic with synthetic samples, never performance claims."""

import pytest

from tests.fixtures.fast_chart_redraws.timing import (
    backend_comparisons,
    fit_comparison,
    redraw_comparison,
)


def row(renderer='llvmpipe (LLVM 20)', api='OpenGL'):
    return {
        'backend': {'api': api, 'renderer': renderer},
        'before_ms': [120, 110, 130],
        'after_ms': [98, 99, 100],
        'every_pattern_ms': [104, 105, 106],
        'adaptive_ms': [99, 100, 101],
    }


def test_hardware_numbers_cannot_replace_the_no_gpu_row():
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([row('Apple M2', 'Metal')])
    with pytest.raises(ValueError, match='require a measured llvmpipe OpenGL row'):
        backend_comparisons([])


def test_each_backend_keeps_its_own_targets_and_identity():
    software = row()
    software['after_ms'] = [99, 100, 101]
    software['every_pattern_ms'] = [105, 106, 107]
    results = backend_comparisons([row('Apple M2', 'Metal'), software])
    assert [item['redraw']['under_100_ms'] for item in results] == [True, False], (
        'The strict redraw bound applies independently to software and hardware renderers'
    )
    assert [item['fit']['within_five_percent'] for item in results] == [True, False], (
        'The inclusive five-percent fit bound applies independently on each backend'
    )
    for result, source in zip(results, [row('Apple M2', 'Metal'), software], strict=True):
        for gate in ('redraw', 'fit'):
            assert result[gate]['backend']['renderer'] == source['backend']['renderer'], (
                'Every timing gate retains the observed renderer rather than pooling hosts'
            )
            assert result[gate]['backend']['api'] == source['backend']['api'], (
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
        fit_comparison([1, 2, 3], [1, 2, 3], backend=backend)


def test_software_row_cannot_omit_either_timing_gate():
    for field in ('before_ms', 'after_ms', 'every_pattern_ms', 'adaptive_ms'):
        incomplete = row()
        del incomplete[field]
        with pytest.raises(KeyError):
            backend_comparisons([incomplete])


@pytest.mark.parametrize('field', ['after_ms', 'adaptive_ms'])
@pytest.mark.parametrize('samples', [[1, 2], [1, float('nan'), 3], [1, 0, 3]])
def test_software_case_requires_repeated_real_samples(field, samples):
    incomplete = row()
    incomplete[field] = samples
    with pytest.raises(ValueError, match='repeated finite positive live samples'):
        backend_comparisons([incomplete])
