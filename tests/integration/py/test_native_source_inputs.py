"""Native input drift covers every CMake-consumed test source before artifact use."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def native_inputs(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        'edi_native_inputs', ROOT / 'tools/ci/edi_native.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True, capture_output=True)
    return module


def commit(root):
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True, capture_output=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-qm',
            'Record native inputs',
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    'relative',
    [
        'tests/fixtures/single_crystal_edges/observer.cpp',
        'tests/fixtures/cli_performance/observer.cpp',
        'tests/fixtures/future_native/CMakeLists.txt',
        'tests/integration/cpp/test_native.cpp',
    ],
)
@pytest.mark.parametrize('transition', ['modified', 'deleted', 'untracked'])
def test_compiled_test_input_drift_is_admitted_to_refusal(native_inputs, relative, transition):
    root = native_inputs.ROOT
    path = root / relative
    path.parent.mkdir(parents=True)
    (root / '.gitignore').write_text('build/\n', encoding='utf-8')
    if transition != 'untracked':
        path.write_text('original compiled input\n', encoding='utf-8')
    commit(root)
    if transition == 'deleted':
        path.unlink()
    else:
        path.write_text('changed compiled input\n', encoding='utf-8')
    assert native_inputs.source_drift() == [relative], (
        'Modified, deleted and newly added compiled fixture/integration inputs must refuse reuse'
    )


def test_identical_bytes_and_ignored_build_output_are_not_source_drift(native_inputs):
    root = native_inputs.ROOT
    source = root / 'tests/fixtures/cli_performance/observer.cpp'
    source.parent.mkdir(parents=True)
    source.write_text('unchanged compiled input\n', encoding='utf-8')
    (root / '.gitignore').write_text('build/\n', encoding='utf-8')
    commit(root)
    source.write_bytes(source.read_bytes())
    output = root / 'build/ci/generated.cpp'
    output.parent.mkdir(parents=True)
    output.write_text('a build product\n', encoding='utf-8')
    assert native_inputs.source_drift() == [], (
        'Content-identical source rewrites and ignored generated outputs preserve admission'
    )
