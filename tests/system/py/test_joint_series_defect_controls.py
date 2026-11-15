"""Defect controls for the runtime boundary predicates."""

import copy
import json
import shutil
import tomllib
from pathlib import Path
from types import SimpleNamespace

import gemmi
import numpy as np
import pytest

from tests.fixtures.cif2 import read_block
from tests.fixtures.e05_t1.iteration_record import (
    check_persisted_iterations,
    pin_declared_descent,
    selected_parameter_count,
)
from tests.fixtures.e05_t1.start_bytes import absorption_start_bytes
from tests.fixtures.joint_series import ncaf, oracle, persistence, prepare_native, subject
from tests.integration.py.test_relation_derived_values import moment_project


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


def test_sequential_workers_reject_chunk_restart_and_preserve_skip_chain():
    template = [4.09, 1.8, 4.7]
    written = [[4.1, 2, 5], [4.16, 2.6, 4.2], [4.08, 1.7, 6], [4.1, 2, 5], [4.16, 2.6, 4.2]]
    oracle.starts([template, *written[:-1]], template, written, chained=True)
    for wrong in ([template] * 5, [template] * 3 + [written[2]] * 2):
        with pytest.raises(AssertionError):
            oracle.starts(wrong, template, written, chained=True)
    after_skip = [written[0], written[1], written[3], written[4]]
    oracle.starts([template, *after_skip[:-1]], template, after_skip, chained=True)
    with pytest.raises(AssertionError):
        oracle.starts([template] * 4, template, after_skip, chained=True)


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


def test_written_predecessor_rejects_full_precision_and_template_carry():
    template, written = [1.8], [[2.1635], [2.1635]]
    oracle.starts([template, written[0]], template, written, chained=True)
    for wrong in (template, [2.16352], [2.1635000001], [float('nan')], [float('inf')]):
        with pytest.raises(AssertionError):
            oracle.starts([template, wrong], template, written, chained=True)


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


@pytest.mark.parametrize('defect', ['stale-value', 'stale-error', 'wrong-value'])
def test_saved_fraction_admits_adoption_and_rejects_stale_state(defect):
    values, errors = np.array([2.16352, 1.23456, 3.78654]), np.array([0.00481, 0.01001, 0.00678])
    covariance = np.diag(errors**2)
    covariance[0, 1] = covariance[1, 0] = 0.35 * errors[0] * errors[1]
    cells = [[4.1, 5.3, 6.7, 90, 90, 90], [4.7, 4.9, 4.1 * 5.3 * 6.7 / (4.7 * 4.9), 90, 90, 90]]
    adopted = persistence.adopted_fraction(values, errors, covariance, cells)
    old_value = values[1] / sum(values[:2])
    gradient = np.array([-values[1], values[0], 0]) / sum(values[:2]) ** 2
    old_error = np.sqrt(gradient @ covariance @ gradient)

    def text(value, error):
        return (
            'data_bank\nloop_\n_linked_structure.structure_id\n'
            '_linked_structure.weight_fraction\nphase .6(.1)\n'
            f'other {value:.17g}({error:.17g})\n'
        )

    oracle.category(
        text(adopted['fraction'], adopted['sigma']),
        '_linked_structure.weight_fraction',
        adopted['fraction'],
        adopted['sigma'],
    )
    value = old_value if defect == 'stale-value' else adopted['fraction']
    error = old_error if defect == 'stale-error' else adopted['sigma']
    if defect == 'wrong-value':
        value += 0.01
    with pytest.raises(AssertionError):
        oracle.category(
            text(value, error),
            '_linked_structure.weight_fraction',
            adopted['fraction'],
            adopted['sigma'],
        )


@pytest.mark.parametrize('defect', ['correlation', 'marginal'])
def test_saved_moment_covariance_corruption_is_rejected(tmp_path, defect):
    root = tmp_path / 'moment'
    _, inputs, covariance = moment_project(root)
    persistence.moment_reference(root, inputs, covariance)
    path = root / ('analysis/analysis.edi' if defect == 'correlation' else 'structures/phase.edi')
    text = path.read_text()
    changed = (
        text.replace(' 0.35\n', ' 0\n')
        if defect == 'correlation'
        else text.replace('1.2(0.04)', '1.2(0.4)')
    )
    assert changed != text, (
        'The corruption control must actually alter a supplied covariance input'
    )
    path.write_text(changed)
    with pytest.raises(AssertionError):
        persistence.moment_reference(root, inputs, covariance)


