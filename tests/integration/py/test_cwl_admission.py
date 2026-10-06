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
    peak.type = profiles.TOKENS[0]

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
