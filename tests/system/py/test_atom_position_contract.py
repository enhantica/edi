"""Unedited atom helper with cctbx operators and injected draws; no app wiring claim."""

import json
import operator
import shutil
import string
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TRUTH = json.loads((ROOT / 'tests/fixtures/c34_t25_fullprof/wyckoff.json').read_text())['groups'][
    'Pm-3m'
]


def method(source, signature):
    assert signature in source, 'The owner random-atom rule requires the injectable atom helper'
    start = source.index(signature)
    opening = source.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        assert end < len(source), 'The production atom helper must close its body'
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


@pytest.fixture(scope='module')
def atom_probe(tmp_path_factory):
    actual = method((ROOT / 'core/src/adapter.cpp').read_text(), 'AtomSite new_atom_site(')
    directory = tmp_path_factory.mktemp('atom-position')
    source = directory / 'probe.cpp'
    source.write_text(
        (ROOT / 'tests/fixtures/correlations/atom_probe.cpp')
        .read_text()
        .replace('// PRODUCTION_ATOM', actual)
    )
    executable = directory / 'probe'
    compiler = shutil.which('clang++')
    assert compiler, 'The atom helper gate requires the declared C++ compiler'
    built = subprocess.run(
        [compiler, '-std=c++20', str(source), '-o', str(executable)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert built.returncode == 0, 'The unedited injected atom helper must compile: ' + built.stderr
    return executable


@pytest.mark.parametrize(
    ('held', 'draws', 'label', 'coordinates'),
    [
        ([('H1', 'H')], [0, 0.1234, 0.2346, 0.3454], 'C1', [0.123, 0.235, 0.345]),
        (
            [('H1', 'H'), ('C1', 'C'), ('O1', 'O'), ('H3', 'H')],
            [0, 0.137, 0.251, 0.369],
            'H2',
            [0.137, 0.251, 0.369],
        ),
        ([], [0.999, 0, 0, 0, 0.137, 0.251, 0.369], 'O1', [0.137, 0.251, 0.369]),
        ([], [0, 0.9999, 0.251, 0.369, 0.137, 0.251, 0.369], 'H1', [0.137, 0.251, 0.369]),
    ],
    ids=[
        'prefer-unused-rounded',
        'all-used-next-free',
        'redraw-special-origin',
        'redraw-rounded-special',
    ],
)
def test_random_atom_obeys_general_position_and_injected_stream(
    atom_probe, held, draws, label, coordinates
):
    operations = TRUTH['operations']
    payload = str(len(held)) + '\n' + ''.join(f'{name} {symbol}\n' for name, symbol in held)
    payload += str(len(operations)) + '\n'
    for operation in operations:
        payload += (
            ' '.join(str(int(v)) for v in operation['r'])
            + ' '
            + ' '.join(str(v) for v in operation['t'])
            + '\n'
        )
    payload += ' '.join(str(v) for v in draws)
    run = subprocess.run(
        [str(atom_probe)], input=payload, capture_output=True, text=True, timeout=3, check=False
    )
    assert run.returncode == 0, (
        'The injected stream must produce a valid nonspecial atom: ' + run.stderr
    )
    name, symbol, letter, *numbers = run.stdout.split()
    xyz = [float(v) for v in numbers[:3]]
    assert name == label and symbol == label.rstrip(string.digits), (
        'A random supported element must have its next free element-number label'
    )
    general = max(TRUTH['wyckoff'], key=operator.itemgetter('multiplicity'))['letter']
    assert letter == general, (
        'A new atom must use the independent catalogue highest-multiplicity letter'
    )
    assert xyz == pytest.approx(coordinates, abs=1e-12), (
        'Injected draws must round to three decimals and redraw special positions'
    )
    assert all(0 <= v < 1 and abs(v * 1000 - round(v * 1000)) < 1e-9 for v in xyz), (
        'Every fractional coordinate must be in [0,1) at three decimals'
    )
    images = {
        tuple(
            round((sum(op['r'][3 * r + c] * xyz[c] for c in range(3)) + op['t'][r]) % 1, 9)
            for r in range(3)
        )
        for op in operations
    }
    assert len(images) == TRUTH['general'], (
        'The independently expanded orbit must have the general-position multiplicity'
    )
    assert int(numbers[3]) == len(draws), (
        'The injected source must consume redraws only when required'
    )
