"""Real Git source/native protocol bytes retain UTF8 under non-UTF8 process locales."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


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
    assert result.returncode == 0, (
        'Git source text is utf8 under a non utf8 process locale. Observed: ' + str(result.stderr)
    )
    expected = payload.strip() if operation == 'manifest' else 'pixi.toml\0résuméϏ.txt\0'
    assert json.loads(result.stdout) == expected, (
        'Source text and Unicode names must retain every UTF8 byte'
    )
