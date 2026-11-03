"""Escape controls for the independent Save observer, not production Save substitutes."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as Record

import pytest

from tests.fixtures.project_save.completion import (
    CELL,
    OPTIONAL_XRAY,
    TENSOR,
    apply_declared,
    coordinates,
    declared_relations,
    fixed_declaration,
    fixed_values,
    model_inputs,
    setting,
    tree,
)
from tests.fixtures.project_save.reference import (
    optional_written,
    require_optional_tokens,
    require_saved_parameters,
    saved_parameters,
    saved_triplet,
    tensor_readback,
)


def parameter(value, su=None, *, free=False):
    return Record(value=value, uncertainty=su, free=free, start_value=None)


def model(*, tensor=False):
    cell = Record(**dict(zip(CELL, map(parameter, (5, 6, 7, 90, 90, 90)), strict=True)))
    site = Record(
        id='A',
        type_symbol='Si',
        adp_type='Uani' if tensor else 'Uiso',
        wyckoff_letter='a',
        fract_x=parameter(0.17),
        fract_y=parameter(0.23),
        fract_z=parameter(0.31),
        occupancy=parameter(1),
        adp_iso=parameter(0.02),
    )
    tensors = (
        [
            Record(
                id='A',
                **{
                    'adp_' + key: parameter(value)
                    for key, value in zip(TENSOR, (0.01, 0.02, 0.03, 0, 0, 0), strict=True)
                },
            )
        ]
        if tensor
        else []
    )
    structure = Record(
        name='sample',
        cell=cell,
        atom_sites=[site],
        atom_site_aniso=tensors,
        space_group=Record(name_h_m='P 1', coord_system_code=''),
    )
    parameters = list(vars(cell).values()) + [
        site.fract_x,
        site.fract_y,
        site.fract_z,
        site.occupancy,
        site.adp_iso,
    ]
    if tensor:
        parameters += [getattr(tensors[0], 'adp_' + key) for key in TENSOR]
    return Record(
        structures=[structure],
        experiments=[],
        parameters=parameters,
        analysis=Record(aliases=[], constraints=[]),
        metadata=Record(path='unused'),
    )


def publish(subject, reference, phase):
    for item, (value, su, free) in zip(subject.parameters, reference[0][phase], strict=True):
        item.value, item.uncertainty, item.free = value, su, free


@pytest.mark.parametrize('kind', ['Uani', 'Bani', 'beta'])
def test_tensor_zero_is_typed_and_keeps_nonzero_free_and_present_su(kind):
    subject = model(tensor=True)
    subject.structures[0].atom_sites[0].adp_type = kind
    _, slots, _, _, _ = model_inputs(subject)
    values = [(p.value, 0.0, p.free) for p in subject.parameters]
    indices = [slots['sample.atom_site_aniso.A.adp_' + key] for key in TENSOR]
    values[indices[4]] = (0.0, 0.0, True)
    values[indices[5]] = (0.0, 0.001, False)
    tensor_readback(subject, values, slots)
    assert values[indices[0]] == (0.01, 0.0, False), (
        'Required: tensor zero is typed and keeps nonzero free and present su.'
    )
    assert values[indices[3]] == (0.0, None, False), (
        'Required: tensor zero is typed and keeps nonzero free and present su.'
    )
    assert values[indices[4]] == (0.0, 0.0, True), (
        'Required: tensor zero is typed and keeps nonzero free and present su.'
    )
    assert values[indices[5]] == (0.0, 0.001, False), (
        'Required: tensor zero is typed and keeps nonzero free and present su.'
    )
    assert saved_triplet(0, None, False) == (0.0, 0.0, False), (
        'Required: tensor zero is typed and keeps nonzero free and present su.'
    )


@pytest.mark.parametrize('mutation', ['component', 'kind', 'site', 'owner'])
def test_tensor_identity_and_complete_population_cannot_be_relabelled(mutation):
    subject = model(tensor=True)
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    if mutation == 'component':
        subject.parameters[-1].uncertainty = 0.0
    elif mutation == 'kind':
        subject.structures[0].atom_sites[0].adp_type = 'Bani'
    elif mutation == 'site':
        subject.structures[0].atom_sites[0].id = 'other'
    else:
        subject.structures[0].name = 'other'
    with pytest.raises(AssertionError):
        require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')


@pytest.mark.parametrize('field', OPTIONAL_XRAY)
@pytest.mark.parametrize(
    ('prior', 'fit_start', 'present', 'written'),
    [
        ((0, None, False), False, False, (0, None, False)),
        ((0, 0, False), False, True, (0, 0, False)),
        ((0, None, True), False, True, (0, None, True)),
        ((0, 0, True), False, True, (0, 0, True)),
        ((1, None, False), False, True, (1, 0, False)),
        ((0, None, False), True, True, (0, 0, False)),
    ],
)
def test_optional_omission_is_distinct_from_a_written_fixed_or_free_zero(
    field,
    prior,
    fit_start,
    present,
    written,
):
    path = 'experiment.instrument.' + field
    values = [written]
    records = optional_written(
        [(path, 'experiment', field, fit_start)],
        values,
        {'slots': {path: 0}, 'completed_input': [prior]},
        {},
    )
    assert records[0][2] is present, (
        'Required: optional omission is distinct from a written fixed or free zero.'
    )
    assert values[0] == (written if present else (0, None, False)), (
        'Required: optional omission is distinct from a written fixed or free zero.'
    )
    assert records[0][3] == (
        written[0],
        written[1] if written[2] else None,
        written[2],
    ), 'Required: optional omission is distinct from a written fixed or free zero.'


@pytest.mark.parametrize('field', OPTIONAL_XRAY)
def test_optional_file_presence_and_syntax_are_observed_independently(tmp_path, field):
    folder = tmp_path / 'experiments'
    folder.mkdir()
    file = folder / 'experiment.edi'
    subject = Record(metadata=Record(path=tmp_path))
    file.write_text('data_experiment\n_instrument.' + field + ' 0\n')
    present = [('experiment', field, True, (0.0, None, False))]
    require_optional_tokens(subject, present)
    with pytest.raises(AssertionError):
        require_optional_tokens(subject, [('experiment', field, False, (0, None, False))])
    for token in ('0()', '0(0)', '1'):
        file.write_text('data_experiment\n_instrument.' + field + ' ' + token + '\n')
        with pytest.raises(AssertionError):
            require_optional_tokens(subject, present)
    file.write_text('data_experiment\n')
    with pytest.raises(AssertionError):
        require_optional_tokens(subject, present)
    require_optional_tokens(subject, [('experiment', field, False, (0, None, False))])


@pytest.mark.parametrize(
    'family',
    [
        ('CONSTANT_WAVELENGTH', 'XRAY'),
        ('CONSTANT_WAVELENGTH', 'NEUTRON'),
        ('TIME_OF_FLIGHT', 'NEUTRON'),
    ],
)
def test_optional_slots_do_not_cross_the_declared_experiment_family(family):
    subject = model()
    entries = {field: parameter(0) for field in OPTIONAL_XRAY}
    subject.parameters += list(entries.values())
    subject.experiments = [
        Record(
            name='experiment',
            linked_structures=[],
            extinction=None,
            instrument=Record(**entries),
            experiment_type=Record(
                beam_mode=Record(name=family[0]), radiation_probe=Record(name=family[1])
            ),
        )
    ]
    _, _, _, optional, _ = model_inputs(subject)
    assert len(optional) == (
        len(OPTIONAL_XRAY) if family == ('CONSTANT_WAVELENGTH', 'XRAY') else 0
    ), 'Required: optional slots do not cross the declared experiment family.'


def constrained_model():
    subject = model()
    subject.structures[0].atom_sites[0].fract_x.value = 0.91234567
    subject.structures[0].atom_sites[0].occupancy.value = 1 - 0.91234567
    subject.analysis.aliases = [
        Record(id='leader', parameter_unique_name='sample.atom_site.A.fract_x'),
        Record(id='dependent', parameter_unique_name='sample.atom_site.A.occupancy'),
    ]
    subject.analysis.constraints = [
        Record(id='complement', expression='dependent=1-leader', enabled=True)
    ]
    return subject


def test_declared_complement_has_distinct_loaded_and_completed_boundaries():
    subject = constrained_model()
    reference = saved_parameters(subject, 'iucr_99')
    assert reference[0]['first_written'][9] == (0.0876543, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['first_loaded'][9] == (0.0876543, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['adopted'][9] == (1 - 0.912346, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['final_written'][9] == (0.087654, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['loaded'][9] == (0.087654, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['parameter_rewrite_required'] is True, (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['completed'][9] == (1 - 0.912346, 0.0, False), (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    assert reference[0]['loaded'][9] != reference[0]['completed'][9], (
        'Required: declared complement has distinct loaded and completed boundaries.'
    )
    for phase in ('loaded', 'completed'):
        publish(subject, reference, phase)
        require_saved_parameters(subject.parameters, reference, model=subject, phase=phase)
        other = 'loaded' if phase == 'completed' else 'completed'
        with pytest.raises(AssertionError):
            require_saved_parameters(subject.parameters, reference, model=subject, phase=other)
    with pytest.raises(AssertionError):
        require_saved_parameters(subject.parameters, reference, model=subject, phase='guess')


def test_unchanged_parameter_adoption_has_one_file_projection_for_either_calculation_path():
    subject = model()
    for item in subject.parameters:
        item.uncertainty = 0.0
    reference = saved_parameters(subject, 'iucr_99')
    stages = reference[0]
    assert stages['parameter_rewrite_required'] is False, (
        'Required: unchanged parameter adoption has one file projection for '
        'either calculation path.'
    )
    assert stages['first_written'] == stages['final_written'] == stages['loaded'], (
        'Required: unchanged parameter adoption has one file projection for '
        'either calculation path.'
    )
    assert stages['adopted'] == stages['completed'], (
        'Required: unchanged parameter adoption has one file projection for '
        'either calculation path.'
    )


def test_optional_dependent_token_is_from_the_final_adopted_write(tmp_path):
    subject = constrained_model()
    optional = parameter(1 - 0.91234567)
    entries = {field: parameter(0) for field in OPTIONAL_XRAY}
    entries['setup_monochromator_twotheta'] = optional
    subject.parameters += list(entries.values())
    subject.experiments = [
        Record(
            name='experiment',
            linked_structures=[],
            extinction=None,
            instrument=Record(**entries),
            experiment_type=Record(
                beam_mode=Record(name='CONSTANT_WAVELENGTH'), radiation_probe=Record(name='XRAY')
            ),
        )
    ]
    subject.analysis.aliases.append(
        Record(
            id='instrument',
            parameter_unique_name='experiment.instrument.setup_monochromator_twotheta',
        )
    )
    subject.analysis.constraints.append(
        Record(
            id='instrument-complement',
            expression='instrument=dependent',
            enabled=True,
        )
    )
    reference = saved_parameters(subject, 'iucr_99')
    first = next(
        row for row in reference[0]['first_tokens'] if row[1] == 'setup_monochromator_twotheta'
    )
    final = next(row for row in reference[3] if row[1] == 'setup_monochromator_twotheta')
    assert first == (
        'experiment',
        'setup_monochromator_twotheta',
        True,
        (0.0876543, None, False),
    ), 'Required: optional dependent token is from the final adopted write.'
    assert final == (
        'experiment',
        'setup_monochromator_twotheta',
        True,
        (0.087654, None, False),
    ), 'Required: optional dependent token is from the final adopted write.'
    folder = tmp_path / 'experiments'
    folder.mkdir()
    file = folder / 'experiment.edi'
    subject.metadata.path = tmp_path
    file.write_text('data_experiment\n_instrument.setup_monochromator_twotheta 0.0876543\n')
    with pytest.raises(AssertionError):
        require_optional_tokens(subject, reference[3])
    file.write_text('data_experiment\n_instrument.setup_monochromator_twotheta 0.087654\n')
    require_optional_tokens(subject, reference[3])


@pytest.mark.parametrize('mutation', ['cycle', 'missing', 'target', 'unsupported'])
def test_declared_expression_refuses_missing_cycles_and_unproved_forms(mutation):
    values = [(0.2, None, False), (0.8, None, False)]
    indices = {'leader': 0, 'dependent': 1}
    expression = {
        'cycle': 'dependent',
        'missing': 'missing',
        'target': 'leader',
        'unsupported': 'abs(leader)',
    }[mutation]
    graph = {1: tree(expression)}
    if mutation == 'target':
        values[1] = (0.8, None, True)
    with pytest.raises(AssertionError):
        apply_declared(values, indices, graph)


def test_disabled_or_changed_declaration_is_not_an_alternative_success_path():
    subject = constrained_model()
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    for field, value in [('enabled', False), ('expression', 'leader=dependent')]:
        changed = deepcopy(subject)
        setattr(changed.analysis.constraints[0], field, value)
        with pytest.raises(AssertionError):
            require_saved_parameters(
                changed.parameters, reference, model=changed, phase='completed'
            )
    _, slots, lookups, _, identity = model_inputs(subject)
    indices, graph = declared_relations(identity, slots, lookups)
    values = [(p.value, p.uncertainty, p.free) for p in subject.parameters]
    with pytest.raises(AssertionError):
        apply_declared(values, indices, graph, blocked={indices['leader']})


def test_topological_declared_values_keep_su_and_refuse_duplicate_targets():
    values = [(0.2, 0.01, True), (0.8, 0.02, False), (0.8, None, False)]
    indices = {'leader': 0, 'dependent': 1, 'copy': 2}
    # Insertion order deliberately lists the consumer first.
    apply_declared(values, indices, {2: tree('dependent'), 1: tree('1-leader')})
    assert values == [
        (0.2, 0.01, True),
        (1 - 0.2, 0.02, False),
        (1 - 0.2, None, False),
    ], 'Required: topological declared values keep su and refuse duplicate targets.'
    subject = constrained_model()
    subject.analysis.constraints.append(
        Record(id='duplicate', expression='dependent=leader', enabled=True)
    )
    with pytest.raises(AssertionError):
        saved_parameters(subject, 'iucr_99')


def test_population_and_optional_constrained_bracket_cannot_disappear():
    subject = model()
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    with pytest.raises(AssertionError):
        require_saved_parameters(
            subject.parameters[:-1], reference, model=subject, phase='completed'
        )
    values = [(1.2, 0.02, False)]
    records = optional_written(
        [('experiment.instrument.setup_wavelength_2', 'experiment', 'setup_wavelength_2', False)],
        values,
        {
            'slots': {'experiment.instrument.setup_wavelength_2': 0},
            'completed_input': [(1.234, 0.021, False)],
        },
        {0: tree('leader')},
    )
    assert records == (('experiment', 'setup_wavelength_2', True, (1.2, 0.02, True)),), (
        'Required: population and optional constrained bracket cannot disappear.'
    )


def fixed_model():
    subject = model()
    structure = subject.structures[0]
    structure.space_group = Record(name_h_m='F d -3 m', coord_system_code='1')
    for axis in ('x', 'y', 'z'):
        getattr(structure.atom_sites[0], 'fract_' + axis).value = 0
    return subject


def test_fixed_representative_matches_independent_cctbx_and_the_full_declared_orbit():
    source = Path(__file__).parents[2] / 'fixtures/c34_t25_fullprof/wyckoff.json'
    cctbx = json.loads(source.read_text())
    # The existing independent fixture owns its shape and the literal representative.
    record = cctbx['groups']['Fd-3m:1']
    fixed = next(row for row in record['wyckoff'] if row['letter'] == 'a')
    representative, orbit = fixed_declaration((227, '1'), 'a')
    assert representative == coordinates(fixed['special_op'], {}), (
        'Required: fixed representative matches independent cctbx and the full declared orbit.'
    )
    assert len(orbit) == fixed['multiplicity'], (
        'Required: fixed representative matches independent cctbx and the full declared orbit.'
    )
    assert (0, 0, 0) in orbit, (
        'Required: fixed representative matches independent cctbx and the full declared orbit.'
    )
    subject = fixed_model()
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')
    subject.structures[0].atom_sites[0].fract_x.value = 0
    with pytest.raises(AssertionError):
        require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')


@pytest.mark.parametrize('mutation', ['orbit', 'translation', 'code', 'letter', 'id', 'owner'])
def test_fixed_setting_letter_owner_and_representative_are_not_interchangeable(mutation):
    subject = fixed_model()
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    structure, site = subject.structures[0], subject.structures[0].atom_sites[0]
    if mutation == 'orbit':
        site.fract_x.value = 0.17
    elif mutation == 'translation':
        site.fract_x.value += 1
    elif mutation == 'code':
        structure.space_group.coord_system_code = '2'
    elif mutation == 'letter':
        site.wyckoff_letter = 'b'
    elif mutation == 'id':
        site.id = 'B'
    else:
        structure.name = 'other'
    with pytest.raises(AssertionError):
        require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')


def test_unconstrained_coordinates_remain_exact_and_fixed_orbits_refuse_off_orbit_input():
    subject = model()
    _, slots, _, _, _ = model_inputs(subject)
    assert fixed_values(subject, slots) == {}, (
        'Required: unconstrained coordinates remain exact and fixed orbits refuse off orbit input.'
    )
    subject = fixed_model()
    subject.structures[0].atom_sites[0].fract_x.value = 0.17
    with pytest.raises(AssertionError):
        saved_parameters(subject, 'iucr_99')
    subject.structures[0].space_group.coord_system_code = ''
    with pytest.raises(AssertionError):
        setting(subject.structures[0])