@pytest.mark.parametrize('defect', ['missing', 'stale-source', 'changed-binary'])
def test_native_preparation_never_compiles_to_repair_bad_evidence(tmp_path, monkeypatch, defect):
    spec = {'engine': 'crysta', 'source': 'authored-selected-observer'}
    build = prepare_native.directory(tmp_path, spec)
    build.mkdir(parents=True)
    binary = build / 'starts'
    binary.write_bytes(b'authored prepared observation')
    receipt = {'spec': spec, 'binary_sha256': subject.digest(binary).hex()}
    manifest = build / 'prepared.json'
    manifest.write_text(json.dumps(receipt))
    assert prepare_native.validate(build, spec) == binary, (
        'A prepared observer must be admitted only with matching source and executable evidence'
    )
    if defect == 'missing':
        manifest.unlink()
    elif defect == 'stale-source':
        receipt['spec'] = {'engine': 'crysta', 'source': 'unrelated observer'}
        manifest.write_text(json.dumps(receipt))
    else:
        binary.write_bytes(b'unrelated binary')
    monkeypatch.setattr(prepare_native, 'configuration', lambda *_: (spec, [], [], []))

    def forbidden(*_args, **_kwargs):
        message = 'The behavior gate may not invoke a compiler or repair its preparation'
        raise RuntimeError(message)

    monkeypatch.setattr(prepare_native.subprocess, 'run', forbidden)
    with pytest.raises(AssertionError):
        prepare_native.prepared(tmp_path, SimpleNamespace(__name__='crysta'))


def test_native_preparation_is_declared_before_its_consumers():
    root = Path(__file__).resolve().parents[3]
    tasks = tomllib.loads((root / 'pixi.toml').read_text())['tasks']
    consumers = (
        ('test', 'suite-coverage', 'group-nightly', 'per-pr-measure')
        if root.name == 'crysta'
        else ('test', 'quick-tests', 'system-tests-part', 'per-pr-measure')
    )
    prepare_native.declared_for(tasks, consumers)
    bad = copy.deepcopy(tasks)
    bad[consumers[0]]['depends-on'] = []
    with pytest.raises(AssertionError):
        prepare_native.declared_for(bad, consumers)


@pytest.mark.parametrize(
    'compound', ['[1 2]', '[1 [2 3]]', '[1 # kept comment\n 2]', '["a]b" [1 2] \'x#y\']']
)
def test_cif2_list_cells_preserve_scalar_category_checks(compound):
    text = (
        '#\\#CIF_2.0\ndata_bank\nloop_\n_linked_structure.structure_id\n'
        '_linked_structure.weight_fraction\nphase 0.67(.04)\nother 0.33(.04)\n'
        'loop_\n_data.axis\n_data.intensity_calc\n_pd_calc.component_intensities_net\n'
        f'1 9 {compound}\n2 10 {compound}\n_caption "literal [caption]"\n'
    )
    block = read_block(text)
    assert len(list(block.find_values('_data.axis'))) == 2, (
        'Each CIF2 component list must remain one loop cell for independent scalar checks'
    )
    assert [
        gemmi.cif.as_string(t) for t in block.find_values('_pd_calc.component_intensities_net')
    ] == [compound, compound], 'The scalar projection must retain a whole CIF2 list in one cell'
    assert gemmi.cif.as_string(block.find_value('_caption')) == 'literal [caption]', (
        'Quoted scalar bracket text must never be treated as a compound token'
    )
    oracle.category(text, '_linked_structure.weight_fraction', 0.33, 0.04)
    with pytest.raises(AssertionError):
        oracle.category(
            text.replace('other 0.33', 'other 0.99'),
            '_linked_structure.weight_fraction',
            0.33,
            0.04,
        )


def test_cli_iteration_record_follows_its_producing_run():
    check_persisted_iterations({'_fit_result.iterations': '4'}, {'iterations': '4'})
    with pytest.raises(AssertionError):
        check_persisted_iterations({'_fit_result.iterations': '7'}, {'iterations': '4'})


@pytest.mark.parametrize('points', [0, 101])
def test_seeded_cadence_ceiling_refuses_before_generating_data(tmp_path, monkeypatch, points):
    def forbidden(*_args, **_kwargs):
        message = 'An out-of-policy point count must be refused before copying observations'
        raise RuntimeError(message)

    monkeypatch.setattr(ncaf.shutil, 'copytree', forbidden)
    with pytest.raises(AssertionError):
        ncaf.prepare(tmp_path / 'series', points=points, descent='fast_descent')


def test_seeded_scale_policy_is_100_points_and_five_banks():
    assert ncaf.MAX_POINTS == 100, (
        'Owner 6c4f7a9d9 sets the slow seeded cadence ceiling at 100 points'
    )
    assert len(ncaf.BANKS) == 5, 'Owner 6c4f7a9d9 retains the five actual NCAF WISH banks'


def test_cli_model_count_drops_only_the_retired_named_slot():
    row = {
        'n_parameters': 4,
        'parameter_names': [
            'cell.length_a',
            'bank.scale',
            'bank.absorption.abscor1',
            'bank.absorption.abscor2',
        ],
    }
    assert selected_parameter_count(row) == 3, (
        'ADR-0123 removes only the inactive named slot from the independent model projection'
    )
    with pytest.raises(AssertionError):
        selected_parameter_count({**row, 'n_parameters': 3})


