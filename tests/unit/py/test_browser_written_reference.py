"""Literal protocol counterfactuals, not captured fit results or new scientific pins."""

import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tests.fixtures.e04_t11_wasm import written


def raw_control():
    fixture = {
        'relative_tolerance': 1e-9,
        'absolute_tolerance': 1e-11,
        'native_start_and_finish': {
            'initial_reduced_chi_square': 9.25,
            'final_reduced_chi_square': 1.125,
            'rwp': 0.125,
            'iterations': 3,
        },
    }
    old = {
        'labels': ['cell_length_a', 'broad_gauss_u'],
        'values': [3.25, 0.125],
        'covariance': [0.04, 0, 0, 0.0009],
        'n_data': 23,
    }
    paths = ['structure.cell.length_a', 'experiment.peak.broad_gauss_u']
    raw = {
        **fixture['native_start_and_finish'],
        'status': 'FitStatus.DONE',
        'converged': True,
        'values': dict(zip(paths, old['values'], strict=True)),
        'uncertainty': dict(zip(paths, [0.2, 0.03], strict=True)),
    }
    report = 'status=done\nconverged=true\nn_points_fitted=23\n'
    candidates = {column: {path} for column, path in enumerate(paths)}
    names = {'structures/s.edi': 's', 'experiments/b.edi': 'b'}
    return fixture, old, raw, report, candidates, names, Path('/unused-authored-control')


def test_raw_reference_qualifies_every_value_su_global_and_exact_point_count():
    args = raw_control()
    selected = written.qualify_raw(*args)
    assert selected == {0: 'structure.cell.length_a', 1: 'experiment.peak.broad_gauss_u'}, (
        'Raw identity must use independent columns and owned named paths; '
        'never equal-value matching'
    )
    for field in ('values', 'uncertainty'):
        for path in args[2][field]:
            mutated = copy.deepcopy(args)
            mutated[2][field][path] += 0.01
            with pytest.raises(ValueError, match='raw value or SU'):
                written.qualify_raw(*mutated)
    for name in args[0]['native_start_and_finish']:
        mutated = copy.deepcopy(args)
        mutated[2][name] += 1
        with pytest.raises(ValueError, match='raw global'):
            written.qualify_raw(*mutated)


@pytest.mark.parametrize(
    'mutation',
    [
        'missing',
        'extra',
        'renamed',
        'ambiguous',
        'wrong-owner',
        'nan',
        'negative-su',
        'not-converged',
        'not-done',
        'false-flag',
    ],
)
def test_raw_reference_refuses_incomplete_or_corrupted_capture(mutation):
    args = list(copy.deepcopy(raw_control()))
    raw, choices = args[2], args[4]
    path = next(iter(raw['values']))
    if mutation == 'missing':
        raw['values'].pop(path)
    elif mutation == 'extra':
        raw['values']['unowned'] = raw['uncertainty']['unowned'] = 1
    elif mutation == 'renamed':
        raw['values']['renamed'] = raw['values'].pop(path)
        raw['uncertainty']['renamed'] = raw['uncertainty'].pop(path)
    elif mutation == 'ambiguous':
        choices[0].add('structure.cell.length_b')
        raw['values']['structure.cell.length_b'] = 3.25
        raw['uncertainty']['structure.cell.length_b'] = 0.2
    elif mutation == 'wrong-owner':
        args[1]['labels'][0] = 'cell_length_b'
    elif mutation == 'nan':
        raw['values'][path] = float('nan')
    elif mutation == 'negative-su':
        raw['uncertainty'][path] = -0.2
    elif mutation == 'not-converged':
        raw['converged'] = False
    elif mutation == 'not-done':
        raw['status'] = 'FitStatus.CANCELLED'
    else:
        raw['converged'] = 1
    with pytest.raises(ValueError, match=r'raw |machine|written reference'):
        written.qualify_raw(*args)


@pytest.mark.parametrize(
    'report',
    [
        'status=done\nconverged=true\n',
        'status=done\nconverged=true\nn_points_fitted=24\n',
        'status=done\nconverged=true\nn_points_fitted=23.0\n',
        'status=done\nconverged=true\nn_points_fitted=23\nn_points_fitted=23\n',
        'status=cancelled\nconverged=true\nn_points_fitted=23\n',
    ],
)
def test_machine_report_point_count_and_terminal_state_are_not_optional(report):
    args = list(raw_control())
    args[3] = report
    with pytest.raises(ValueError, match=r'raw |machine|written reference'):
        written.qualify_raw(*args)


