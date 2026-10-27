"""Persisted IUCr spelling and both-rule reader parity from independent decimal cases."""

import json
import re
import shutil
import struct
from decimal import Decimal
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/report_units/reference.json').read_text())
INPUT = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'


def project(tmp_path, token, rule):
    destination = tmp_path / 'input'
    shutil.copytree(INPUT, destination)
    experiment = destination / 'experiments/bank.edi'
    text = experiment.read_text()
    assert text.count('pA 10.011 4()') == 1, 'The hand-input background token must be unambiguous'
    experiment.write_text(text.replace('pA 10.011 4()', 'pA 10.011 ' + token))
    if rule is not None:
        metadata = destination / 'project.edi'
        metadata.write_text(metadata.read_text() + '\n_su_format.rule ' + rule + '\n')
    return destination


def saved_token(destination):
    text = (destination / 'experiments/bank.edi').read_text()
    line = next(line for line in text.splitlines() if line.startswith('pA '))
    return line.split()[-1]


@pytest.mark.parametrize(('value', 'su', 'rule', 'expected'), REFERENCE['formats'])
def test_every_writer_uses_the_project_iucr_rule(value, su, rule, expected, tmp_path):
    loaded = engine.Project.load(project(tmp_path, '4()', rule))
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value = float(value)
    parameter.uncertainty = float(su)
    parameter.free = True
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    assert saved_token(destination) == expected, (
        'Written values must follow the independent IUCr decimal rule, decade recheck, '
        'half-away rounding and fixed-point edge spellings'
    )
    assert '_su_format.rule ' + rule in (destination / 'project.edi').read_text(), (
        'Every save must preserve the selected project uncertainty rule'
    )
    again = engine.Project.load(destination)
    shown, bracket = expected[:-1].split('(')
    places = len(shown.split('.')[1]) if '.' in shown else 0
    expected_su = Decimal(bracket) if '.' in bracket else Decimal(bracket) * Decimal(10) ** -places
    restored = again.experiments['bank'].background[0].intensity
    assert restored.value == pytest.approx(float(shown), rel=0, abs=0), (
        'Reload must retain the independently rounded value, including its sign'
    )
    assert restored.uncertainty == pytest.approx(float(expected_su), rel=0, abs=0), (
        'Decimal brackets store the uncertainty itself; integer brackets scale by place'
    )
    if float(value):
        assert restored.value != 0, 'A saved nonzero value must never be written as zero'
    second = tmp_path / 'again'
    again.save_as(second)
    assert saved_token(second) == expected, (
        'An IUCr-spelled value must be a save-load-save fixed point'
    )


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize(('decimals', 'digits', 'expected'), REFERENCE['readers'])
def test_both_rules_read_and_resave_integer_su_without_underflow(
    rule, decimals, digits, expected, tmp_path
):
    token = '5.' + '0' * decimals + '(' + digits + ')'
    source = project(tmp_path, token, rule)
    if expected is None and digits:
        with pytest.raises(ValueError, match=re.escape(token)) as error:
            engine.Project.load(source)
        assert token in str(error.value), (
            'A nonzero unrepresentable uncertainty must be refused by token'
        )
        return
    loaded = engine.Project.load(source)
    wanted = None if expected is None else float(expected)
    parameter = loaded.experiments['bank'].background[0].intensity
    assert parameter.uncertainty == wanted, (
        'Loading must scale integer uncertainty independently of the rule'
    )
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    restored = engine.Project.load(destination).experiments['bank'].background[0].intensity
    assert (restored.uncertainty is None) == (wanted is None), (
        'Save and reload must preserve engaged zero versus absent uncertainty'
    )
    if wanted is not None:
        assert restored.uncertainty >= wanted, (
            'The writer must never round a representable uncertainty down to zero'
        )


def test_absent_rule_defaults_and_unknown_rule_refuses(tmp_path):
    source = project(tmp_path, '2.16352(481)', None)
    loaded = engine.Project.load(source)
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    assert saved_token(destination) == '2.164(5)', (
        'An absent rule must select the IUCr recommendation-12 default'
    )
    metadata = source / 'project.edi'
    metadata.write_text(metadata.read_text() + '\n_su_format.rule iucr_7\n')
    with pytest.raises(ValueError, match=r'_su_format\.rule') as error:
        engine.Project.load(source)
    assert '_su_format.rule' in str(error.value), (
        'An unknown rule refusal must name its persisted item'
    )


