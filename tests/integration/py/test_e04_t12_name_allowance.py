"""Keep test names without exempting the code and text beside them."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tests.integration.py.test_e04_t12_public_content import check, commit, event, specimen

ROOT = Path(__file__).resolve().parents[3]


def scanner():
    path = ROOT / 'tools/public-release/scan.py'
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('name_allowance_scanner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unsafe_line(shape):
    residue = 're' + 'lay ' + 'E' + '05-' + 'T1 I-' + '0300'
    marker = 'test_' + 'e05_t1_saved'
    label = 'E' + '05-' + 'T1 saved'
    return {
        'unrelated-node-string': 'def ' + marker + '(): note = "kind:: ' + residue + '"\n',
        'indexed-expression': 'def ' + marker + '(): note = test_cache["' + residue + '"]\n',
        'cpp-namespace': 'TEST_CASE("'
        + label
        + '") { auto note = state::lookup("'
        + residue
        + '"); }\n',
        'comment-marker': 'note = "kind:: ' + residue + '"  # ' + marker + '\n',
        'string-marker': 'note = test_cache["' + residue + '"]; marker = "' + marker + '"\n',
    }[shape]


def stored(root, channel, text):
    if channel == 'ordinary':
        path = root / 'tests/unit/py/test_saved.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    else:
        path = root / 'saved.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('test_saved.txt', text)
    return path.relative_to(root).as_posix()


SHAPES = [
    'unrelated-node-string',
    'indexed-expression',
    'cpp-namespace',
    'comment-marker',
    'string-marker',
]


@pytest.mark.parametrize('shape', SHAPES)
@pytest.mark.parametrize('channel', ['ordinary', 'decoded-member'])
def test_e04_t12_strict_names_do_not_mask_unrelated_spans(tmp_path, shape, channel):
    root, _base = specimen(tmp_path)
    relative = stored(root, channel, 'def test_saved(): pass\n')
    commit(root, 'Add saved data')
    tool = scanner()
    good = tool.analyse(root, only=[relative], strict=lambda _name: True)
    assert not good.members, (
        'strict ordinary and decoded controls must first admit public-safe text'
    )
    stored(root, channel, unsafe_line(shape))
    commit(root, 'Update saved data')
    result = tool.analyse(root, only=[relative], strict=lambda _name: True)
    assert any(kind == 'process reference' for _name, _line, kind in result.members), (
        'a test marker must not exempt an unrelated code, string or comment span: ' + shape
    )


@pytest.mark.parametrize('shape', SHAPES)
@pytest.mark.parametrize('channel', ['ordinary', 'decoded-member'])
@pytest.mark.parametrize('mode', ['root', 'push', 'pr'])
@pytest.mark.parametrize('version', ['tip', 'cleaned-tip'])
def test_e04_t12_name_span_escapes_refuse_every_history(tmp_path, shape, channel, mode, version):
    root, base = specimen(tmp_path)
    payload = event() if mode == 'pr' else {}
    start = None if mode == 'root' else base
    assert check(root, start, base, payload, tmp_path).returncode == 0, (
        'each publication history must start with an accepted safe control'
    )
    stored(root, channel, unsafe_line(shape))
    head = commit(root, 'Add saved data')
    if version == 'cleaned-tip':
        stored(root, channel, 'def test_saved(): pass\n')
        head = commit(root, 'Update saved data')
    result = check(root, start, head, payload, tmp_path)
    assert result.returncode != 0, (
        'publication histories must refuse unrelated name-like spans even when cleaned at the tip'
    )


@pytest.fixture(scope='module')
def real_parameter_node(tmp_path_factory):
    folder = tmp_path_factory.mktemp('pytest-name-control')
    path = folder / 'test_names.py'
    parameter = 're' + 'lay ' + 'E' + '05-' + 'T1 I-' + '0300'
    path.write_text(
        'import pytest\n@pytest.mark.parametrize("value", [1], ids=[' + repr(parameter) + '])\n'
        'def test_' + 'e05_t1_saved(value): pass\n'
    )
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            '-o',
            'addopts=',
            '-p',
            'no:cacheprovider',
            '--collect-only',
            '-q',
            str(path),
        ],
        cwd=folder,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (
        'the parameter-name oracle must use a real independent pytest collection'
    )
    nodes = [line for line in result.stdout.splitlines() if '::test_' in line]
    assert len(nodes) == 1, 'the compatibility oracle must obtain the actual collected pytest node'
    return nodes[0]


def compatible_line(kind, real_parameter_node):
    label = 'E' + '05-' + 'T1 saved case'
    if kind == 'pytest-parameter':
        return real_parameter_node + '\n'
    if kind in {'TEST_CASE', 'TEST_SUITE', 'SUBCASE'}:
        return kind + '("' + label + '") {}\n'
    return '0.123\ttests/unit/cpp/test_' + 'e05_t1_saved.cpp::' + label + '\n'


@pytest.mark.parametrize(
    'kind', ['pytest-parameter', 'TEST_CASE', 'TEST_SUITE', 'SUBCASE', 'runtime-node']
)
@pytest.mark.parametrize('channel', ['ordinary', 'decoded-member'])
@pytest.mark.parametrize('mode', ['root', 'push', 'pr'])
def test_e04_t12_supported_test_names_remain_public_compatible(
    tmp_path, kind, channel, mode, real_parameter_node
):
    root, base = specimen(tmp_path)
    stored(root, channel, compatible_line(kind, real_parameter_node))
    head = commit(root, 'Add saved names')
    result = check(
        root, None if mode == 'root' else base, head, event() if mode == 'pr' else {}, tmp_path
    )
    assert result.returncode == 0, (
        'actual pytest parameter ids, doctest declarations and runtime node names '
        'must remain publishable'
    )
