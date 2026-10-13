"""Serialization regression pins from the declared pre-change Release producer."""

import hashlib
import json
import shutil

import edi
import pytest

from tests.fixtures.shared_correlations.freeze_saved import HERE, hashes, loop_bytes

PROVENANCE = json.loads((HERE / 'saved-provenance.json').read_text())


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
        assert (destination / 'analysis/analysis.edi').read_bytes() == analysis.read_bytes(), (
            'An unchanged reload and save must retain every pre-change analysis byte'
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
    assert actual == expected, (
        'Saving the fixed single or template fitted state must retain the exact correlation loop'
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
        assert loop_bytes((destination / 'analysis/analysis.edi').read_bytes()) == loop, (
            'Reading saved rows must preserve pair17 and the literal decimal coefficient spelling'
        )
        project = edi.Project.load(destination)
