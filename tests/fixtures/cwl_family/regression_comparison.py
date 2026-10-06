"""Exact native pre-change rename pins and a separate cross-platform diagnostic."""

import base64
import hashlib
import json
import shutil

import numpy as np

SOURCE = '7a8eabf53084332a10b90991907d2040e5365b6a'
ENGINE_SOURCE = 'b9f2267451adf1896463c706a87fea20790d28ac'


def require_reference(record, native_platform=None):
    assert record['source'] == SOURCE, (
        'The regression capture must belong to the retained pre-change engine'
    )
    assert record['engine_source'] == ENGINE_SOURCE, (
        'The edi capture retains its qualified pre-change engine identity'
    )
    assert record['kind'] == 'regression-pin', (
        'The engine capture must remain labelled as a regression pin'
    )
    assert record['platform'] in {'Linux', 'Darwin'}, (
        'The independent retained capture records a supported native platform'
    )
    if native_platform is not None:
        assert record['platform'] == native_platform, (
            'The rename property requires the independent capture of its own native platform'
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
    require_reference(record, native_platform)
    compare(
        actual,
        base64.b64decode(record['pins'][name], validate=True),
        native_platform,
        record['platform'],
    )


def read_reference(root, native_platform):
    path = root / f'tch-regression-{native_platform}.json'
    assert path.is_file(), (
        'Every native rename property requires its own pre-change platform reference'
    )
    record = json.loads(path.read_text())
    require_reference(record, native_platform)
    return record


def rename_project(root, destination, name, token, record):
    inputs = root / 'rename_inputs'
    hashes = {
        path.relative_to(inputs).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(inputs.rglob('*.edi'))
    }
    assert len(hashes) == 4, 'The rename vehicle retains both complete historical input projects'
    if record['platform'] == 'Darwin':
        assert hashes == record['input_sha256'], (
            'Darwin expected and actual native runs consume identical serialized pre-change inputs'
        )
    shutil.copytree(inputs / name, destination, dirs_exist_ok=True)
    experiment = destination / 'experiments/bank.edi'
    text = experiment.read_text()
    lines = [line for line in text.splitlines() if line.startswith('_peak.type ')]
    assert len(lines) == 1, (
        'A retained rename vehicle has exactly one historical profile declaration'
    )
    experiment.write_text(text.replace(lines[0], '_peak.type ' + token))
    return destination
