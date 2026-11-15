"""Defect controls for the runtime boundary predicates."""

import shutil
import tomllib
from pathlib import Path

import pytest

from tests.fixtures.joint_series import oracle, subject


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


def test_worker_chunks_reject_both_restart_and_accidental_full_chain():
    template = [4.09, 1.8, 4.7]
    fitted = [[4.1, 2, 5], [4.16, 2.6, 4.2], [4.08, 1.7, 6], [4.1, 2, 5], [4.16, 2.6, 4.2]]
    valid = [template] * 3 + [fitted[2]] * 2
    oracle.starts(valid, template, fitted, chained=True, chunks=(3, 2))
    for bad in ([template] * 5, [template, *fitted[:-1]]):
        with pytest.raises(AssertionError):
            oracle.starts(bad, template, fitted, chained=True, chunks=(3, 2))
    after_skip = [fitted[0], fitted[1], fitted[3], fitted[4]]
    oracle.starts(
        [template] * 2 + [fitted[1]] * 2, template, after_skip, chained=True, chunks=(2, 2)
    )
    with pytest.raises(AssertionError):
        oracle.starts([template] * 4, template, after_skip, chained=True, chunks=(2, 2))


@pytest.mark.parametrize(
    ('value', 'sigma', 'shown', 'error'),
    [
        (2.16352, 0.00481, '2.1635', '.0049'),
        (-2.16352, 0.00481, '-2.1635', '.0049'),
        (1.23456, 0.01001, '1.235', '.011'),
    ],
)
def test_valid_report_rounding_and_corruption(value, sigma, shown, error):
    name = 'phase.atom_site_moment.A.spherical_polar'
    row = {name: shown, name + '.uncertainty': error}
    oracle.series_cells(row, name, value, sigma)
    with pytest.raises(AssertionError):
        oracle.series_cells({**row, name: str(value + 1)}, name, value, sigma)
    with pytest.raises(AssertionError):
        oracle.series_cells({**row, name + '.uncertainty': '0'}, name, value, sigma)
    token = f'{shown}({error})'
    oracle.category(
        'data_phase\n_atom_site_moment.spherical_polar ' + token + '\n',
        '_atom_site_moment.spherical_polar',
        value,
        sigma,
        rule='iucr_99',
    )


def test_start_chain_admits_rounded_predecessor_and_rejects_reset():
    template, fitted = [1.8], [[2.1635], [2.1635]]
    oracle.starts(
        [template, [2.16352]], template, fitted, chained=True, uncertainties=[[0.0049], [0.0049]]
    )
    with pytest.raises(AssertionError):
        oracle.starts(
            [template, template],
            template,
            fitted,
            chained=True,
            uncertainties=[[0.0049], [0.0049]],
        )


@pytest.mark.parametrize('channel', ['spherical_polar', 'spherical_azimuthal', 'follower'])
@pytest.mark.parametrize('defect', ['missing', 'zero', 'stale'])
def test_nonzero_angle_and_follower_errors_reject_bad_cells(channel, defect):
    name = (
        'linked_structure.other.scale'
        if channel == 'follower'
        else 'phase.atom_site_moment.A.' + channel
    )
    row = {name: '2.1635', name + '.uncertainty': '.0049'}
    oracle.series_cells(row, name, 2.16352, 0.00481)
    bad = dict(row)
    if defect == 'missing':
        bad.pop(name + '.uncertainty')
    else:
        bad[name + '.uncertainty'] = '0' if defect == 'zero' else '.011'
    with pytest.raises(AssertionError):
        oracle.series_cells(bad, name, 2.16352, 0.00481)


@pytest.mark.parametrize('defect', ['newer-other-build', 'archive', 'headers', 'source-identity'])
def test_native_subject_mismatch_is_refused(tmp_path, defect):
    build = tmp_path / 'build/selected'
    build.mkdir(parents=True)
    include = tmp_path / 'source/include/crysta'
    include.mkdir(parents=True)
    (include / 'model.hpp').write_text('selected headers')
    (build / 'CMakeCache.txt').write_text(
        'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(tmp_path / 'source') + '\n'
    )
    (build / '_crysta.so').write_bytes(b'selected extension')
    (build / 'libcrysta_core.a').write_bytes(b'selected archive')
    installed = tmp_path / 'installed/_crysta.so'
    installed.parent.mkdir()
    shutil.copyfile(build / '_crysta.so', installed)
    other = tmp_path / 'build/newest'
    other.mkdir()
    (other / '_crysta.so').write_bytes(b'unrelated extension')
    (other / 'libcrysta_core.a').write_bytes(b'unrelated archive')
    shutil.copyfile(build / 'CMakeCache.txt', other / 'CMakeCache.txt')
    assert subject.selected_core(tmp_path, installed) == (
        build / 'libcrysta_core.a',
        include.parent,
    ), 'Native selection must follow the selected extension bytes, regardless of build timestamps'
    subject.identity('selected\n', 'selected')

    def rejected():
        if defect == 'source-identity':
            subject.identity('other', 'selected')
        elif defect == 'headers':
            wrong = tmp_path / 'wrong/include'
            wrong.mkdir(parents=True)
            (wrong / 'model.hpp').write_text('different header')
            subject.selected_core(tmp_path, installed, include=wrong)
        else:
            subject.selected_core(tmp_path, installed, archive=other / 'libcrysta_core.a')

    with pytest.raises(AssertionError):
        rejected()
