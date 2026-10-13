"""Exact native pre-change rename pins and a separate cross-platform diagnostic."""

import base64
import hashlib
import json
import shutil

import numpy as np

SOURCE = '7a8eabf53084332a10b90991907d2040e5365b6a'
ENGINE_SOURCE = 'b9f2267451adf1896463c706a87fea20790d28ac'
DISPATCH_ENGINE_SOURCE = 'c2353f8f6414e4346c0701ca7018c7e615de9495'


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


def require_dispatch_reference(dispatch, historical, root, native_platform):
    assert dispatch['kind'] == 'regression-pin', 'Native dispatch captures are regression pins'
    assert dispatch['platform'] == native_platform, 'A native pin must come from its own platform'
    assert dispatch['reviewed_engine_source'] == DISPATCH_ENGINE_SOURCE, (
        'A dispatch adaptation requires the exact reviewed engine source'
    )
    assert dispatch['sdk_manifest']['source_sha'] == dispatch['engine_source'], (
        'The captured module must use the reviewed SDK source'
    )
    assert (
        dispatch['sdk_manifest']['platform']
        == {'Linux': 'linux-64', 'Darwin': 'osx-arm64'}[native_platform]
    ), 'A native pin must retain its actual SDK platform'
    from tests.fixtures.cwl_family.capture_dispatch_pins import SOURCE_OBJECTS  # noqa: PLC0415

    assert dispatch['source_objects'] == SOURCE_OBJECTS, (
        'A test-only descendant must retain every reviewed production source object'
    )
    assert (
        dispatch['historical_sha256']
        == hashlib.sha256(
            (root / f'tch-regression-{native_platform}.json').read_bytes()
        ).hexdigest()
    ), 'A dispatch adaptation cannot rewrite the retained historical pin'
    assert dispatch['input_sha256'] == json.loads(
        (root / 'rename-input-sha256.json').read_text()
    ), 'A dispatch adaptation must retain every historical physical input byte'
    assert set(dispatch['pins']) == set(historical['pins']), (
        'A dispatch adaptation retains both profile subjects'
    )
    for name, pin in dispatch['pins'].items():
        old = base64.b64decode(historical['pins'][name], validate=True)
        new = base64.b64decode(pin, validate=True)
        assert len(new) == len(old) > 0 and len(new) % 8 == 0, (
            'A dispatch adaptation retains the complete native sample population'
        )
        before, after = np.frombuffer(old, dtype='<f8'), np.frombuffer(new, dtype='<f8')
        assert np.isfinite(before).all() and np.isfinite(after).all(), (
            'A dispatch adaptation requires finite historical and native samples'
        )
        delta = float(np.max(np.abs(after - before)))
        scale = max(float(np.max(np.abs(before))), np.finfo(np.float64).tiny)
        assert delta <= 2**-34 * scale, 'A dispatch adaptation retains the unchanged value norm'
        move = dispatch['moves'][name]
        assert move['before_sha256'] == hashlib.sha256(old).hexdigest(), (
            'A dispatch adaptation retains its recorded before bytes'
        )
        assert move['after_sha256'] == hashlib.sha256(new).hexdigest(), (
            'A dispatch adaptation retains its recorded after bytes'
        )
        assert move['normwise'] == delta / scale, (
            'A dispatch adaptation must report its actual measured move'
        )


def compare_pin(actual, record, name, native_platform):
    require_reference(record, native_platform)
    compare(
        actual,
        base64.b64decode(record.get('dispatch_pins', record['pins'])[name], validate=True),
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
    adaptation = root / f'tch-dispatch-{native_platform}.json'
    if adaptation.is_file():
        dispatch = json.loads(adaptation.read_text())
        require_dispatch_reference(dispatch, record, root, native_platform)
        record = dict(record, dispatch_pins=dispatch['pins'])
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
