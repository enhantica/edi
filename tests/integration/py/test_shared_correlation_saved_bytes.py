"""Serialization regression pins from the declared pre-change Release producer."""

import hashlib
import json
import shutil

import edi
import pytest

from tests.fixtures.report_units.iucr_reference import rounded_record
from tests.fixtures.shared_correlations.freeze_saved import HERE, hashes, loop_bytes

PROVENANCE = json.loads((HERE / 'saved-provenance.json').read_text())


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_frozen_numeric_table_keeps_the_declared_pre_change_fitted_state(case):
    provenance = json.loads((HERE / 'numeric-provenance.json').read_text())['cases'][case]
    data = (HERE / (case + '-numeric.table')).read_bytes()
    assert hashlib.sha256(data).hexdigest() == provenance['numeric_sha256'], (
        'The generated-row input must retain its frozen fitted numeric-state digest'
    )
    loop = (HERE / (case + '-correlations.edi')).read_bytes()
    assert (
        hashlib.sha256(loop).hexdigest()
        == provenance['producer_loop_sha256']
        == PROVENANCE['cases'][case]['loop_sha256']
    ), 'The numeric regression input must remain tied to the original pre-change producer bytes'
    fields = data.decode().splitlines()
    size = int(fields[0])
    names = fields[1 : size + 1]
    values = [float.fromhex(value) for value in fields[size + 2 :]]
    rows = [line.split() for line in loop.decode().splitlines() if ' deterministic ' in line]
    assert len(values) == int(fields[size + 1]) == len(rows) == size * (size - 1) // 2, (
        'The row-free numeric input must retain every off-diagonal fitted coefficient'
    )
    pairs = [(names[i], names[j]) for i in range(size) for j in range(i + 1, size)]
    assert pairs == [(row[2], row[3]) for row in rows], (
        'Frozen numeric names must preserve the complete original covariance column order'
    )
    assert values == [float(row[4]) for row in rows], (
        'Every frozen binary coefficient must equal the original fitted double exactly'
    )


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_pre_change_correlation_bytes_survive_unchanged_reload(tmp_path, case):
    source = tmp_path / 'source'
    shutil.copytree(HERE / (case + '-input'), source)
    analysis = HERE / (case + '-analysis.edi')
    assert (
        hashlib.sha256(analysis.read_bytes()).hexdigest()
        == PROVENANCE['cases'][case]['analysis_sha256']
    ), 'The committed analysis bytes must retain the declared pre-change producer digest'
    (source / 'analysis/analysis.edi').write_bytes(analysis.read_bytes())
    loaded = edi.Project.load(source)
    for name in ['once', 'twice']:
        destination = tmp_path / name
        loaded.save_as(destination)
        assert (destination / 'analysis/analysis.edi').read_bytes() == rounded_record(
            analysis.read_bytes()
        ), (
            'Before exact pre-change spelling; after only parameter s.u. and correlation '
            'tokens receive independently calculated IUCr spelling; all other bytes stay pinned'
        )
        loaded = edi.Project.load(destination)


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_fitted_correlation_loop_matches_pre_change_regression_pin(tmp_path, case):
    source = tmp_path / 'source'
    shutil.copytree(HERE / (case + '-input'), source)
    assert hashes(source) == PROVENANCE['cases'][case]['input_sha256'], (
        'The fixed-state witness must retain all exact pre-change producer input bytes'
    )
    fixed_state = (HERE / (case + '-analysis.edi')).read_bytes()
    expected = (HERE / (case + '-correlations.edi')).read_bytes()
    assert (
        hashlib.sha256(fixed_state).hexdigest() == PROVENANCE['cases'][case]['analysis_sha256']
    ), 'The fixed fitted state must retain every byte from its declared pre-change producer'
    assert hashlib.sha256(expected).hexdigest() == PROVENANCE['cases'][case]['loop_sha256'], (
        'The exact coefficient spelling must retain its frozen serialization digest'
    )
    assert loop_bytes(fixed_state) == expected, (
        'The fixed fitted state and separate loop pin must contain identical bytes'
    )
    (source / 'analysis/analysis.edi').write_bytes(fixed_state)
    project = edi.Project.load(source)
    saved = tmp_path / 'saved'
    project.save_as(saved)
    actual = loop_bytes((saved / 'analysis/analysis.edi').read_bytes())
    assert actual == rounded_record(expected), (
        'Saving the fixed single or template fitted state preserves every loop byte except '
        'the independently IUCr-rounded coefficient tokens'
    )
    reopened = edi.Project.load(saved)
    reopened.save_as(tmp_path / 'again')
    assert loop_bytes((tmp_path / 'again/analysis/analysis.edi').read_bytes()) == actual, (
        'The saved fixed fitted rows must keep every id and coefficient byte on reload'
    )


@pytest.mark.parametrize('coefficient', ['0.50', '-0.84016805041680576'])
def test_loaded_nonordinal_id_and_decimal_spelling_survive_views_and_save(tmp_path, coefficient):
    source = tmp_path / 'source'
    shutil.copytree(HERE / 'single-input', source)
    loop = (
        b'loop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
        b'_fit_parameter_correlation.parameter_unique_name_i\n'
        b'_fit_parameter_correlation.parameter_unique_name_j\n'
        b'_fit_parameter_correlation.correlation\n'
        b'pair17 deterministic bank.background.base.coef bank.background.ramp.coef '
        + coefficient.encode()
        + b'\n'
    )
    path = source / 'analysis/analysis.edi'
    path.write_bytes(path.read_bytes().rstrip() + b'\n\n' + loop)
    project = edi.Project.load(source)
    for name in ['once', 'twice']:
        destination = tmp_path / name
        project.save_as(destination)
        assert loop_bytes((destination / 'analysis/analysis.edi').read_bytes()) == rounded_record(
            loop
        ), (
            'Reading saved rows retains pair17, both endpoints and source kind; only the '
            'coefficient changes to the independent IUCr spelling, then stays byte identical'
        )
        project = edi.Project.load(destination)
