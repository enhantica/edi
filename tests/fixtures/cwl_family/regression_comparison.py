"""Retained pre-change regression bytes with the published platform tolerance.

Linux remains exact. Other platforms compare the original Linux values using
ADR-0057's max(relative, absolute) bound; no post-change expectation is generated.
"""

import base64

import numpy as np

SOURCE = '7a8eabf53084332a10b90991907d2040e5365b6a'
ENGINE_SOURCE = 'b9f2267451adf1896463c706a87fea20790d28ac'


def require_reference(record):
    assert record['source'] == SOURCE, (
        'The regression capture must belong to the retained pre-change engine'
    )
    assert record['engine_source'] == ENGINE_SOURCE, (
        'The edi capture retains its qualified pre-change engine identity'
    )
    assert record['kind'] == 'regression-pin', (
        'The engine capture must remain labelled as a regression pin'
    )
    assert record['platform'] == 'Linux', (
        'The independent retained capture records its native Linux platform'
    )
    assert set(record['pins']) == {'tch', 'fcj'}, (
        'The retained capture must contain both unchanged profile subjects'
    )


def compare(actual, expected, native_platform, reference_platform='Linux'):
    assert len(expected) > 0, 'The regression reference must contain samples'
    assert len(expected) % 8 == 0, 'The regression reference must contain complete doubles'
    assert len(actual) == len(expected), 'The renamed profile must retain every reference sample'
    values = np.frombuffer(actual, dtype='<f8')
    reference = np.frombuffer(expected, dtype='<f8')
    assert np.isfinite(values).all(), 'Platform comparison refuses nonfinite actual samples'
    assert np.isfinite(reference).all(), 'Platform comparison refuses nonfinite reference samples'
    if native_platform == reference_platform:
        assert actual == expected, (
            'The recorded native platform must retain the original calculation bytes exactly'
        )
    else:
        limit = np.maximum(5e-9 * np.abs(reference), 5e-10)
        assert np.all(np.abs(values - reference) <= limit), (
            'Cross-platform regression values must obey ADR-0057 '
            'max(relative 5e-9, absolute 5e-10) at every sample'
        )


def compare_pin(actual, record, name, native_platform):
    require_reference(record)
    compare(
        actual,
        base64.b64decode(record['pins'][name], validate=True),
        native_platform,
        record['platform'],
    )
