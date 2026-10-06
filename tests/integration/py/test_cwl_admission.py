"""Whole declaration and mutation admission for every CW profile slot group."""

import itertools

import edi as engine
import numpy as np
import pytest

from tests.fixtures.cwl_family import admission, profiles


def load_route(route, text, path, holder):
    path.write_text(text)
    if route == 'text':
        return engine.ExperimentFactory.from_cif_str(text)
    if route == 'file':
        return engine.ExperimentFactory.from_cif_path(path)
    result = holder.experiments.add_from_cif_str(text)
    return holder.experiments[-1] if result is None else result


@pytest.mark.parametrize(('token', 'group', 'field'), admission.DECLARATIONS)
@pytest.mark.parametrize(
    ('shape', 'route'),
    [
        (shape, route)
        for shape in [
            'edi-scalar',
            'edi-loop',
            'edi-mixed',
            'cif-scalar',
            'cif-loop',
            'cif-mixed',
            'cif-dot-scalar',
            'cif-dot-loop',
            'cif-dot-mixed',
        ]
        for route in (
            ['project', 'text', 'file', 'collection']
            if shape.startswith('edi')
            else ['text', 'file', 'collection']
        )
    ],
)
def test_every_foreign_slot_declaration_shape_is_refused(
    tmp_path, token, group, field, shape, route
):
    directory = profiles.write_project(tmp_path / 'input', token)
    path = directory / 'experiments/bank.edi'
    original = path.read_text()
    text = admission.classic(original) if shape.startswith('cif') else original
    holder = engine.Project.load(directory)
    if route == 'project':
        control = engine.Project.load(directory)
    else:
        # Give collection imports a distinct datablock identity before testing admission.
        if route == 'collection':
            text = text.replace('data_bank\n', 'data_probe\n', 1)
        control = load_route(route, text, path, holder)
    assert control is not None, 'Every declaration refusal must have a passing valid load control'
    assert field in admission.GROUPS[group][0], (
        'Every independent declaration case names its group'
    )
    damaged = text + admission.declaration(
        field, shape, classic_field=shape.startswith('cif') and '-dot-' not in shape
    )
    # A fresh holder prevents duplicate-key errors from masquerading as admission.
    fresh_dir = profiles.write_project(tmp_path / ('holder-' + field), token)
    fresh = engine.Project.load(fresh_dir)
    if route == 'project':
        path.write_text(damaged)
        call, arguments = engine.Project.load, (directory,)
    else:
        call, arguments = load_route, (route, damaged, path, fresh)
    with pytest.raises((ValueError, RuntimeError)) as failure:
        call(*arguments)
    assert field in str(failure.value), (
        'Foreign declaration refusal must identify the supplied slot'
    )


@pytest.mark.parametrize('token', profiles.TOKENS[2:4])
@pytest.mark.parametrize('spelling', ['classic', 'dot'])
@pytest.mark.parametrize('route', ['text', 'file', 'collection'])
def test_cif_nonzero_mixing_survives_import_without_default_substitution(
    tmp_path, token, spelling, route
):
    directory = profiles.write_project(tmp_path / 'input', token)
    path = directory / 'experiments/bank.edi'
    text = admission.classic(path.read_text()).replace('data_bank\n', 'data_probe\n', 1)
    prefix = '_easydiffraction_peak.' if spelling == 'classic' else '_peak.'
    text += f'\n{prefix}mixing_eta_0 .23\n{prefix}mixing_eta_1 .0031\n'
    if token == profiles.TOKENS[3]:
        text += f'{prefix}asym_beba_limit 160\n'
    project = engine.Project.load(directory)
    experiment = load_route(route, text, path, project)
    if experiment is None:
        experiment = project.experiments[-1]
    intercept, slope = profiles.mixing_parameters(experiment.peak)
    np.testing.assert_array_equal(
        [intercept.value, slope.value],
        [0.23, 0.0031],
        err_msg='CIF import retains both supplied nonzero mixing coefficients exactly',
    )
    if token == profiles.TOKENS[3]:
        assert experiment.peak.asym_beba_limit.value == 160, (
            'CIF import retains the owner PCR limit value instead of substituting its default'
        )
        assert not experiment.peak.asym_beba_limit.free, (
            'CIF import keeps the independently classified limit setting fixed'
        )


