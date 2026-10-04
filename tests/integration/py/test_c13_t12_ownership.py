"""model admission: checked ids, atomic whole-item assignment and re-init."""

import contextlib
import gc

import pytest
from c13_t12_support import engine, loops, project


def test_singular_experiment_assignment_cannot_copy_sibling_id(tmp_path):
    model = project(tmp_path / 'input')
    first, second = model.experiments
    first.instrument.calib_twotheta_offset.value = 0.17
    second.instrument.calib_twotheta_offset.value = 0.93
    loops._named(lambda: setattr(model, 'experiment', second), second.name)
    assert model.experiment.name == 'experiment', (
        ' refused whole-item copy preserves target identity'
    )
    assert model.experiment.instrument.calib_twotheta_offset.value.hex() == (0.17).hex(), (
        ' whole-item admission must check identity before copying scalar fields'
    )
    model.experiment.instrument.calib_twotheta_offset.value = 0.21
    assert model.experiment.instrument.calib_twotheta_offset.value.hex() == (0.21).hex(), (
        ' ordinary scalar edits remain available on checked items'
    )


# E11 previously covered site/experiment only; now every bound constructible
# keyed item is held across reconstruction and checked through its live view.
# SequentialExtractRule is native-only; abstract experiment intermediates have
# no bound constructor, so neither provides a Python reconstruction entry.
@pytest.mark.parametrize('kind', ['site', 'experiment', 'structure', 'orientation'])
def test_python_reinitialization_cannot_detach_attached_item(tmp_path, kind):
    model = project(tmp_path / 'input')
    if kind == 'site':
        items, key = model.structure.atom_sites, 'id'
    elif kind == 'structure':
        model.structures.create(name='second')
        items, key = model.structures, 'name'
    elif kind == 'orientation':
        # An unlinked bank permits the two distinct row keys needed by E11.
        model.experiment.linked_structure.structure_id = ''
        items, key = model.experiment.preferred_orientation, 'structure_id'
        items.create(structure_id='structure')
        items.create(structure_id='second')
    else:
        items, key = model.experiments, 'name'
    first, second = items
    before = [getattr(item, key) for item in items]
    original = getattr(second, key)

    def intact():
        assert list(items)[1] is second, (
            ' reconstruction preserves the held object in its owning view'
        )
        assert [getattr(item, key) for item in items] == before, (
            ' reconstruction preserves all stored identities'
        )
        loops._named(lambda: setattr(second, key, getattr(first, key)), getattr(first, key))
        assert getattr(second, key) == original, (
            ' reconstruction leaves sibling admission checked and unchanged'
        )

    with contextlib.suppress(TypeError, RuntimeError, ValueError):
        second.__init__()  # noqa: PLC2801 - E11 deliberately attempts reconstruction
    intact()
    if hasattr(second, '__setstate__'):
        state = first.__getstate__()
        with contextlib.suppress(TypeError, RuntimeError, ValueError):
            second.__setstate__(state)
        intact()
    else:
        assert '__setstate__' not in type(second).__dict__, (
            ' no state-replacement entry exists on this type'
        )


def test_default_and_explicit_bank_keys_collide_at_admission(tmp_path):
    model = project(tmp_path / 'input')
    model.experiments[0].name = ''
    loops._named(lambda: setattr(model.experiments[1], 'name', 'experiment'), 'experiment')
    assert model.experiments[1].name == 'second', (
        ' canonical-key collision refuses without renaming'
    )


@pytest.mark.parametrize('kind', ['site', 'structure', 'experiment'])
def test_edi_shared_membership_refuses_second_owner(tmp_path, kind):
    left, right = project(tmp_path / 'left'), project(tmp_path / 'right')
    a, b, key = _views(left, right, kind)
    member = a[0]
    original = [getattr(item, key) for item in b]
    with pytest.raises((ValueError, RuntimeError)) as caught:
        b.add(member)
    assert getattr(member, key) in str(caught.value), ' shared-owner refusal must name the item'
    assert [getattr(item, key) for item in b] == original, (
        ' refused sharing leaves the destination unchanged'
    )
    loops._named(lambda: setattr(a[1], key, getattr(member, key)), getattr(member, key))


def _views(left, right, kind):
    if kind == 'site':
        return left.structure.atom_sites, right.structure.atom_sites, 'id'
    if kind == 'structure':
        left.structures.create(name='second')
        right.structures.create(name='second')
        return left.structures, right.structures, 'name'
    return left.experiments, right.experiments, 'name'


