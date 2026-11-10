"""Explicit-pattern native calls must select the same participants as the model fit."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.multiphase import participants as case

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def native_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('fit-participants-native')
    binary = directory / 'consumer'
    sdk = Path(os.environ.get('CRYSTA_SDK_DIR', ROOT / 'build/crysta-prefix'))
    build = ROOT / ('build/ci-consumer' if os.environ.get('CRYSTA_SDK_DIR') else 'build/ci')
    environment = Path(sys.executable).resolve().parent.parent
    compiler = shutil.which('clang++')
    assert compiler, 'Native participant gates require the declared compiler'
    compiled = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-O0',
            '-pthread',
            '-I' + str(ROOT / 'core/include'),
            '-I' + str(sdk / 'include'),
            '-I' + str(environment / 'include/eigen3'),
            str(ROOT / 'tests/fixtures/multiphase/native_participants.cpp'),
            str(build / 'core/libedi_core.a'),
            str(sdk / 'lib/libcrysta_core.a'),
            '-lgomp' if sys.platform == 'linux' else '-lomp',
            '-L' + str(environment / 'lib'),
            '-Wl,-rpath,' + str(environment / 'lib'),
            '-lsleef',
            '-o',
            str(binary),
        ],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    assert compiled.returncode == 0, (
        'The native participant vehicle must compile before its outcomes count: ' + compiled.stderr
    )
    return binary


def outcome(native_probe, root, route, empty='', spelling='named'):
    result = subprocess.run(
        [str(native_probe), str(root), route, empty, spelling],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, (
        'Explicit-pattern participant calls must report admission or refusal without crashing: '
        + result.stderr
    )
    return result.stdout


@pytest.mark.parametrize('key', case.GRAPHS)
def test_native_explicit_joint_uses_each_enabled_component(native_probe, tmp_path, key):
    actual = outcome(native_probe, case.graph(tmp_path / 'input', key), 'explicit-joint')
    if case.GRAPHS[key][3]:
        assert actual.startswith('ADMITTED'), (
            'Independently anchored components must admit the native joint request: ' + actual
        )
    else:
        assert actual.startswith('REFUSED') and (
            'dilation' in actual or 'null direction' in actual
        ), 'Native explicit patterns must not hide disconnected active dilations: ' + actual


@pytest.mark.parametrize('route', ['explicit-single', 'explicit-joint'])
@pytest.mark.parametrize(
    'selection', ['other-bank-empty', 'disabled-empty', 'unused-empty-first', 'selected-empty']
)
@pytest.mark.parametrize('reverse', [False, True], ids=['forward', 'reverse'])
def test_native_explicit_pattern_atom_check_matches_its_selected_banks(
    native_probe, tmp_path, route, selection, reverse
):
    edges = {'p': [('alpha', True)], 'q': [('beta', True)]}
    empty = 'beta'
    if selection == 'disabled-empty':
        edges['q'] = [('alpha', True), ('beta', False)]
    elif selection == 'unused-empty-first':
        edges = {'p': [('beta', True)], 'q': [('beta', True)]}
        empty = 'alpha'
    elif selection == 'selected-empty':
        empty = 'alpha'
    root = case.write(
        tmp_path / 'input',
        edges,
        fixed_wavelengths=('p', 'q'),
        reverse=reverse,
        mode='single' if route == 'explicit-single' else 'joint',
    )
    actual = outcome(native_probe, root, route, empty)
    single = route == 'explicit-single'
    refuse = (selection == 'selected-empty' and (not single or not reverse)) or (
        selection == 'other-bank-empty' and (not single or reverse)
    )
    if refuse:
        assert actual.startswith('REFUSED') and 'no atom sites' in actual, (
            'Native explicit patterns must validate every selected active phase: ' + actual
        )
    else:
        assert actual.startswith('ADMITTED'), (
            'Native single-bank fits must exclude other-bank, disabled and unused empty phases: '
            + actual
        )


@pytest.mark.parametrize('route', ['explicit-single', 'explicit-joint'])
@pytest.mark.parametrize('spelling', ['empty-structure-name', 'empty-link-id'])
def test_native_canonical_phase_identity_cannot_skip_atom_preflight(
    native_probe, tmp_path, route, spelling
):
    root = case.write(
        tmp_path / 'input',
        {'p': [('alpha', True), ('beta', True)], 'q': [('beta', True)]},
        fixed_wavelengths=('p', 'q'),
        mode='single' if route == 'explicit-single' else 'joint',
    )
    path = root / 'structures/alpha.edi'
    path.write_text(path.read_text().replace('data_alpha', 'data_structure'))
    for path in (root / 'experiments').glob('*.edi'):
        path.write_text(path.read_text().replace('alpha 1.125()', 'structure 1.125()'))
    actual = outcome(native_probe, root, route, 'structure', spelling)
    assert actual.startswith('REFUSED') and 'no atom sites' in actual, (
        'Native canonical identity must resolve the active phase before inspecting its atoms: '
        + actual
    )