@pytest.mark.parametrize(('source', 'target'), list(itertools.permutations(profiles.TOKENS, 2)))
def test_every_directed_cw_switch_reshapes_slots_and_roundtrips(tmp_path, source, target):
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', source))
    old_peak = project.experiments[0].peak
    for field in admission.owned_fields(source):
        parameter = getattr(old_peak, field)
        parameter.value = (
            160 if field == 'asym_beba_limit' else (0.0031 if field.endswith('_1') else 0.031)
        )
        if field not in admission.SETTINGS:
            parameter.uncertainty = 0.001
            parameter.free = True
        else:
            parameter.free = False
    old_peak.type = target
    peak = project.experiments[0].peak
    expected = set(admission.owned_fields(target))
    for field in admission.FIELDS:
        assert hasattr(peak, field) == (field in expected), (
            'A directed CW switch must expose exactly the target profile slot groups'
        )
    for field in expected:
        parameter = getattr(peak, field)
        parameter.value = (
            160 if field == 'asym_beba_limit' else (0.0031 if field.endswith('_1') else 0.031)
        )
        if field not in admission.SETTINGS:
            parameter.uncertainty = 0.001
            parameter.free = True
        else:
            parameter.free = False
    project.analysis.calculate()
    before = np.asarray(project.experiments[0].data.intensity_calc).copy()
    assert np.isfinite(before).all(), 'Every switched CW profile calculates finite samples'
    assert np.any(before > 0), 'Every switched CW profile calculates a nonzero pattern'
    project.save_as(tmp_path / 'saved')
    record = (tmp_path / 'saved/experiments/bank.edi').read_text()
    for field in admission.FIELDS:
        assert (
            ('_peak.' + field + ' ') in record
            if field in expected
            else ('_peak.' + field + ' ') not in record
        ), 'Saving a switched profile must preserve exactly its target slot group population'
    reopened = engine.Project.load(tmp_path / 'saved')
    reopened.analysis.calculate()
    np.testing.assert_array_equal(
        before,
        reopened.experiments[0].data.intensity_calc,
        err_msg='Switch save/reload must retain every calculated sample',
    )
    for field in expected:
        loaded = getattr(reopened.experiments[0].peak, field)
        assert loaded.value == getattr(peak, field).value, (
            'Switch save/reload retains every supplied target value including the fixed limit'
        )
        if field not in admission.SETTINGS:
            assert loaded.uncertainty == getattr(peak, field).uncertainty, (
                'Switch save/reload retains each supplied coefficient uncertainty'
            )
        assert loaded.free == (field not in admission.SETTINGS), (
            'Switch save/reload retains coefficient free-state '
            'and the independent fixed-limit contract'
        )


@pytest.mark.parametrize('source', profiles.TOKENS[2:])
@pytest.mark.parametrize(
    'escape', ['old-view', 'cached-value', 'cached-free', 'cached-uncertainty']
)
def test_held_old_view_cannot_reengage_a_removed_slot(tmp_path, source, escape):
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', source))
    peak = project.experiments[0].peak
    field = admission.owned_fields(source)[0]
    parameter = getattr(peak, field)
    parameter.value = 0.23
    previous = parameter.value
    peak.type = profiles.TOKENS[0]
    assert not parameter.is_attached(), (
        'A removed optional peak slot reports the detached lifetime of ADR-0012'
    )
    assert parameter.value == previous, (
        'A detached optional peak handle retains its last readable value'
    )

    def escape_write():
        if escape == 'old-view':
            getattr(peak, field).value = 0.37
        elif escape == 'cached-value':
            parameter.value = 0.37
        elif escape == 'cached-free':
            parameter.free = True
        else:
            parameter.uncertainty = 0.001

    with pytest.raises((ValueError, RuntimeError, AttributeError)):
        escape_write()
    assert not hasattr(project.experiments[0].peak, field), (
        'A retained view must not restore a foreign slot to the active profile'
    )
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    assert '_peak.' + field not in (tmp_path / 'saved/experiments/bank.edi').read_text(), (
        'The adapter save must never discard a slot silently recreated by a retained view'
    )


def test_wrong_concrete_peak_view_cannot_add_foreign_slots(tmp_path):
    control = engine.Project.load(profiles.write_project(tmp_path / 'control', profiles.TOKENS[4]))
    control_view = engine.CwlTchPseudoVoigt(control.experiments[0])
    assert control_view.broad_lorentz_x.value == pytest.approx(0), (
        'The concrete-view escape must first prove its valid constructor and slot access'
    )
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', profiles.TOKENS[0]))
    with pytest.raises((ValueError, RuntimeError, AttributeError, TypeError)):
        engine.CwlTchPseudoVoigt(project.experiments[0]).broad_lorentz_x.value = 0.37
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    assert '_peak.broad_lorentz_x' not in (tmp_path / 'saved/experiments/bank.edi').read_text(), (
        'A wrong concrete view must not create state the adapter silently discards'
    )


