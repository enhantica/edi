"""Defect controls for the runtime boundary predicates."""

import tomllib
from pathlib import Path

import pytest

from tests.fixtures.joint_series import oracle


@pytest.mark.parametrize(
    'change',
    [
        {'fit_result.success': 'False'},
        {'fit_result.reduced_chi_square': 'nan'},
        {'fit_result.termination': 'max_iter_exhausted'},
        {'fit_result.termination': 'cancelled'},
    ],
)
def test_seeded_failed_record_is_rejected(change):
    row = {
        'fit_result.success': 'True',
        'fit_result.reduced_chi_square': '9.96',
        'fit_result.termination': 'chi_converged',
    }
    oracle.outcome(row)
    with pytest.raises(AssertionError):
        oracle.outcome({**row, **change})


@pytest.mark.parametrize('factor', [0, 100, None])
def test_wrong_derived_error_is_rejected(factor):
    oracle.numeric_error(0.005879447357921313, 0.005879447357921313)
    with pytest.raises(AssertionError):
        oracle.numeric_error(
            None if factor is None else factor * 0.005879447357921313, 0.005879447357921313
        )


def test_template_restart_and_skip_reset_are_rejected():
    template = [4.1, 2, 5]
    successful = [[4.16, 2.6, 4.2], [4.08, 1.7, 6]]
    oracle.starts([template, successful[0]], template, successful, chained=True)
    with pytest.raises(AssertionError):
        oracle.starts([template, template], template, successful, chained=True)
    with pytest.raises(AssertionError):
        oracle.starts([template, successful[0]], template, successful, chained=False)


@pytest.mark.parametrize('defect', ['folder', 'pattern'])
def test_saved_link_defects_are_rejected(tmp_path, defect):
    external = tmp_path / 'external'
    external.mkdir()
    (external / 'T300K_b5.xy').write_text('1 2 3\n')
    text = (
        '_sequential_fit.data_dir "'
        + str(external)
        + (
            '"\nloop_\n_sequential_fit_experiment.experiment_id\n_sequential_fit_'
            'experiment.file_pattern\nzeta "*_b5.xy"\n'
        )
    )
    oracle.link(text, tmp_path, external, {'zeta': '*_b5.xy'})
    bad = (
        text.replace(str(external), str(tmp_path / 'unrelated'))
        if defect == 'folder'
        else text.replace('*_b5.xy', '*_wrong.xy')
    )
    with pytest.raises(AssertionError):
        oracle.link(bad, tmp_path, external, {'zeta': '*_b5.xy'})


def test_local_nightly_task_consumes_the_declared_seeded_file():
    root = Path(__file__).resolve().parents[3]
    command = tomllib.loads((root / 'pixi.toml').read_text())['tasks']['nightly-only-tests']['cmd']
    assert 'tests/system/py/test_joint_series_seeded_nightly.py' in command, (
        'The named local nightly task must actually execute its declared seeded witness'
    )


@pytest.mark.parametrize('token', ['1.23(0)', '1.23(400)'])
def test_wrong_saved_category_error_is_rejected(token):
    oracle.category(
        'data_phase\n_atom_site_moment.spherical_modulus 1.23(4)\n',
        '_atom_site_moment.spherical_modulus',
        1.23,
        0.04,
    )
    with pytest.raises(AssertionError):
        oracle.category(
            'data_phase\n_atom_site_moment.spherical_modulus ' + token + '\n',
            '_atom_site_moment.spherical_modulus',
            1.23,
            0.04,
        )


@pytest.mark.parametrize(
    'name',
    ['phase.atom_site_moment.A.spherical_modulus', 'linked_structure.other.weight_fraction'],
)
@pytest.mark.parametrize('defect', ['missing', 'stale-error', 'wrong-value'])
def test_wrong_series_derived_cells_are_rejected(name, defect):
    row = {name: '1.23', name + '.uncertainty': '.04'}
    oracle.series_cells(row, name, 1.23, 0.04)
    bad = dict(row)
    if defect == 'missing':
        bad.pop(name + '.uncertainty')
    elif defect == 'stale-error':
        bad[name + '.uncertainty'] = '.4'
    else:
        bad[name] = '9.99'
    with pytest.raises(AssertionError):
        oracle.series_cells(bad, name, 1.23, 0.04)


def test_tied_saved_fraction_error_is_numerical():
    text = (
        'data_bank\nloop_\n_linked_structure.structure_id\n'
        '_linked_structure.weight_fraction\nphase 0.67(4)\nother 0.33(4)\n'
    )
    oracle.category(text, '_linked_structure.weight_fraction', 0.33, 0.04)
    for token in ('0.33(0)', '0.33(400)'):
        with pytest.raises(AssertionError):
            oracle.category(
                text.replace('0.33(4)', token), '_linked_structure.weight_fraction', 0.33, 0.04
            )
