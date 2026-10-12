"""Newest parameter-name policy reaches both correlation endpoint fields."""

import shutil
from pathlib import Path

import edi as engine
import pytest

from tests.integration.py.test_newest_project_format import OLDER

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/loop_parameter_ids'
COEFFICIENT = '-.6257812345678901'
FILE = 'experiments/scan/bank.background[0].xye'


def correlation_loop(endpoint, identity, per_file, kind):
    names = (
        ['bank.background.pA.intensity', 'bank.background.pB.intensity']
        if kind == 'line-segment'
        else ['bank.background.base.coef', 'bank.background.ramp.coef']
    )
    names[endpoint] = identity
    return (
        'loop_\n_fit_parameter_correlation.id\n'
        '_fit_parameter_correlation.source_kind\n'
        '_fit_parameter_correlation.parameter_unique_name_i\n'
        '_fit_parameter_correlation.parameter_unique_name_j\n'
        '_fit_parameter_correlation.correlation\n'
        + ('_fit_parameter_correlation.file_path\n' if per_file else '')
        + 'witness crysta '
        + ' '.join(names)
        + ' '
        + COEFFICIENT
        + (' ' + FILE if per_file else '')
        + '\n'
    )


def stage(kind, endpoint, identity, per_file, destination):
    shutil.copytree(FIXTURE / kind, destination)
    analysis = destination / 'analysis/analysis.edi'
    text = analysis.read_text()
    if per_file:
        text = text.replace('_fitting_mode.type single', '_fitting_mode.type sequential')
        text += '\n_sequential_fit.data_dir experiments/scan\n'
        text += '_sequential_fit.file_pattern *.xye\n'
        scan = destination / 'experiments/scan'
        scan.mkdir()
        (destination / FILE).write_text('40 5.125 1\n44 6.375 1\n')
    analysis.write_text(text + '\n' + correlation_loop(endpoint, identity, per_file, kind))
    return destination


@pytest.mark.parametrize(('kind', 'older'), OLDER)
@pytest.mark.parametrize('endpoint', [0, 1], ids=['i', 'j'])
@pytest.mark.parametrize('per_file', [False, True], ids=['global', 'scan-file'])
def test_old_correlation_endpoint_is_a_short_named_refusal(
    kind, older, endpoint, per_file, tmp_path
):
    source = stage(kind, endpoint, older, per_file, tmp_path / 'input')
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    with pytest.raises((ValueError, RuntimeError)) as failure:
        engine.Project.load(source)
    message = str(failure.value)
    assert older in message, (
        'Every old correlation endpoint must be refused with its exact spelling'
    )
    assert 'older' in message.lower() and 'version' in message.lower(), (
        'Correlation endpoints obey the same named older-version rule as aliases and fit slots'
    )
    assert len(message) <= 240 and len(message.splitlines()) <= 2, (
        'An older correlation endpoint needs the same short load-dialog diagnostic'
    )
    assert {
        p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()
    } == before, 'Refusing an old correlation endpoint must preserve every original input byte'


@pytest.mark.parametrize('endpoint', [0, 1], ids=['i', 'j'])
@pytest.mark.parametrize('per_file', [False, True], ids=['global', 'scan-file'])
def test_current_numeric_row_endpoint_and_coefficient_text_roundtrip(endpoint, per_file, tmp_path):
    current = 'bank.background.1.intensity'
    source = stage('line-segment', endpoint, current, per_file, tmp_path / 'input')
    bank = source / 'experiments/bank.edi'
    bank.write_text(bank.read_text().replace('pA 10.011 4()', '1 10.011 4()'))
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text().replace('bank.background.pA.intensity', current))
    model = engine.Project.load(source)
    model.save_as(tmp_path / 'first')
    saved = (tmp_path / 'first/analysis/analysis.edi').read_text()
    assert current in saved.split(), (
        'A declared numeric row id is current, never an ordinal escape'
    )
    assert COEFFICIENT in saved.split(), (
        'Endpoint validation must retain the original coefficient text'
    )
    if per_file:
        assert FILE in saved.split(), 'A scan file path is not a parameter-name validation surface'
    engine.Project.load(tmp_path / 'first').save_as(tmp_path / 'second')
    assert (tmp_path / 'second/analysis/analysis.edi').read_bytes() == saved.encode(), (
        'Current endpoint names, coefficient text and optional file association roundtrip exactly'
    )
