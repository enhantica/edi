"""Retain both immutable native domains and refuse undeclared vehicle projections."""

import copy
import json

import pytest

from tests.fixtures.e04_t11_wasm import cli_domains as domains
from tests.fixtures.e04_t11_wasm.compare import compare


def declaration():
    return json.loads((domains.HERE / 'cli-domains.json').read_text())


def current_record():
    # Protocol vectors retain frozen operands; this does not claim a live backend execution.
    text = (domains.ROOT / domains.PATHS['current_report']).read_text()
    return text.replace('stopping_rule=none', 'stopping_rule=chi_square_change')


def test_both_native_domains_retain_original_bytes_bounds_and_operand_inventory():
    selected = domains.domain()
    before = domains.historical_bytes(domains.input_bytes(), selected)
    assert b'_minimizer.stop_rule shift_su\n' in before[domains.ANALYSIS], (
        'The historical fixture keeps its authenticated explicit scalar stopping-rule input'
    )
    assert (
        selected['historical']['parameters'].keys() == selected['oracle']['parameters'].keys()
    ), 'Current backend parity retains every historical fitted operand'
    assert (
        selected['oracle']['relative_tolerance'],
        selected['oracle']['absolute_tolerance'],
    ) == (1e-9, 1e-11), (
        'The domain adaptation preserves the original relative and absolute numerical bounds'
    )
    compare(
        (domains.ROOT / domains.PATHS['historical_report']).read_text(), selected['historical']
    )
    domains.compare_current(current_record(), selected['oracle'])


@pytest.mark.parametrize('escape', ['path', 'hash', 'conditions', 'project', 'empty'])
def test_native_domain_refuses_wrong_anchor_and_condition_declarations(escape):
    bad = declaration()
    if escape == 'path':
        bad['files']['current_oracle']['path'] = domains.PATHS['historical_oracle']
    elif escape == 'hash':
        bad['files']['current_report']['sha256'] = '0' * 64
    elif escape == 'conditions':
        bad['conditions']['descent'] = 'multistart_prune'
    elif escape == 'project':
        bad['inputs'] = 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project'
    else:
        bad = {}
    with pytest.raises(ValueError, match=r'domain|anchor'):
        domains.domain(bad)


@pytest.mark.parametrize('escape', ['missing', 'extra', 'analysis', 'scientific'])
def test_current_input_refuses_every_unarchived_byte_or_inventory_change(escape):
    actual = domains.input_bytes()
    if escape == 'missing':
        actual.pop('project.edi')
    elif escape == 'extra':
        actual['unrecorded.edi'] = b'new input'
    elif escape == 'analysis':
        actual[domains.ANALYSIS] += b'\n_minimizer.descent ladder\n'
    else:
        name = next(name for name in actual if name.startswith('structures/'))
        actual[name] += b'\n'
    with pytest.raises(ValueError, match=r'historical inputs|minimizer input'):
        domains.historical_bytes(actual, domains.domain())


def test_vehicle_changes_only_the_declared_conditions_before_any_fit(tmp_path):
    original = domains.input_bytes()
    project = tmp_path / 'project'
    domains.vehicle(project)
    domains.verify_vehicle(project, original)
    analysis = project / domains.ANALYSIS
    assert analysis.read_bytes() == original[domains.ANALYSIS] + domains.SUFFIX, (
        'The backend vehicle declares ladder and chi-square stopping before solving'
    )
    analysis.write_bytes(analysis.read_bytes().replace(b'ladder', b'multistart_prune'))
    with pytest.raises(ValueError, match='declared ladder'):
        domains.verify_vehicle(project, original)


def test_current_report_refuses_wrong_conditions_bounds_and_duplicate_fields():
    oracle = domains.domain()['oracle']
    good = current_record()
    domains.compare_current(good, oracle)
    for bad in (
        good.replace('descent=ladder', 'descent=multistart_prune'),
        good.replace('stopping_rule=chi_square_change', 'stopping_rule=shift_su'),
        good.replace('iterations=9', 'iterations=1001'),
        good + '\ndescent=ladder\n',
    ):
        with pytest.raises(ValueError, match=r'condition|bound|duplicated'):
            domains.compare_current(bad, oracle)


def test_current_domain_retains_every_original_missing_nonfinite_and_perturbation_control():
    oracle = domains.domain()['oracle']
    good = domains.fields(current_record())
    keys = [*oracle['parameters'], 'reduced_chi_square']
    for key in keys:
        for value in ('nan', 'inf', str(float(good[key]) * 1.000001)):
            bad = {**good, key: value}
            with pytest.raises(ValueError, match='wasm fit'):
                domains.compare_current('\n'.join(f'{k}={v}' for k, v in bad.items()), oracle)
        missing = copy.copy(good)
        missing.pop(key)
        with pytest.raises(ValueError, match='wasm fit'):
            domains.compare_current('\n'.join(f'{k}={v}' for k, v in missing.items()), oracle)
