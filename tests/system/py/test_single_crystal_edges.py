"""Single-crystal model boundaries, checked by independent algebra and retention laws."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.single_crystal_edges.inputs import (
    COEFFICIENTS,
    HKLS,
    KINDS,
    bare,
    powder,
    project,
    relations,
    sphere,
    weighted,
)
from tests.fixtures.single_crystal_edges.observe import numbers, observe, params, snapshot
from tests.integration.py.test_single_crystal import engine

ROOT = Path(__file__).resolve().parents[3]
BACKEND = 'edi'
SLOTS = (
    'domain_radius',
    'mosaic_spread',
    'crystal_radius',
    'coefficient',
    *('coefficient_' + c for c in COEFFICIENTS),
)
ACTIVE = {
    'none': (),
    'larson-isotropic': ('coefficient',),
    'larson-anisotropic': tuple('coefficient_' + c for c in COEFFICIENTS),
    'becker-coppens-type-1': ('mosaic_spread',),
    'becker-coppens-type-2': ('domain_radius',),
    'becker-coppens-mixed': ('domain_radius', 'mosaic_spread'),
}
SHAPES = [
    (tof, field, n, entry, operation)
    for tof in [False, True]
    for field in (
        'index_h',
        'index_k',
        'index_l',
        'intensity_meas',
        'intensity_meas_su',
        'wavelength',
    )
    if tof or field != 'wavelength'
    for n in (0, 2, 4)
    for entry in (('owned', 'setter') if BACKEND == 'crysta' else ('owned',))
    for operation in ('calc', 'fit', 'save')
]


@pytest.fixture(scope='module')
def native():
    if BACKEND == 'edi':
        directory = Path(engine()._edi.__file__).resolve().parents[2]
    else:
        directory = (ROOT / 'build/crysta').resolve().parent
    executable = (
        directory
        / ('single_crystal_edges' if BACKEND == 'edi' else 'tests/fixtures/single_crystal_edges')
        / 'single_crystal_edge_probe'
    )
    assert executable.is_file(), (
        'The public-model observer must be prepared by the normal native build '
        'before acceptance tests'
    )
    identity = subprocess.check_output([str(executable), '--identity'], text=True).strip()
    source = ROOT / 'tests/fixtures/single_crystal_edges/probe.cpp'
    assert identity == hashlib.sha256(source.read_bytes()).hexdigest(), (
        'The prepared observer must match the exact committed observation source'
    )
    return executable


def refused(result, *names):
    assert not result['ok'], 'Unsupported model input must refuse before reading or solving it'
    error = result['error'].lower()
    assert any(name.lower() in error for name in names), (
        'Input refusal must name the affected category, field or physical limitation: ' + error
    )


@pytest.mark.parametrize(('tof', 'field', 'n', 'entry', 'operation'), SHAPES)
def test_reflection_shape_is_atomic_at_every_entry(
    native, tmp_path, tof, field, n, entry, operation
):
    root = project(tmp_path / 'model', tof=tof)
    result = observe(native, root, 'shape', field, n, operation, entry)
    refused(result, 'refl', 'miller', field, 'wavelength', 'column', 'intensity', 'sigma')
    assert snapshot(result, 'after:') == snapshot(result, 'before:'), (
        'Malformed reflection admission and compute refusal must preserve every '
        'prior input and parameter'
    )
    assert numbers(result, 'retained:calc:bank') == numbers(result, 'old:calc:bank'), (
        'Malformed reflection refusal must retain the previously published intensity buffer'
    )
    assert not (tmp_path / 'model-saved').exists(), (
        'Malformed reflection save refusal must not publish a partial destination'
    )


BOUND_CASES = [('lower', op) for op in ['apply', 'calc', 'fit', 'save']]
if BACKEND == 'crysta':
    BOUND_CASES += [('upper', op) for op in ['apply', 'calc', 'fit', 'save']]


@pytest.mark.parametrize(('edge', 'operation'), BOUND_CASES)
def test_finite_dependents_cross_bounds_with_warning(native, tmp_path, edge, operation):
    result = observe(native, project(tmp_path / 'model'), 'bound', edge, operation)
    assert result['ok'], (
        'Finite constrained dependents must be written even outside explicit bounds: '
        + result['error']
    )
    expected = 5.13 if edge == 'upper' else -0.13
    applied = params(result, 'saved:' if operation == 'save' else 'after:')
    assert applied['structure.atom_site.Ni.adp_iso'][0] == pytest.approx(expected, abs=1e-14), (
        'Finite range escape must keep the relation result, never clip or retain the old value'
    )
    assert 'warn' in result['notes'].lower() or 'outside' in result['notes'].lower(), (
        'A finite dependent outside its range must produce a visible warning'
    )
    if operation == 'save':
        assert snapshot(result, 'after:') == snapshot(result, 'before:'), (
            'Saving constrained values must retain the live model '
            'while applying its output snapshot'
        )
        assert params(result, 'saved:')['structure.atom_site.Ni.adp_iso'][0] == pytest.approx(
            expected, abs=1e-14
        ), 'Saved and reloaded finite dependents must retain the relation value outside the range'


@pytest.mark.parametrize('operation', ['apply', 'calc', 'fit', 'save'])
def test_nonfinite_relation_chain_never_partially_writes(native, tmp_path, operation):
    result = observe(native, project(tmp_path / 'model'), 'bound', 'nonfinite', operation)
    refused(result, 'finite', 'sqrt', 'constraint', 'relation', 'domain')
    assert snapshot(result, 'after:') == snapshot(result, 'before:'), (
        'A later nonfinite dependent must refuse before changing any earlier value, '
        'free flag or start value'
    )


LAYOUTS = {
    'leading': [('other', '19', False), ('structure', '2.3()', True)],
    'trailing': [('structure', '2.3()', True), ('other', '19', False)],
    'lone': [('structure', '2.3()', False)],
}


@pytest.mark.parametrize('layout', LAYOUTS)
def test_enabled_links_survive_roundtrip(native, tmp_path, layout):
    root = project(tmp_path / 'model', links=LAYOUTS[layout])
    result = observe(native, root, 'roundtrip')
    expected = [
        ['bank', key, enabled, float(scale.removesuffix('()'))]
        for key, scale, enabled in LAYOUTS[layout]
    ]
    loaded = [
        [bank, key, enabled == '1', float(scale)]
        for bank, key, enabled, scale in result['loaded:link']
    ]
    assert loaded == expected, (
        'Every loaded enabled flag and scale must equal the independently authored input rows'
    )
    assert result['saved:link'] == result['loaded:link'], (
        'Saving and reloading must preserve every enabled flag, linked identity and scale'
    )
    if layout == 'lone':
        refused(result, 'enabled', 'structure', 'link')


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('operation', ['calc', 'fit'])
def test_disabled_link_never_supplies_active_scale(native, tmp_path, layout, operation):
    result = observe(native, project(tmp_path / 'model', links=LAYOUTS[layout]), operation)
    if layout == 'lone' or not result['ok']:
        refused(result, 'enabled', 'structure', 'link')
        assert snapshot(result, 'after:') == snapshot(result, 'loaded:'), (
            'Unsupported linked layouts must refuse before changing any stored state'
        )
        return
    if operation == 'calc':
        assert numbers(result, 'calc:bank') == pytest.approx(
            [2.3 * bare(h) for h in HKLS], rel=2e-12
        ), 'Only the enabled structure scale may multiply its calculated intensities'
    else:
        assert params(result)['bank.linked_structure.structure.scale'][0] == pytest.approx(
            4.7, rel=2e-7
        ), 'Fit must solve the enabled scale from independent one-atom observations'
        assert params(result)['bank.linked_structure.other.scale'][0] == 19, (
            'A disabled scale must never enter the selected free set or receive a fitted write'
        )


INACTIVE = [(kind, slot) for kind in KINDS for slot in SLOTS if slot not in ACTIVE[kind]]


@pytest.mark.parametrize(('kind', 'slot'), INACTIVE)
def test_unsupported_free_slots_refuse_instead_of_zero_columns(native, tmp_path, kind, slot):
    # Start from a fully populated type, then use the raw public type token, preserving the mark.
    seed = (
        'larson-anisotropic'
        if slot.startswith('coefficient_')
        else ('larson-isotropic' if slot == 'coefficient' else 'becker-coppens-mixed')
    )
    root = project(tmp_path / 'model', kind=seed, links=[('structure', '2.3', True)])
    result = observe(native, root, 'mark', 'bank.extinction.' + slot, kind)
    refused(result, slot, 'inactive', 'unsupported', 'crystal radius', 'free')
    assert snapshot(result, 'after:') == snapshot(result, 'before:'), (
        'Unsupported free marks must refuse atomically before fitting or clearing the caller mark'
    )


@pytest.mark.parametrize(
    ('kind', 'slot'), [(kind, slot) for kind, slots in ACTIVE.items() for slot in slots]
)
def test_active_slot_is_the_only_solved_extinction_parameter(native, tmp_path, kind, slot):
    result = observe(
        native,
        project(tmp_path / 'model', kind=kind, free=slot, links=[('structure', '2.3', True)]),
        'fit',
    )
    assert result['ok'], (
        'An active differentiable extinction parameter must reach fitting: ' + result['error']
    )
    assert [row[0].rsplit('.', 1)[-1] for row in result['fitted']] == [slot], (
        'The selected free set must contain exactly the active marked slot and no '
        'inactive stored slots'
    )


def test_free_cw_wavelength_refuses_at_fit(native, tmp_path):
    result = observe(
        native,
        project(tmp_path / 'model', kind='becker-coppens-mixed'),
        'mark',
        'bank.instrument.setup_wavelength',
    )
    refused(result, 'wavelength')
    assert snapshot(result, 'after:') == snapshot(result, 'before:'), (
        'Unsupported free wavelength must refuse without changing parameter values or flags'
    )


def test_free_cw_wavelength_file_note_in_consumer(native, tmp_path):
    result = observe(native, project(tmp_path / 'model', wavelength='1.6()'), 'load')
    assert result['ok'], 'A supported CW file must load before free-state policy is applied'
    if BACKEND == 'edi':
        assert not params(result)['bank.instrument.setup_wavelength'][1], (
            'Consumer loading must fix the unsupported free CW wavelength'
        )
        assert 'wavelength' in result['notes'].lower(), (
            'Fixing a file-loaded free CW wavelength must emit a named load note'
        )


def test_constrained_internal_wavelength_cannot_bypass_free_policy(native, tmp_path):
    root = project(
        tmp_path / 'model',
        kind='becker-coppens-mixed',
        free='mosaic_spread',
        links=[('structure', '2.3', True)],
    )
    relations(
        root,
        {'g': 'bank.extinction.mosaic_spread', 'w': 'bank.instrument.setup_wavelength'},
        ['w = g / 58187.5'],
    )
    result = observe(native, root, 'fit')
    refused(result, 'wavelength', 'unsupported', 'dependent', 'constraint')


@pytest.mark.parametrize('weights', [(1, 9), (9, 1), (1, 1)])
def test_joint_weights_move_a_genuinely_shared_coefficient(native, tmp_path, weights):
    root, coefficient, chi2 = weighted(tmp_path / 'model', weights)
    result = observe(native, root, 'fit')
    assert result['ok'], 'Joint weighted shared-coefficient fitting must run: ' + result['error']
    for bank in ('bank1', 'bank2'):
        assert params(result)[bank + '.extinction.coefficient'][0] == pytest.approx(
            coefficient, rel=3e-6
        ), (
            'Joint weights must select the independent weighted-mean optimum of one '
            'shared Larson coefficient'
        )
    assert numbers(result, 'chi2')[0] == pytest.approx(chi2, rel=2e-8, abs=1e-12), (
        'The objective must use dataset weight divided by observation variance for every row'
    )


EDITS = [
    ('becker-coppens-mixed', 'bank.linked_structure.structure.scale', '0.17'),
    ('becker-coppens-mixed', 'type', 'becker-coppens-type-2'),
    ('becker-coppens-mixed', 'distribution', 'lorentzian'),
]
EDITS += [
    ('becker-coppens-mixed', 'bank.extinction.' + s, '0.13')
    for s in ('domain_radius', 'mosaic_spread', 'crystal_radius')
]
EDITS += [('larson-isotropic', 'bank.extinction.coefficient', '0.13')]
EDITS += [('larson-anisotropic', 'bank.extinction.coefficient_' + s, '0.13') for s in COEFFICIENTS]


@pytest.mark.parametrize(('kind', 'slot', 'delta'), EDITS)
def test_each_intensity_input_stales_state_and_peek(native, tmp_path, kind, slot, delta):
    result = observe(native, project(tmp_path / 'model', kind=kind), 'fresh', slot, delta)
    assert result['ok'], 'A valid reflection edit must remain calculable: ' + result['error']
    assert result['state_before'] == [['1', '1']], (
        'Calculation must publish Current reflection state and peek'
    )
    assert result['state_after'] == [['2', '2']], (
        'Every scale or extinction input edit must expose Stale through state and '
        'peek before recomputation'
    )
    assert result['state_ensured'] == [['1', '1']], (
        'Ensuring calculated reflections must restore Current state'
    )


def test_free_metadata_does_not_stale_reflection_values(native, tmp_path):
    result = observe(
        native,
        project(tmp_path / 'model'),
        'fresh',
        'bank.linked_structure.structure.scale',
        'free',
    )
    assert result['ok'], 'A free flag edit must remain calculable'
    assert result['state_after'] == [['1', '1']], (
        'A free-flag edit alone must retain the narrower physical reflection dependency'
    )


FORBIDDEN = (
    '_peak.type',
    '_background.type',
    '_data.two_theta',
    '_excluded_region.start',
    '_absorption.type',
    '_preferred_orientation.structure_id',
)


@pytest.mark.parametrize('tag', FORBIDDEN)
@pytest.mark.parametrize('loop', [False, True])
def test_powder_categories_are_named_refusals(native, tmp_path, tag, loop):
    extra = f'loop_\n{tag}\n1\n' if loop else f'{tag} 1\n'
    root = project(tmp_path / 'model', extra=extra)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*.edi')}
    result = observe(native, root, 'load')
    refused(result, tag.split('.')[0])
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob('*.edi')} == before, (
        'Rejected powder categories must leave every source project byte intact'
    )


def test_tof_instrument_admission_is_explicit(native, tmp_path):
    result = observe(
        native,
        project(tmp_path / 'model', tof=True, extra='_instrument.calib_d_to_tof_linear 2500\n'),
        'calc',
    )
    if BACKEND == 'crysta':
        refused(result, 'instrument')
        return
    assert result['ok'], (
        'Obsolete TOF instrument compatibility must retain calculation from row wavelengths'
    )
    assert 'instrument' in result['notes'].lower(), (
        'Ignoring obsolete TOF instrument input must emit its load note'
    )
    assert numbers(result, 'calc:bank') == pytest.approx(
        [2.3 * bare(h) for h in HKLS], rel=2e-12
    ), 'Obsolete TOF instrument fields must not replace per-reflection wavelengths or scale'


@pytest.mark.parametrize('tof', [False, True])
@pytest.mark.parametrize('distribution', ['gaussian', 'lorentzian'])
@pytest.mark.parametrize('created', ['file', 'model'])
def test_type_two_distribution_retains_closed_form_across_roundtrip(
    native, tmp_path, tof, distribution, created
):
    root = project(
        tmp_path / 'model',
        tof=tof,
        kind='becker-coppens-type-2',
        distribution=distribution if created == 'file' else None,
    )
    result = observe(
        native,
        root,
        'roundtrip' if created == 'file' else 'distribution',
        *([distribution] if created == 'model' else []),
    )
    assert result['ok'], (
        'Both type-II distributions must be admitted consistently: ' + result['error']
    )
    expected = [
        2.3 * bare(h) * sphere(h, 1.2 + 0.2 * i if tof else 1.6, distribution)
        for i, h in enumerate(HKLS)
    ]
    assert numbers(result, 'saved:calc:bank') == pytest.approx(expected, rel=2e-12, abs=1e-13), (
        'Type-II save/reload must retain the chosen distribution and independent '
        'sphere intensities'
    )
    if created == 'model':
        assert numbers(result, 'calc:bank') == pytest.approx(expected, rel=2e-12, abs=1e-13), (
            'A programmatically selected type-II distribution must use the same '
            'independent closed form'
        )


def test_powder_retains_its_narrower_reflection_dependency(native, tmp_path):
    result = observe(
        native,
        powder(tmp_path / 'model'),
        'fresh',
        'bank.linked_structure.structure.scale',
        '0.17',
    )
    assert result['ok'], 'A powder scale edit must remain calculable: ' + result['error']
    expected = [['1', '1']] if BACKEND == 'crysta' else [['2', '2']]
    assert result['state_after'] == expected, (
        'Powder raw reflection state must ignore scale; '
        'the consumer aggregate includes its changed pattern'
    )


@pytest.mark.parametrize('tof', [False, True])
@pytest.mark.parametrize('distribution', ['gaussian', 'lorentzian'])
def test_python_created_type_two_distribution_survives_save(tmp_path, tof, distribution):
    root = project(tmp_path / 'model', tof=tof, kind='becker-coppens-type-2', distribution=None)
    model = engine().Project.load(root)
    model.experiments[0].extinction.mosaic_distribution = distribution
    model.analysis.calculate()
    expected = [
        2.3 * bare(h) * sphere(h, 1.2 + 0.2 * i if tof else 1.6, distribution)
        for i, h in enumerate(HKLS)
    ]
    assert list(model.experiments[0].refln.intensity_calc) == pytest.approx(expected, rel=2e-12), (
        'The Python type-II distribution setter must select the independent sphere formula'
    )
    destination = tmp_path / 'saved'
    model.save_as(destination)
    restored = engine().Project.load(destination)
    restored.analysis.calculate()
    assert list(restored.experiments[0].refln.intensity_calc) == pytest.approx(
        expected, rel=2e-12
    ), 'A Python-created type-II distribution must retain calculated values after save and reload'


def test_python_free_cw_wavelength_cannot_be_silently_omitted(tmp_path):
    model = engine().Project.load(project(tmp_path / 'model', kind='becker-coppens-mixed'))
    model.experiments[0].instrument.setup_wavelength.free = True
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)wavelength'):
        model.analysis.fit()


def test_python_type_transition_does_not_solve_an_inactive_slot(tmp_path):
    model = engine().Project.load(project(tmp_path / 'model', kind='becker-coppens-mixed'))
    extinction = model.experiments[0].extinction
    extinction.domain_radius.free = True
    extinction.type = 'none'
    if BACKEND == 'edi':
        assert extinction.domain_radius is None, (
            'The typed consumer selector must remove inactive slots'
        )
    else:
        with pytest.raises((ValueError, RuntimeError), match=r'(?i)inactive|extinction|free'):
            model.analysis.fit()