def write_project(root, *, reverse=False):
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'project.edi').write_text('_edi.schema_version 3\n')
    (root / 'structures/s.edi').write_text('data_s\n_cell.length_a 3.25(2)\n')
    categories = [
        '_peak.type cwl-tch\n',
        '_instrument.calib_twotheta_offset 0.25(3)\n_instrument.type diffractometer\n',
        '_absorption.type empirical\n_absorption.abscor1 0.125(4)\n',
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\ns 2.50(5)\n',
    ]
    (root / 'experiments/b.edi').write_text(
        'data_b\n' + ''.join(reversed(categories) if reverse else categories)
    )


def test_written_missing_categories_are_compared_by_owned_identity(tmp_path):
    expected, actual = tmp_path / 'reference', tmp_path / 'browser'
    write_project(expected)
    write_project(actual, reverse=True)
    fixture = {'relative_tolerance': 1e-9, 'absolute_tolerance': 1e-11}
    assert written.compare_written(actual, expected, fixture)['extra_cells'] == 6, (
        'Instrument, complete linked storage and absorption must survive category reordering'
    )
    source = (actual / 'experiments/b.edi').read_text()
    for before, after in [
        ('0.25(3)', '0.26(3)'),
        ('0.25(3)', '0.25(4)'),
        ('0.25(3)', '0.25'),
        ('0.25(3)', '0.25(0)'),
        ('2.50(5)', '2.51(5)'),
        ('0.125(4)', '0.126(4)'),
        ('abscor1', 'abscor2'),
        ('s 2.50', 'other 2.50'),
        ('_instrument.type diffractometer\n', ''),
        ('_absorption.type empirical\n', '_absorption.type empirical\n_absorption.extra 1\n'),
    ]:
        assert before in source, 'Written-field mutation must reach an actual authored operand'
        (actual / 'experiments/b.edi').write_text(source.replace(before, after))
        with pytest.raises(ValueError, match=r'web fit|written |science identity'):
            written.compare_written(actual, expected, fixture)
    (actual / 'experiments/b.edi').write_text(source)
    (actual / 'extra.bin').write_bytes(b'not ignored')
    with pytest.raises(ValueError, match='file inventory'):
        written.compare_written(actual, expected, fixture)


def test_extra_storage_duplicate_and_unknown_loop_shape_refuse(tmp_path):
    root = tmp_path / 'actual'
    write_project(root)
    path = root / 'experiments/b.edi'
    original = path.read_text()
    for suffix in [
        '_instrument.calib_twotheta_offset 0.25(3)\n',
        'loop_\n_absorption.abscor1\n0.125\n',
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\ns 2.5\n',
    ]:
        path.write_text(original + suffix)
        with pytest.raises((ValueError, RuntimeError)):
            written.extra_records(root)


def test_written_reference_requires_every_actual_capture_flag():
    required = dict.fromkeys(
        ('raw', 'ordinary_save', 'reopen', 'arrays', 'source_unchanged'), True
    )
    written.validate_capture_flags(required)
    for name in required:
        for value in (False, 0, 1, None, 'true'):
            with pytest.raises(ValueError, match='written reference is incomplete'):
                written.validate_capture_flags({**required, name: value})
        with pytest.raises(ValueError, match='written reference is incomplete'):
            written.validate_capture_flags({
                key: value for key, value in required.items() if key != name
            })
    with pytest.raises(ValueError, match='written reference is incomplete'):
        written.validate_capture_flags({**required, 'complete': True})


def test_reused_adp_column_never_selects_a_numerically_equal_wrong_site():
    args = list(copy.deepcopy(raw_control()))
    args[1]['labels'][0] = 'La.adp_iso'
    old = 'structure.cell.length_a'
    chosen, dependent = 'structure.atom_sites[La].adp_iso', 'structure.atom_sites[Ba].adp_iso'
    for field in ('values', 'uncertainty'):
        args[2][field][chosen] = args[2][field].pop(old)
    args[4][0] = {chosen, dependent}
    assert written.qualify_raw(*args)[0] == chosen, (
        'Reused covariance coordinates select the actual old-label owner; '
        'not an equal-valued alias'
    )
    for field in ('values', 'uncertainty'):
        args[2][field][dependent] = args[2][field].pop(chosen)
    with pytest.raises(ValueError, match='raw label differs'):
        written.qualify_raw(*args)