@pytest.mark.parametrize('kind', ['site', 'structure', 'experiment'])
@pytest.mark.parametrize('removal', ['remove', 'delete', 'clear', 'owner-destruction', 'upsert'])
def test_edi_held_item_detaches_at_each_lifecycle_exit(tmp_path, kind, removal):
    model, other = project(tmp_path / 'left'), project(tmp_path / 'right')
    view, other_view, key = _views(model, other, kind)
    member, sibling = view[0], view[1]
    identity = getattr(member, key)
    sibling_key = getattr(sibling, key)
    if removal == 'remove':
        view.remove(identity)
    elif removal == 'delete':
        del view[identity]
    elif removal == 'clear':
        view.clear()
    elif removal == 'upsert':
        replacement = other_view[0]
        other_view.remove(getattr(replacement, key))
        setattr(replacement, key, identity)
        view.add(replacement)
        assert view[0] is replacement, ' keyed add must replace the equal-id item'
        assert len(view) == 2, ' upsert must never append a duplicate identity'
    else:
        del view, model
        gc.collect()
    setattr(member, key, sibling_key)
    assert getattr(member, key) == sibling_key, (
        ' detached held items have free identity after every lifecycle exit'
    )


@pytest.mark.parametrize('kind', ['site', 'structure', 'experiment'])
def test_edi_adding_same_item_twice_is_idempotent(tmp_path, kind):
    model, other = project(tmp_path / 'left'), project(tmp_path / 'right')
    view, _, key = _views(model, other, kind)
    member = view[0]
    before = [getattr(item, key) for item in view]
    view.add(member)
    assert [getattr(item, key) for item in view] == before, (
        ' same-pointer upsert keeps one membership'
    )
    loops._named(lambda: setattr(view[1], key, getattr(member, key)), getattr(member, key))


def test_edi_dictionary_factory_rejects_internal_duplicates():
    spec = {
        'name': 'structure',
        'space_group': {'name_h_m': 'P 1'},
        'atom_sites': [{'id': 'X', 'type_symbol': 'O'}, {'id': 'Y', 'type_symbol': 'O'}],
    }
    control = engine.StructureFactory.from_dict(spec)
    assert [s.id for s in control.atom_sites] == ['X', 'Y'], (
        ' dictionary factory unique control reaches both rows'
    )
    spec['atom_sites'][1]['id'] = 'X'
    loops._named(lambda: engine.StructureFactory.from_dict(spec), 'X')


def test_edi_default_collections_have_unique_keys():
    model = engine.Project()
    for collection in (model.structures, model.experiments):
        keys = [
            item.name or ('structure' if collection is model.structures else 'experiment')
            for item in collection
        ]
        assert len(keys) == len(set(keys)) == 1, (
            ' explicit default construction supplies one distinct member'
        )


# Review-6 F2 before: ASCII diagnostics only. After: the binding must retain the
# complete printable arbitrary id, including the suffix beyond embedded NUL.
@pytest.mark.parametrize('kind', ['site', 'structure', 'experiment', 'orientation'])
@pytest.mark.parametrize(
    ('identity', 'printed'),
    [('\0tail', r'\x00tail'), ('head\x01tail', r'head\x01tail'), ('bäd\tend', 'bäd\\x09end')],
)
def test_arbitrary_identity_refusals_survive_python_translation(tmp_path, kind, identity, printed):
    left, right = project(tmp_path / 'left'), project(tmp_path / 'right')
    if kind == 'orientation':
        for model in (left, right):
            model.experiment.linked_structure.structure_id = ''
            model.experiment.preferred_orientation.clear()
            model.experiment.preferred_orientation.create(structure_id='first')
            model.experiment.preferred_orientation.create(structure_id='second')
        items, other, key = (
            left.experiment.preferred_orientation,
            right.experiment.preferred_orientation,
            'structure_id',
        )
    else:
        items, other, key = _views(left, right, kind)
    held, sibling = items
    setattr(held, key, identity)
    donor = other[0]
    other.remove(getattr(donor, key))
    setattr(donor, key, identity)
    before = [getattr(item, key) for item in items]

    def named(action):
        with pytest.raises((ValueError, RuntimeError)) as caught:
            action()
        assert printed in str(caught.value), (
            ' Python refusal preserves the full printable arbitrary identity'
        )
        assert all(ord(char) >= 32 and ord(char) != 127 for char in str(caught.value)), (
            ' Python refusal never displays raw identity controls'
        )

    named(lambda: setattr(sibling, key, identity))
    named(lambda: items._assign([held, donor]))
    named(lambda: items._assign([held, held]))
    named(lambda: other.add(held))
    assert [getattr(item, key) for item in items] == before, (
        ' arbitrary-string refusals retain original collection identities'
    )
    assert items[0] is held, ' arbitrary-string refusals retain the original held object'
