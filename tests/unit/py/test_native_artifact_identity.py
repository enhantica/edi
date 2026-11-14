"""Native transport accepts the two shipped CLI forms and exact host identities."""

import ast
import importlib.util
import json
import os
import subprocess
import sys
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


@pytest.mark.parametrize('operation', ['manifest', 'tracked-names'])
def test_git_source_text_is_utf8_under_a_non_utf8_process_locale(tmp_path, operation):
    payload = '# source identity: χ² Ϗ\n[activation.env]\nCRYSTA_COMMIT="' + 'a7' * 20 + '"\n'
    (tmp_path / 'pixi.toml').write_text(payload, encoding='utf-8')
    (tmp_path / 'résuméϏ.txt').write_text('independent tracked name', encoding='utf-8')
    for args in (
        ['init', '-q'],
        ['add', '.'],
        [
            '-c',
            'user.name=Encoding control',
            '-c',
            'user.email=encoding@example.invalid',
            'commit',
            '-qm',
            'UTF8 source',
        ],
    ):
        subprocess.run(['git', *args], cwd=tmp_path, capture_output=True, check=True)
    code = """
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('native_encoding',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ROOT=Path(sys.argv[2])
args=('show','HEAD:pixi.toml') if sys.argv[3]=='manifest' else ('ls-files','-z')
print(json.dumps(module.git(*args)))
"""
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            code,
            str(ROOT / 'tools/ci/edi_native.py'),
            str(tmp_path),
            operation,
        ],
        env={
            **os.environ,
            'PYTHONUTF8': '0',
            'PYTHONCOERCECLOCALE': '0',
            'LC_ALL': 'C',
            'LANG': 'C',
        },
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected = payload.strip() if operation == 'manifest' else 'pixi.toml\0résuméϏ.txt\0'
    assert json.loads(result.stdout) == expected, (
        'Source text and Unicode names must retain every UTF8 byte'
    )


@pytest.mark.parametrize(
    'relative', ['tools/ci/edi_native.py', 'tools/ci/crysta_source_receipt.py']
)
def test_native_source_protocol_readers_never_use_ambient_text_decoding(relative):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and ast.unparse(node.func) == 'subprocess.run'
    ]
    assert calls, 'The census must reach the actual source protocol subprocess boundaries'
    for call in calls:
        keywords = {item.arg: item.value for item in call.keywords}
        if ast.literal_eval(keywords.get('text', ast.Constant(False))):
            assert 'encoding' in keywords and ast.literal_eval(keywords['encoding']) == 'utf-8', (
                'Every decoded source/native protocol result declares strict UTF8 on all platforms'
            )