@pytest.mark.parametrize(
    ('token', 'field', 'fallback'),
    [
        (token, field, 0.0)
        for token in profiles.TOKENS[2:4]
        for field in ('mixing_eta_0', 'mixing_eta_1')
    ]
    + [
        (profiles.TOKENS[3], field, 0.0)
        for field in ('asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1')
    ]
    + [(profiles.TOKENS[3], 'asym_beba_limit', 180.0)]
    + [(profiles.TOKENS[5], field, 0.0) for field in ('asym_fcj_1', 'asym_fcj_2')],
)
def test_optional_profile_cell_clear_uses_declared_default(tmp_path, token, field, fallback):
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', token))
    peak = project.experiments[0].peak
    held = getattr(peak, field)
    held.value = 160 if field == 'asym_beba_limit' else 0.031
    previous = held.value
    setattr(peak, field, None)
    assert not held.is_attached(), 'Clearing an optional profile cell detaches its old handle'
    assert held.value == previous, (
        'A cleared optional profile handle retains its last readable value'
    )
    with pytest.raises((ValueError, RuntimeError)):
        held.value = previous + 0.001
    assert getattr(peak, field) is None, 'An absent optional profile cell remains visibly absent'
    width = peak.broad_gauss_w
    width.free = True
    assert any(item.value == width.value for item in project.free_parameters), (
        'Free selection admits optional absence and retains an actual free width coefficient'
    )
    project.analysis.calculate()
    actual = np.asarray(project.experiments[0].data.intensity_calc).copy()
    project.save_as(tmp_path / 'saved')
    restored = engine.Project.load(tmp_path / 'saved')
    restored.analysis.calculate()
    np.testing.assert_array_equal(
        actual,
        restored.experiments[0].data.intensity_calc,
        err_msg='Optional defaults retain calculation bytes across save and reload',
    )
    assert getattr(restored.experiments[0].peak, field).value == fallback, (
        'Save and reload realize the independently declared default for the absent optional slot'
    )


@pytest.mark.parametrize('source', profiles.TOKENS)
def test_cleared_cw_selector_conforms_to_the_default_tch_family(tmp_path, source):
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', source))
    old = project.experiments[0].peak
    old.type = None
    peak = project.experiments[0].peak
    assert isinstance(peak, engine.CwlTchPseudoVoigt), (
        'A cleared CW selector resolves to the concrete CW TCH default view'
    )
    assert peak.broad_lorentz_x is not None and peak.broad_lorentz_y is not None, (
        'Clearing any CW selector conforms the required default TCH width block'
    )
    for field in set(admission.FIELDS) - set(admission.owned_fields(profiles.TOKENS[4])):
        assert not hasattr(peak, field), (
            'Clearing a selector removes every foreign optional profile slot'
        )
    peak.broad_lorentz_x.value = 0.023
    peak.broad_lorentz_y.value = 0.047
    peak.broad_lorentz_x.free = True
    assert project.free_parameters, 'The default family keeps its actual free TCH coefficient'
    project.analysis.calculate()
    before = np.asarray(project.experiments[0].data.intensity_calc).copy()
    project.save_as(tmp_path / 'saved')
    restored = engine.Project.load(tmp_path / 'saved')
    assert isinstance(restored.experiments[0].peak, engine.CwlTchPseudoVoigt), (
        'A cleared CW selector saves and reloads as the same effective default family'
    )
    restored.analysis.calculate()
    np.testing.assert_array_equal(
        before,
        restored.experiments[0].data.intensity_calc,
        err_msg='Selector clearing retains default-family samples across save and reload',
    )


def test_fixed_beba_limit_flag_cannot_create_a_binding_fit_parameter(tmp_path):
    project = engine.Project.load(
        profiles.write_project(
            tmp_path / 'input',
            profiles.TOKENS[3],
            extra='_peak.asym_beba_limit 160\n_peak.asym_beba_a0 .031\n',
        )
    )
    peak = project.experiments[0].peak
    limit = peak.asym_beba_limit
    refusal = None
    try:
        limit.free = True
    except (ValueError, RuntimeError) as error:
        refusal = str(error).lower()
    if refusal is not None:
        assert 'fixed' in refusal or 'limit' in refusal, (
            'A fixed-setting mutation refusal must identify the rejected contract'
        )
    peak.asym_beba_a0.free = True
    free = list(project.free_parameters)
    assert all(item.value != 160 for item in free), (
        'Bindings never advertise the fixed nondefault BeBa limit as a fitted coefficient'
    )
    assert any(item.value == 0.031 for item in free), (
        'Fixed-limit admission preserves the actual supplied free asymmetry coefficient'
    )
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    restored = engine.Project.load(tmp_path / 'saved')
    assert restored.experiments[0].peak.asym_beba_limit.value == 160, (
        'A fixed setting keeps its supplied nondefault value across persistence'
    )
    assert not restored.experiments[0].peak.asym_beba_limit.free, (
        'A setting never changes from fitted at admission to silently fixed only after save'
    )