def test_cli_fixture_declares_its_historical_descent_without_overwriting_it(tmp_path):
    path = tmp_path / 'analysis.edi'
    path.write_text('_fitting_mode.type joint\n')
    pin_declared_descent(path, 'ladder')
    first = path.read_bytes()
    assert b'_minimizer.descent ladder' in first, (
        'The historical ladder fixture must not inherit the newer fast-descent default'
    )
    pin_declared_descent(path, 'ladder')
    assert path.read_bytes() == first, (
        'An already explicit historical descent must retain its bytes'
    )
    with pytest.raises(AssertionError):
        pin_declared_descent(path, 'fast_descent')


@pytest.mark.parametrize('defect', ['active-input', 'retired-nonzero', 'unrelated-byte'])
def test_cli_corpus_identity_accepts_only_the_inert_field_transition(defect):
    original = b'data_wish\n_absorption.abscor1 0.0(10)\n_absorption.abscor2 0.0\n'
    current = original.replace(b'_absorption.abscor2 0.0\n', b'')
    name = 'experiments/wish_5_6.edi'
    assert absorption_start_bytes(name, current) == original, (
        'Only the committed inactive zero-field deletion may adapt the CLI corpus identity'
    )
    if defect == 'active-input':
        bad = current.replace(b'0.0(10)', b'0.1(10)')
    elif defect == 'retired-nonzero':
        bad = original.replace(b'abscor2 0.0', b'abscor2 1.0')
    else:
        bad = current + b'# changed unrelated byte\n'
    assert absorption_start_bytes(name, bad) != original, (
        'The corpus identity rejects active, nonzero retired and unrelated changes'
    )


@pytest.mark.parametrize('layout', ['direct', 'nested', 'external'])
def test_native_build_location_disambiguates_identical_extension_copies(tmp_path, layout):
    root = tmp_path / 'checkout'
    root.mkdir()
    source = tmp_path / 'source'
    (source / 'include').mkdir(parents=True)
    selected = tmp_path / 'external' if layout == 'external' else root / 'build/selected'
    selected.mkdir(parents=True)
    extension = selected / ('_crysta.so' if layout == 'direct' else 'python/crysta/_crysta.so')
    extension.parent.mkdir(parents=True, exist_ok=True)
    extension.write_bytes(b'selected extension')
    (selected / 'libcrysta_core.a').write_bytes(b'selected archive')
    cache = 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(source) + '\n'
    (selected / 'CMakeCache.txt').write_text(cache)
    copied = root / 'build/other'
    copied.mkdir(parents=True)
    (copied / '_crysta.so').write_bytes(b'selected extension')
    (copied / 'libcrysta_core.a').write_bytes(b'other archive')
    (copied / 'CMakeCache.txt').write_text(cache)
    assert subject.selected_core(root, extension) == (
        selected / 'libcrysta_core.a',
        source / 'include',
    ), 'A loaded extension must select its own CMake core before copied artifacts'


@pytest.mark.parametrize('defect', ['none', 'linked-sha', 'package', 'prefix'])
def test_native_edi_local_build_qualifies_its_cmake_prefix(tmp_path, defect):
    root = tmp_path / 'edi'
    source = tmp_path / 'source'
    (source / 'core/include').mkdir(parents=True)
    artifact = root / 'build/local-configuration'
    extension = artifact / 'python/edi/_edi.so'
    extension.parent.mkdir(parents=True)
    extension.write_bytes(b'selected edi extension')
    (artifact / 'core').mkdir()
    (artifact / 'core/libedi_core.a').write_bytes(b'edi core')
    sdk = tmp_path / 'selected-sdk'
    package = sdk / 'lib/cmake/crysta'
    package.mkdir(parents=True)
    config = package / 'crystaConfig.cmake'
    config.write_text('selected package')
    (sdk / 'lib/libcrysta_core.a').write_bytes(b'crysta core')
    (sdk / 'include').mkdir()
    (sdk / '.crysta-sha').write_text('a' * 40)
    (artifact / '.crysta-linked-sha').write_text('a' * 40)
    (artifact / 'CMakeCache.txt').write_text(
        'crysta_DIR:PATH=' + str(package) + '\nCMAKE_HOME_DIRECTORY:INTERNAL=' + str(source) + '\n'
    )
    if defect == 'linked-sha':
        (artifact / '.crysta-linked-sha').write_text('b' * 40)
    elif defect == 'package':
        config.unlink()
    elif defect == 'prefix':
        (sdk / 'lib/libcrysta_core.a').unlink()
    if defect != 'none':
        with pytest.raises(AssertionError):
            subject.selected_edi(root, extension)
    else:
        assert subject.selected_edi(root, extension) == (
            artifact,
            sdk,
            source / 'core/include',
            'a' * 40,
        ), 'A local edi observer must use its selected package and linked source identity'