def test_authors_roundtrip_keeps_utf8_and_semicolon_separator(tmp_path):
    source = project(tmp_path, '4()', 'iucr_99')
    metadata = source / 'project.edi'
    metadata.write_text(
        metadata.read_text() + '\n_metadata.authors "' + REFERENCE['authors'] + '"\n'
    )
    loaded = engine.Project.load(source)
    assert getattr(loaded.metadata, 'authors', None) == REFERENCE['authors'], (
        'The project loader must retain UTF-8 authors and their semicolon separator'
    )
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    assert engine.Project.load(destination).metadata.authors == REFERENCE['authors'], (
        'Authors must survive save and reload byte for byte'
    )


@pytest.mark.parametrize(('coefficient', 'expected'), REFERENCE['correlations'])
def test_written_correlations_follow_significant_digits(coefficient, expected, tmp_path):
    source = project(tmp_path, '4()', 'iucr_19')
    analysis = source / 'analysis/analysis.edi'
    loop = (
        '\nloop_\n_fit_parameter_correlation.id\n'
        '_fit_parameter_correlation.source_kind\n'
        '_fit_parameter_correlation.parameter_unique_name_i\n'
        '_fit_parameter_correlation.parameter_unique_name_j\n'
        '_fit_parameter_correlation.correlation\n'
    )
    analysis.write_text(
        analysis.read_text()
        + loop
        + '1 deterministic bank.background.pA.intensity bank.background.pB.intensity '
        + f'{coefficient!r}\n'
    )
    loaded = engine.Project.load(source)
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    written = (destination / 'analysis/analysis.edi').read_text()
    line = next(
        line
        for line in written.splitlines()
        if 'bank.background.pA.intensity bank.background.pB.intensity' in line
    )
    assert line.split()[-1] == expected, (
        'Written correlations require two significant digits, or three at |r| >= 0.95'
    )


@pytest.mark.parametrize(
    ('free', 'su'), [(False, 0.001), (True, None), (True, 0.0), (True, float('nan'))]
)
def test_fixed_absent_zero_and_nonfinite_uncertainty_keep_their_distinctions(free, su, tmp_path):
    loaded = engine.Project.load(project(tmp_path, '4()', 'iucr_19'))
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value = 0.10000000000000002
    parameter.uncertainty = su
    parameter.free = free
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    restored = engine.Project.load(destination).experiments['bank'].background[0].intensity
    assert struct.pack('>d', restored.value) == struct.pack('>d', 0.10000000000000002), (
        'Fixed, absent, zero and nonfinite uncertainty must retain the exact round-trip value'
    )
    assert restored.free == free, 'Uncertainty spelling must retain the parameter free state'
    wanted = 0.0 if not free or (su is not None and not su) else None
    assert restored.uncertainty == wanted, (
        'Bare fixed values reload with the retained engaged zero; free zero remains '
        'engaged while free absent and nonfinite uncertainties remain absent'
    )


def test_cell_length_with_larger_uncertainty_remains_loadable(tmp_path):
    loaded = engine.Project.load(project(tmp_path, '4()', 'iucr_19'))
    parameter = loaded.structures[0].cell.length_a
    parameter.value = 3.88
    parameter.uncertainty = 1e20
    parameter.free = True
    destination = tmp_path / 'saved-cell'
    loaded.save_as(destination)
    written = next((destination / 'structures').glob('*.edi')).read_text()
    token = re.search(r'^_cell\.length_a\s+(\S+)', written, re.MULTILINE)
    assert token is not None, 'The saved structure must contain its cell length'
    assert token[1] == '3.9(100000000000000000000.)', (
        'Zero-avoiding rounding keeps two value digits and a decimal uncertainty bracket'
    )
    restored = engine.Project.load(destination).structures[0].cell.length_a
    assert (restored.value, restored.uncertainty) == (3.9, 1e20), (
        'A cell length with a much larger s.u. must still load as the stated nonzero pair'
    )
