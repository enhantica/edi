"""Data-free reflection experiments retain their state until real rows are loaded."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.single_crystal_edges.inputs import project
from tests.fixtures.single_crystal_edges.observe import numbers, observe
from tests.integration.py.test_single_crystal import engine

ROOT = Path(__file__).resolve().parents[3]
BACKEND = 'edi'
ENTRANCES = [('create', 'missing')] + [
    (origin, form) for origin in ('text', 'file', 'project') for form in ('missing', 'empty')
]
EMPTY_STAGES = ['created:'] + [
    f'empty{cycle}:{stage}:' for cycle in range(3) for stage in ('saved', 'loaded')
]
MEASURED_STAGES = ['measured:', 'measured0:', 'measured1:']


@pytest.fixture(scope='module')
def native():
    selected = os.environ.get('SINGLE_CRYSTAL_EMPTY_OBSERVER')
    if selected:
        executable = Path(selected)
    else:
        directory = (
            Path(engine()._edi.__file__).resolve().parents[2]
            if BACKEND == 'edi'
            else (ROOT / 'build/crysta').resolve().parent
        )
        executable = (
            directory
            / (
                'single_crystal_edges'
                if BACKEND == 'edi'
                else 'tests/fixtures/single_crystal_edges'
            )
            / 'single_crystal_edge_probe'
        )
    assert executable.is_file(), 'The empty-state gate requires the prepared real model observer'
    identity = subprocess.check_output([str(executable), '--identity'], text=True).strip()
    assert (
        identity
        == hashlib.sha256(
            (ROOT / 'tests/fixtures/single_crystal_edges/probe.cpp').read_bytes()
        ).hexdigest()
    ), 'The prepared empty-state observer must match its complete committed source'
    return executable


def lifecycle(native, tmp_path, tof, origin, form):
    root = project(tmp_path / 'model', tof=tof, hkls=(), links=[('structure', '1', True)])
    experiment = root / 'experiments/bank.edi'
    if form == 'missing':
        text = experiment.read_text()
        experiment.write_text(text[: text.index('loop_\n_refln.index_h')])
    data = tmp_path / 'real.dat'
    rows = [(1, 2, 3, 18.5, 0.7), (-2, 1, 3, -2.75, 0.4), (1, 2, 3, 0, 0.6)]
    data.write_text(
        ''.join(
            ' '.join(map(str, (*row, *([1.2 + 0.2 * i] if tof else [])))) + '\n'
            for i, row in enumerate(rows)
        )
    )
    return observe(native, root, 'empty', origin, 'tof' if tof else 'cw', data)


@pytest.mark.parametrize('tof', [False, True], ids=['cw', 'tof'])
@pytest.mark.parametrize(('origin', 'form'), ENTRANCES)
def test_empty_reflection_state_survives_creation_and_repeated_round_trips(
    native, tmp_path, tof, origin, form
):
    result = lifecycle(native, tmp_path, tof, origin, form)
    assert result['ok'], (
        'Every empty single-crystal entrance and repeated save/reload must succeed: '
        + result['error']
    )
    for stage in EMPTY_STAGES:
        assert result[stage + 'state'] == [['1', '0', '0', str(int(tof)), '1']], (
            'An experiment with no reflection rows must remain data-free, pattern-free, '
            'and in its declared beam mode before and after every save/reload: ' + stage
        )
        for column in ('h', 'k', 'l', 'f2', 'su', 'lambda'):
            assert not numbers(result, stage + column), (
                'A missing or empty reflection loop must never acquire invented rows: '
                + stage
                + column
            )
        if BACKEND == 'edi':
            assert result[stage + 'editable'] == [['1', '1', '1', '1']], (
                'Both app type selectors must remain editable throughout the data-free '
                'creation/save/reload lifecycle: ' + stage
            )


@pytest.mark.parametrize('tof', [False, True], ids=['cw', 'tof'])
@pytest.mark.parametrize('origin', ['create', 'text', 'file', 'project'])
def test_real_reflection_load_locks_type_and_preserves_every_row_after_round_trips(
    native, tmp_path, tof, origin
):
    result = lifecycle(native, tmp_path, tof, origin, 'empty')
    assert result['ok'], (
        'Real reflection loading must follow the empty lifecycle: ' + result['error']
    )
    expected = {
        'h': [1, -2, 1],
        'k': [2, 1, 2],
        'l': [3, 3, 3],
        'f2': [18.5, -2.75, 0],
        'su': [0.7, 0.4, 0.6],
        'lambda': [1.2, 1.4, 1.6] if tof else [],
    }
    for stage in MEASURED_STAGES:
        assert result[stage + 'state'] == [['0', '0', '3', str(int(tof)), '1']], (
            'Only actual loaded rows may lock the type; every measured save/reload '
            'must retain that state and beam mode: ' + stage
        )
        for column, values in expected.items():
            assert numbers(result, stage + column) == pytest.approx(values, rel=0, abs=1e-15), (
                'Real reflection load and repeated round trips must retain signed indices, '
                'duplicates, weak or negative measurements, uncertainties and wavelengths: '
                + stage
                + column
            )
        if BACKEND == 'edi':
            assert result[stage + 'editable'] == [['0', '0', '1', '1']], (
                'Real data must lock both app type selectors without changing any '
                'reflection input on refusal: ' + stage
            )