def test_optional_absorption_requires_the_original_declared_bank_and_field(tmp_path):
    source = tmp_path / 'source'
    write_project(source)
    names = {'structures/s.edi': 's', 'experiments/b.edi': 'b', 'experiments/c.edi': 'c'}
    banks = {'experiments/b.edi': ('b', ('s',)), 'experiments/c.edi': ('c', ('s',))}
    fixture = {
        'scientific': {
            'structures/s.edi': [['_cell.length_a', '3.25']],
            'experiments/b.edi': [['_peak.type', 'cwl-tch']],
            'experiments/c.edi': [['_peak.type', 'cwl-tch']],
        },
        'native_precision_bindings': [],
    }
    raw = {'labels': ['b.abscor1'], 'values': [0.125], 'covariance': [0.0009]}
    assert written.raw_candidates(fixture, raw, names, banks, source) == {
        0: {'experiments[b].absorption.abscor1'}
    }, 'The optional field must retain its original experiment bank and FIRST storage spelling'
    path = source / 'experiments/b.edi'
    text = path.read_text()
    for before, after in [
        ('_absorption.abscor1 0.125(4)\n', ''),
        ('abscor1', 'abscor2'),
        ('data_b', 'data_wrong'),
    ]:
        path.write_text(text.replace(before, after))
        if before == 'data_b':
            # The declarations must be independently read from this changed input,
            # never continue with a cached bank name after an owner rename.
            changed = {**names, 'experiments/b.edi': 'wrong'}
            with pytest.raises(ValueError, match='no declared fitted storage'):
                written.raw_candidates(fixture, raw, changed, banks, source)
        else:
            with pytest.raises(ValueError, match='optional absorption must exist'):
                written.raw_candidates(fixture, raw, names, banks, source)
    path.write_text(text)


def test_only_the_two_declared_headerless_records_get_observer_wrapping(tmp_path):
    project = tmp_path / 'project.edi'
    project.write_text('_edi.schema_version 3\n')
    before = project.read_bytes()
    assert written.document(project, 'project.edi').find_value('_edi.schema_version') == '3', (
        'The FIRST project record is headerless; observer parsing must preserve its schema token'
    )
    assert project.read_bytes() == before, 'Observer wrapping must not rewrite a saved project'
    analysis = tmp_path / 'analysis.edi'
    analysis.write_text('_fitting_mode.type single\n')
    assert (
        written.document(analysis, 'analysis/analysis.edi').find_value('_fitting_mode.type')
        == 'single'
    ), 'The existing headerless analysis wrapper must retain its original declaration'
    for name in ('structures/unowned.edi', 'experiments/unowned.edi', 'other.edi'):
        with pytest.raises((RuntimeError, ValueError)):
            written.document(project, name)


def test_native_value_iterable_collection_captures_named_banks_and_refuses_inventory_escape(
    tmp_path,
):
    class ValueIterable:
        def __init__(self, rows):
            self.rows = rows

        def __iter__(self):
            return iter(self.rows.values())

        def keys(self):
            return iter(self.rows.keys())

        def items(self):
            return iter(self.rows.items())

    data = SimpleNamespace(
        intensity_meas=[2.25, 4.5],
        intensity_meas_su=[0.5, 0.75],
        intensity_calc=[2.0, 4.0],
        intensity_bkg=[0.25, 0.5],
        calc_status=['incl', 'excl'],
        axis=lambda: [10.5, 11.5],
    )
    rows = {'bank-a': SimpleNamespace(data=data), 'bank-b': SimpleNamespace(data=data)}
    collection = ValueIterable(rows)
    assert all(actual is rows[name] for actual, name in zip(collection, rows, strict=True)), (
        'The native keyed collection iterates real fixture values, never dictionary keys'
    )
    assert list(collection.keys()) == ['bank-a', 'bank-b'], (
        'Only the declared keys() protocol supplies the bank inventory'
    )
    banks = {'experiments/a.edi': ('bank-a', ('s',)), 'experiments/b.edi': ('bank-b', ('s',))}
    owner = SimpleNamespace(experiments=collection)
    captured = written.capture_arrays(owner, tmp_path, banks, 'positive.npz')
    wanted = {name + '__' + field for name in rows for field in (*written.ARRAY_FIELDS, 'axis')}
    assert captured.keys() == wanted, 'The complete named public array population must be captured'
    with np.load(tmp_path / 'positive.npz', allow_pickle=False) as saved:
        assert set(saved.files) == wanted, 'The actual NPZ must retain every named array'
        for name in rows:
            assert np.array_equal(
                saved[name + '__intensity_meas'], np.array(data.intensity_meas)
            ), 'Value iteration must not replace the measured data or its bank identity'
            assert np.array_equal(saved[name + '__calc_status'], np.array(data.calc_status)), (
                'The captured bank must preserve its actual inclusion/exclusion statuses'
            )
    for label, changed in [
        ('missing', {'bank-a': rows['bank-a']}),
        ('extra', {**rows, 'bank-c': SimpleNamespace(data=data)}),
    ]:
        owner.experiments = ValueIterable(changed)
        target = label + '.npz'
        with pytest.raises(
            ValueError, match='live native arrays changed experiment bank inventory'
        ):
            written.capture_arrays(owner, tmp_path, banks, target)
        assert not (tmp_path / target).exists(), (
            'An incomplete or extra bank inventory must refuse before writing any capture'
        )
