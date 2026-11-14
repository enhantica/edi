"""Native transport accepts the two shipped CLI forms and exact host identities."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def native():
    spec = importlib.util.spec_from_file_location(
        'native_identity', ROOT / 'tools/ci/edi_native.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    'output',
    ['edi 2026.11.14\n', 'easydiffraction (edi core 0.0.0-dev)\n'],
)
def test_shipped_cli_version_forms_cross_the_complete_producer_check(native, monkeypatch, output):
    reached = []
    monkeypatch.setattr(native, 'prove_import', lambda: reached.append('import'))
    monkeypatch.setattr(native, 'runnable', lambda: reached.append('runners'))
    monkeypatch.setattr(
        native.subprocess,
        'run',
        lambda *a, **_kwargs: subprocess.CompletedProcess(a, 0, output, ''),
    )
    native.prove()
    assert reached == ['import', 'runners']


@pytest.mark.parametrize(
    'output',
    [
        '',
        'edi\n',
        'edi \n',
        'edi 1.0\nforeign\n',
        'foreign edi 1.0\n',
        'easydiffraction\n',
        'easydiffraction (edi core )\n',
        'easydiffraction (foreign core 1)\n',
        'easydiffraction (edi core 1) extra\n',
    ],
)
def test_missing_foreign_or_multiline_cli_response_refuses(native, monkeypatch, output):
    monkeypatch.setattr(native, 'prove_import', lambda: None)
    monkeypatch.setattr(
        native.subprocess,
        'run',
        lambda *a, **_kwargs: subprocess.CompletedProcess(a, 0, output, ''),
    )
    with pytest.raises(native.RefusedError, match='CLI gives no version line'):
        native.prove()


@pytest.mark.parametrize('status', [1, 2, -1])
def test_failed_cli_refuses_even_when_output_looks_valid(native, monkeypatch, status):
    monkeypatch.setattr(native, 'prove_import', lambda: None)
    monkeypatch.setattr(
        native.subprocess,
        'run',
        lambda *a, **_kwargs: subprocess.CompletedProcess(a, status, 'edi 2026.11.14\n', ''),
    )
    with pytest.raises(native.RefusedError, match='CLI gives no version line'):
        native.prove()


@pytest.mark.parametrize('label', ['win-64', 'win-64-app', 'Windows-X64', 'Windows-AMD64'])
def test_windows_native_identity_maps_to_its_own_sdk(native, monkeypatch, label):
    monkeypatch.setenv('PIXI_PLATFORM', label)
    assert native.sdk_platform() == 'win-64'


def test_unknown_windows_architecture_is_not_an_x64_sdk(native, monkeypatch):
    monkeypatch.setenv('PIXI_PLATFORM', 'Windows-ARM64')
    with pytest.raises(native.RefusedError, match='no edi native platform'):
        native.sdk_platform()
