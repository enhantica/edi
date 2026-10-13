"""Closed-form controls for the one declared inactive-weight byte projection."""

import pytest

from tests.fixtures.fitting_modes.historical_bytes import historical_analysis


@pytest.mark.parametrize('mode', ['single', 'sequential', 'independent'])
def test_inactive_weight_projection_preserves_every_other_byte(tmp_path, mode):
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'analysis').mkdir()
    for name in ['alpha', 'beta']:
        (tmp_path / f'experiments/{name}.edi').write_text(f'data_{name}\n')
    (tmp_path / 'analysis/analysis.edi').write_text(
        'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nalpha 0.625\nbeta 2.125\n'
    )
    prefix = (
        f'_edi.schema_version 3\n\n_fitting_mode.type {mode}\n\n_minimizer.max_iterations 123\n'
    ).encode()
    loop = b'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nalpha 0.625\nbeta 2.125\n'
    assert historical_analysis(tmp_path, prefix) == prefix + b'\n' + loop, (
        'The declared projection must restore only the historical inactive loop and its separator'
    )
    result = b'\n_fit_result.result_kind single\n_fit_result.objective_value 0.375\n'
    assert historical_analysis(tmp_path, prefix + result) == prefix + b'\n' + loop + result, (
        'The inactive-weight projection must retain every saved result byte and insertion boundary'
    )
    changed = prefix.replace(b'123', b'124')
    assert historical_analysis(tmp_path, changed) != prefix + b'\n' + loop, (
        'An unrelated saved setting change must remain visible to the immutable byte witness'
    )
    with pytest.raises(AssertionError, match='omit the entire'):
        historical_analysis(tmp_path, prefix + b'\n' + loop)
    with pytest.raises(AssertionError, match='exactly'):
        historical_analysis(tmp_path, prefix + b'\n')
    joint = prefix.replace(mode.encode(), b'joint') + b'\n' + loop
    assert historical_analysis(tmp_path, joint) == joint, (
        'The active joint category must never be projected or removed from a saved byte witness'
    )


@pytest.mark.parametrize('damage', ['unknown', 'duplicate', 'extra-column'])
def test_inactive_weight_projection_refuses_undeclared_input_rows(tmp_path, damage):
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'experiments/alpha.edi').write_text('data_alpha\n')
    (tmp_path / 'analysis').mkdir()
    loop = 'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nalpha 0.625\n'
    if damage == 'unknown':
        loop += 'beta 2.125\n'
    elif damage == 'duplicate':
        loop += 'alpha 2.125\n'
    else:
        loop = loop.replace('_joint_fit.weight', '_joint_fit.extra\n_joint_fit.weight')
    (tmp_path / 'analysis/analysis.edi').write_text(loop)
    with pytest.raises(AssertionError, match='Historical-weight'):
        historical_analysis(tmp_path, b'_fitting_mode.type single\n')
