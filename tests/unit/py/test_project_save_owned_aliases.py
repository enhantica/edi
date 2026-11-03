"""Closed setting and public owned-parameter entrances for the Save reference."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as Record

import pytest

from tests.fixtures.project_save import completion
from tests.fixtures.project_save.completion import (
    EXTINCTION,
    declared_relations,
    model_inputs,
    setting,
)
from tests.fixtures.project_save.reference import require_saved_parameters, saved_parameters
from tests.unit.py.test_project_save_completion_reference import model, parameter, publish


def named_structure(name, code):
    return Record(space_group=Record(name_h_m=name, coord_system_code=code))


def test_short_index_revalidates_private_changed_bytes_after_exact_cache_warm(
    tmp_path, monkeypatch
):
    original = Path(completion.__file__).with_name('declared-space-groups.symtab')
    table = tmp_path / 'declared-space-groups.symtab'
    assert table.resolve() != original.resolve(), 'The adversary cannot overwrite the shared table'
    data = original.read_bytes()
    table.write_bytes(data)
    monkeypatch.setattr(completion, '__file__', str(tmp_path / 'completion.py'))
    completion.declared_groups.cache_clear()
    completion.declared_short_aliases.cache_clear()
    try:
        assert setting(named_structure('P 1 21/c 1', 'b1'))[0] == (14, 'b1'), (
            'The private original payload first reaches a genuine exact-name lookup'
        )
        warmed = completion.declared_groups()[0]
        table.write_bytes(data + b'\nP 1 99/c 1\t14\tb1\n')
        assert completion.declared_groups()[0] is warmed, (
            'The changed-byte adversary reaches the already validated declaration cache'
        )
        with pytest.raises(
            AssertionError, match='exact short-name table bytes must remain frozen'
        ):
            setting(named_structure('P99/c', 'b1'))
    finally:
        completion.declared_short_aliases.cache_clear()
        completion.declared_groups.cache_clear()


@pytest.mark.parametrize('name', ['P 21/c', 'P21/c', 'P 1 21/c 1'])
def test_short_names_select_the_same_explicit_declared_setting(name):
    assert setting(named_structure(name, 'b1'))[0] == (14, 'b1'), (
        'The frozen declared full H-M spelling owns the short explicit-b1 identity'
    )


@pytest.mark.parametrize(
    ('name', 'code'),
    [
        ('P 21/c', ''),
        ('P 21/c', 'unknown'),
        ('P 999', 'b1'),
        ('P 21/c:b1', 'a3'),
        ('P 21/c 1 1', 'b1'),
    ],
)
def test_short_fallback_never_guesses_or_widens_an_exact_match(name, code):
    with pytest.raises(AssertionError):
        setting(named_structure(name, code))


@pytest.mark.parametrize(('name', 'key'), [('P1', (1, '-')), ('P-1', (2, '-'))])
def test_identity_direction_is_not_removed_from_triclinic_symbols(name, key):
    assert setting(named_structure(name, ''))[0] == key, (
        'Bare identity and inversion remain distinct frozen declarations'
    )


def test_a_changed_valid_short_setting_cannot_satisfy_the_old_identity():
    subject = model()
    structure = subject.structures[0]
    structure.space_group = named_structure('P21/c', 'b1').space_group
    structure.atom_sites[0].wyckoff_letter = 'e'
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')
    structure.space_group.coord_system_code = 'a3'
    assert setting(structure)[0] == (14, 'a3'), (
        'The adversary reaches another valid explicit setting'
    )
    with pytest.raises(AssertionError):
        require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')


def owned_model(field):
    subject = model()
    first, second, dependent = parameter(12), parameter(6), parameter(3)
    fields = dict.fromkeys(EXTINCTION)
    fields[field] = dependent
    if field.startswith('coefficient_'):
        kind, distribution = 'larson-anisotropic', None
    elif field == 'coefficient':
        kind, distribution = 'larson-isotropic', None
    else:
        kind, distribution = 'mixed', 'gaussian'
    extinction = Record(type=kind, mosaic_distribution=distribution, **fields)
    subject.experiments = [
        Record(
            name=name,
            linked_structures=[Record(structure_id='sample', scale=scale, enabled=True)],
            extinction=extinction if name == 'first' else None,
            experiment_type=Record(
                beam_mode=Record(name='TIME_OF_FLIGHT'), radiation_probe=Record(name='NEUTRON')
            ),
        )
        for name, scale in [('first', first), ('second', second)]
    ]
    subject.parameters += [first, second, dependent]
    subject.analysis.aliases = [
        Record(id='leader', parameter_unique_name='first.linked_structure.sample.scale'),
        Record(id='middle', parameter_unique_name='second.linked_structure.sample.scale'),
        Record(id='dependent', parameter_unique_name='first.extinction.' + field),
    ]
    # The dependent's consumer precedes its leader's relation in the actual declaration list.
    subject.analysis.constraints = [
        Record(id='consumer', expression='dependent=middle/2', enabled=True),
        Record(id='middle', expression='middle=leader/2', enabled=True),
    ]
    return subject


@pytest.mark.parametrize('field', EXTINCTION)
def test_all_present_extinction_slots_and_bank_scales_keep_owned_topological_relations(field):
    subject = owned_model(field)
    _, slots, lookups, _, identity = model_inputs(subject)
    indices, graph = declared_relations(identity, slots, lookups)
    assert set(indices) == {'leader', 'middle', 'dependent'}, (
        'Every offered alias is actually bound'
    )
    assert len(graph) == 2, 'Both consumer-first declared relations reach the existing evaluator'
    reference = saved_parameters(subject, 'iucr_99')
    assert reference[0]['completed'][-3:] == [
        (12.0, 0.0, False),
        (6.0, 0.0, False),
        (3.0, 0.0, False),
    ], 'Literal independent division controls retain all value/SU/free states'
    publish(subject, reference, 'completed')
    require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')


@pytest.mark.parametrize(
    'mutation',
    [
        'bank',
        'link',
        'removed-link',
        'duplicate-link',
        'absent-field',
        'added-field',
        'subtype',
        'distribution',
        'duplicate-storage',
        'unknown-path',
        'descriptor',
        'duplicate-target',
        'cycle',
        'missing-alias',
        'wrong-link-path',
    ],
)
def test_owned_alias_population_and_declared_identity_cannot_be_relabelled(mutation):
    subject = owned_model('crystal_radius')
    reference = saved_parameters(subject, 'iucr_99')
    publish(subject, reference, 'completed')
    require_saved_parameters(subject.parameters, reference, model=subject, phase='completed')
    bad = deepcopy(subject)
    bank = bad.experiments[0]
    if mutation == 'bank':
        bank.name = 'renamed'
    elif mutation == 'link':
        bank.linked_structures[0].structure_id = 'renamed'
    elif mutation == 'removed-link':
        bank.linked_structures.clear()
    elif mutation == 'duplicate-link':
        bank.linked_structures.append(deepcopy(bank.linked_structures[0]))
    elif mutation == 'absent-field':
        bank.extinction.crystal_radius = None
    elif mutation == 'added-field':
        bank.extinction.domain_radius = parameter(0)
        bad.parameters.append(bank.extinction.domain_radius)
    elif mutation == 'subtype':
        bank.extinction.type = 'type-II'
    elif mutation == 'distribution':
        bank.extinction.mosaic_distribution = 'lorentzian'
    elif mutation == 'duplicate-storage':
        bank.extinction.crystal_radius = bank.linked_structures[0].scale
    else:
        alter_declaration(bad, mutation)
    with pytest.raises(AssertionError):
        require_saved_parameters(bad.parameters, reference, model=bad, phase='completed')
    if mutation in {
        'unknown-path',
        'descriptor',
        'duplicate-target',
        'cycle',
        'missing-alias',
        'wrong-link-path',
    }:
        with pytest.raises(AssertionError):
            saved_parameters(bad, 'iucr_99')


def alter_declaration(subject, mutation):
    if mutation == 'unknown-path':
        subject.analysis.aliases[0].parameter_unique_name = 'absent.linked_structure.sample.scale'
    elif mutation == 'wrong-link-path':
        subject.analysis.aliases[0].parameter_unique_name = 'first.linked_structure.absent.scale'
    elif mutation == 'descriptor':
        subject.analysis.aliases[2].parameter_unique_name = 'first.extinction.type'
    elif mutation == 'duplicate-target':
        subject.analysis.constraints.append(
            Record(id='extra', expression='dependent=leader', enabled=True)
        )
    elif mutation == 'missing-alias':
        subject.analysis.aliases.pop()
    else:
        assert mutation == 'cycle', 'Every authored declaration adversary reaches a named mutation'
        subject.analysis.constraints[1].expression = 'middle=dependent'
