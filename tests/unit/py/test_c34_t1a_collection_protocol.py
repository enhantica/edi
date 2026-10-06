""": R15 collection behavior and the no-detached-container property."""

from __future__ import annotations

import copy
import gc
import sys
import weakref
from pathlib import Path

import edi
import pytest

from tests.fixtures.constraint_expressions.project import unlink_structure

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank/project'
KEYED_KINDS = ('structures', 'experiments', 'atom_sites')
QUERY_NAMES = ('keys', 'values', 'items')
LIST_ONLY_MUTATORS = ('append', 'extend', 'insert', 'pop', 'reverse', 'sort', '__setitem__')
SHOW_NAMES_PAYLOAD = {
    'structures': ('Defined structures 🧩', "['ncaf']"),
    'experiments': (
        'Defined experiments 🔬',
        "['wish_1_10', 'wish_2_9', 'wish_3_8', 'wish_4_7', 'wish_5_6']",
    ),
}


def _project() -> edi.Project:
    return edi.Project.load(PROJECT)


def _collection(project: edi.Project, kind: str) -> object:
    if kind == 'structures':
        return project.structures
    if kind == 'experiments':
        return project.experiments
    if kind == 'atom_sites':
        return project.structures['ncaf'].atom_sites
    raise AssertionError(f' fixture named an unknown keyed collection kind: {kind}')


def _key(item: object, kind: str) -> str:
    return str(item.id if kind == 'atom_sites' else item.name)


def _new_item(kind: str, key: str) -> object:
    if kind == 'structures':
        item = edi.Structure()
        item.name = key
        item.cell.length_a.value = 7.125
        return item
    if kind == 'experiments':
        item = edi.BraggPdExperiment()
        item.name = key
        item.instrument.setup_twotheta_bank.value = 73.25
        return item
    if kind == 'atom_sites':
        item = edi.AtomSite()
        item.id = key
        item.type_symbol = 'Xe'
        item.adp_iso.value = 0.375
        return item
    raise AssertionError(f' fixture cannot construct an item for {kind}')


def _create(collection: object, kind: str, key: str) -> object:
    if kind == 'structures':
        return collection.create(name=key)
    if kind == 'experiments':
        return collection.create(name=key)
    if kind == 'atom_sites':
        return collection.create(id=key, type_symbol='Xe')
    raise AssertionError(f' fixture cannot create an item for {kind}')


def _probe_value(item: object, kind: str) -> float:
    if kind == 'structures':
        return float(item.cell.length_a.value)
    if kind == 'experiments':
        return float(item.instrument.setup_twotheta_bank.value)
    if kind == 'atom_sites':
        return float(item.adp_iso.value)
    raise AssertionError(f' fixture cannot read a live-value probe for {kind}')


def _set_probe_value(item: object, kind: str, value: float) -> None:
    if kind == 'structures':
        item.cell.length_a.value = value
    elif kind == 'experiments':
        item.instrument.setup_twotheta_bank.value = value
    elif kind == 'atom_sites':
        item.adp_iso.value = value
    else:
        raise AssertionError(f' fixture cannot mutate a live-value probe for {kind}')


def _item_probe(item: object, label: str) -> float:
    if label == 'Structure':
        return float(item.cell.length_a.value)
    if label == 'BraggPdExperiment':
        return float(item.instrument.setup_twotheta_bank.value)
    if label == 'AtomSite':
        return float(item.adp_iso.value)
    if label == 'LineSegment':
        return float(item.intensity.value)
    raise AssertionError(f' fixture cannot read an item-lifetime probe for {label}')


def _by_key_without_protocol(collection: object, kind: str, key: str) -> object:
    matches = [item for item in collection if _key(item, kind) == key]
    assert len(matches) == 1, f' liveness readback requires exactly one {kind} item keyed {key!r}'
    return matches[0]


def _assert_no_list_mutator(value: object, *, label: str) -> None:
    present = [name for name in LIST_ONLY_MUTATORS if hasattr(value, name)]
    assert not present, (
        f' I5 requires {label} to make detached-list mutation unspellable; found {present}'
    )


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_keyed_collections_expose_the_complete_r15_protocol(kind: str) -> None:
    collection = _collection(_project(), kind)

    for verb in ('add', 'create', 'remove', 'clear', *QUERY_NAMES):
        assert callable(getattr(collection, verb, None)), (
            f' requires {kind}.{verb} with the upstream R15 spelling'
        )
    assert isinstance(collection.names, list), (
        f' requires {kind}.names to preserve the upstream list return contract'
    )
    for query_name in QUERY_NAMES:
        result = getattr(collection, query_name)()
        assert iter(result) is result, (
            f' requires {kind}.{query_name}() to return a lazy iterator, not a snapshot'
        )
        assert not isinstance(result, (list, tuple, dict, set)), (
            f' requires {kind}.{query_name}() to avoid materialising a mutable container'
        )


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_mutating_verbs_return_none_and_reach_live_storage(kind: str) -> None:
    project = _project()
    collection = _collection(project, kind)
    original_names = tuple(_key(item, kind) for item in collection)
    replacement_key = original_names[0]
    replacement = _new_item(kind, replacement_key)

    assert collection.add(replacement) is None, (
        f' copies upstream {kind}.add return convention exactly'
    )
    assert tuple(collection.names) == original_names, (
        f' add replacement must preserve {kind} insertion position'
    )
    assert collection[replacement_key] is replacement, (
        f' add must store the same {kind} object, not a clone'
    )
    changed = 8.625
    _set_probe_value(replacement, kind, changed)
    assert _probe_value(_collection(project, kind)[replacement_key], kind) == changed, (
        f' post-add mutation of the standalone {kind} item must reach the project'
    )

    created_key = f'c34-created-{kind}'
    assert _create(collection, kind, created_key) is None, (
        f' copies upstream {kind}.create return convention exactly'
    )
    assert _key(collection[created_key], kind) == created_key, (
        f' {kind}.create must make the requested keyed item live immediately'
    )
    assert collection.remove(created_key) is None, (
        f' copies upstream {kind}.remove return convention exactly'
    )
    with pytest.raises(KeyError):
        collection.remove(created_key)
    assert collection.clear() is None, f' copies upstream {kind}.clear return convention exactly'
    assert len(collection) == 0, f' {kind}.clear must unlink every item'


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_queries_keys_and_exceptions_are_upstream_exact(kind: str) -> None:
    collection = _collection(_project(), kind)
    keys = list(collection.keys())
    values = list(collection.values())
    pairs = list(collection.items())

    assert keys == [_key(item, kind) for item in values], (
        f' {kind} keys and values must align in insertion order'
    )
    assert pairs == list(zip(keys, values, strict=True)), (
        f' {kind}.items must pair each live item with its key in insertion order'
    )
    assert list(collection.names) == keys, (
        f' {kind}.names must project the same ordered keys as keys()'
    )
    assert list(collection) == values, f' iteration over {kind} must yield items rather than keys'
    assert collection[-1] is values[-1], (
        f' {kind} negative positional indexing must follow upstream list semantics'
    )
    assert collection[keys[0]] is values[0], (
        f' {kind} string indexing must return the corresponding live item'
    )
    assert 3.5 not in collection, (
        f' {kind} membership must return false for an absent hashable probe'
    )
    with pytest.raises(KeyError):
        _ = collection['c34-absent-key']
    with pytest.raises(IndexError):
        _ = collection[len(collection)]
    with pytest.raises(TypeError):
        _ = collection[2.5]
    with pytest.raises(TypeError):
        _ = [] in collection


@pytest.mark.parametrize('kind', tuple(SHOW_NAMES_PAYLOAD))
def test_c34_t1a_show_names_prints_the_anchored_names_projection(
    kind: str,
    capfd: pytest.CaptureFixture[str],
) -> None:
    collection = _collection(_project(), kind)
    capfd.readouterr()

    assert collection.show_names() is None, (
        f' {kind}.show_names must preserve the upstream 0ffba46f return contract'
    )

    captured = capfd.readouterr()
    assert tuple(captured.out.splitlines()) == SHOW_NAMES_PAYLOAD[kind], (
        f' {kind}.show_names must emit only the authorized 0ffba46f payload lines: the '
        'exact header followed by the independently fixed saved-project names in order'
    )
    assert not captured.err, f' {kind}.show_names must not emit diagnostics on stderr'


def test_c34_t1a_duplicate_refusal_preserves_unique_upsert_and_removal() -> None:
    collection = _project().structures
    collection.clear()
    first = _new_item('structures', 'a')
    middle = _new_item('structures', 'b')
    last = _new_item('structures', 'c')
    for item in (first, middle, last):
        collection.add(item)
    # Before: the R15 regression pin admitted duplicates and observed first/last
    # disagreement. After  D8: refuse the duplicate and retain unique upsert.
    with pytest.raises(ValueError, match='a'):
        last.name = 'a'
    assert collection['a'] is first, (
        ' refused duplicate rename preserves the originally keyed item'
    )
    assert list(collection.keys()) == ['a', 'b', 'c'], (
        ' refused duplicate rename preserves all ordered keys'
    )
    replacement = _new_item('structures', 'a')
    collection.add(replacement)
    assert list(collection) == [replacement, middle, last], (
        ' equal-id add replaces its unique match and preserves other held items'
    )
    assert collection['a'] is replacement, (
        ' keyed lookup resolves the replacement after equal-id upsert'
    )
    collection.remove('a')
    assert list(collection) == [middle, last], (
        ' removal unlinks its unique matching item and preserves other held items'
    )
    assert collection['c'] is last, (
        ' the sibling whose rename was refused stays addressable after removal'
    )
    with pytest.raises(KeyError):
        _ = collection['a']


def test_c34_t1a_atom_site_id_is_the_live_rekeying_identity() -> None:
    sites = _project().structure.atom_sites
    site = sites[0]
    old_id = site.id
    site.id = 'C34-Rekeyed-Site'

    assert sites['C34-Rekeyed-Site'] is site, (
        ' AtomSites must derive lookup from the live AtomSite.id field'
    )
    with pytest.raises(KeyError):
        _ = sites[old_id]


@pytest.mark.parametrize('kind', KEYED_KINDS)
@pytest.mark.parametrize('route', ['getitem', 'iteration', 'values', 'items'])
def test_c34_t1a_every_item_return_route_is_live(kind: str, route: str) -> None:
    project = _project()
    collection = _collection(project, kind)
    first = next(iter(collection))
    key = _key(first, kind)
    if route == 'getitem':
        borrowed = collection[key]
    elif route == 'iteration':
        borrowed = next(iter(collection))
    elif route == 'values':
        borrowed = next(collection.values())
    else:
        pair = next(collection.items())
        borrowed = pair[1]

    expected = _probe_value(borrowed, kind) + 1.375
    _set_probe_value(borrowed, kind, expected)
    fresh = _by_key_without_protocol(_collection(project, kind), kind, key)
    assert _probe_value(fresh, kind) == expected, (
        f' {kind} item returned through {route} must mutate the live project, not a copy'
    )


def test_c34_t1a_query_results_and_pair_rows_close_all_mutable_copy_escapes() -> None:
    project = _project()
    for kind in KEYED_KINDS:
        collection = _collection(project, kind)
        _assert_no_list_mutator(collection, label=f'{kind} view')
        projected_names = collection.names
        expected_names = list(collection.keys())
        assert isinstance(projected_names, list), (
            f' requires {kind}.names to preserve the upstream list return contract'
        )
        assert projected_names == expected_names, (
            f' {kind}.names must initially project the exact ordered live keys'
        )
        projected_names.append(f'c34-detached-{kind}')
        assert list(collection.keys()) == expected_names, (
            f' mutating the projected {kind}.names list must not mutate live storage'
        )
        assert collection.names == expected_names, (
            f' a fresh {kind}.names projection must ignore prior snapshot mutation'
        )
        created_key = f'c34-after-names-{kind}'
        _create(collection, kind, created_key)
        assert projected_names == [*expected_names, f'c34-detached-{kind}'], (
            f' an existing {kind}.names snapshot must remain detached from later storage'
        )
        assert collection.names == [*expected_names, created_key], (
            f' a fresh {kind}.names projection must reflect later collection mutation'
        )
        for query_name in QUERY_NAMES:
            result = getattr(collection, query_name)()
            _assert_no_list_mutator(result, label=f'{kind}.{query_name}() result')
        pair = next(collection.items())
        assert isinstance(pair, tuple), (
            f' C4 requires each {kind}.items() row to be an immutable tuple'
        )
        with pytest.raises(TypeError):
            pair[0] = 'detached-mutation-is-forbidden'


def test_c34_t1a_positional_and_tuple_surfaces_are_live_or_immutable() -> None:
    project = _project()
    experiment = project.experiment
    background = experiment.background
    _assert_no_list_mutator(background, label='background positional view')
    for forbidden in ('remove', 'clear'):
        assert not hasattr(background, forbidden), (
            f' background view must not expose list mutator {forbidden}'
        )

    point = background[0]
    expected = point.intensity.value + 2.875
    point.intensity.value = expected
    assert project.experiment.background[0].intensity.value == expected, (
        ' background indexing must return a live LineSegment rather than a copy'
    )

    excluded = experiment.excluded_regions
    assert isinstance(excluded, tuple), (
        ' C5 requires excluded_regions to return an immutable outer tuple'
    )
    assert all(isinstance(pair, tuple) for pair in excluded), (
        ' C5 requires every excluded_regions pair to be immutable too'
    )
    _assert_no_list_mutator(excluded, label='excluded_regions tuple')
    replacement = [(11.25, 12.75), (21.5, 23.0)]
    experiment.excluded_regions = replacement
    assert experiment.excluded_regions == tuple(replacement), (
        ' keeps excluded_regions replacement while making its getter immutable'
    )


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_keyed_collections_reject_wholesale_assignment(kind: str) -> None:
    project = _project()
    if kind == 'structures':
        owner, attribute = project, 'structures'
    elif kind == 'experiments':
        owner, attribute = project, 'experiments'
    else:
        owner, attribute = project.structure, 'atom_sites'
    with pytest.raises(AttributeError):
        setattr(owner, attribute, [])


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_held_items_and_leaves_survive_every_collection_mutator(kind: str) -> None:
    project = _project()
    collection = _collection(project, kind)
    held = next(iter(collection))
    held_key = _key(held, kind)
    leaf_before = _probe_value(held, kind)
    extra_key = f'c34-extra-{kind}'

    _create(collection, kind, extra_key)
    assert _probe_value(held, kind) == leaf_before, (
        f' {kind} create must not invalidate a held item or its Parameter leaf'
    )
    collection.remove(extra_key)
    replacement = _new_item(kind, extra_key)
    collection.add(replacement)
    assert _probe_value(held, kind) == leaf_before, (
        f' {kind} add/remove must not invalidate an unrelated held item'
    )
    held_leaf = (
        held.cell.length_a
        if kind == 'structures'
        else held.instrument.setup_twotheta_bank
        if kind == 'experiments'
        else held.adp_iso
    )
    assert held_leaf.is_attached(), f' live {kind} leaf must report attached'
    if kind == 'structures':
        unlink_structure(project, held_key)
    collection.remove(held_key)
    assert not held_leaf.is_attached(), f' removed {kind} leaf must report detached'
    with pytest.raises(RuntimeError, match='detached'):
        _set_probe_value(held, kind, leaf_before + 4.125)
    assert _probe_value(held, kind) == leaf_before, (
        f' removed {kind} item must retain its last readable value after refusing a write'
    )
    assert held_key not in collection, (
        f' removed {kind} item must stay detached while the caller still holds it'
    )
    other = _new_item(kind, held_key)
    collection.add(other)
    _set_probe_value(other, kind, leaf_before + 8.25)
    assert _probe_value(held, kind) == leaf_before, (
        f' live {kind} collection mutation must not flow back into a detached held item'
    )
    collection.clear()
    assert _probe_value(held, kind) == leaf_before, (
        f' {kind} clear must not invalidate an externally held detached item'
    )


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_owner_view_lifetime_holds_in_both_directions(kind: str) -> None:
    project = _project()
    if kind == 'atom_sites':
        owner = project.structure
        view = owner.atom_sites
    else:
        owner = project
        view = _collection(project, kind)
    baseline = sys.getrefcount(owner)
    transient = _collection(project, kind) if kind != 'atom_sites' else owner.atom_sites
    assert sys.getrefcount(owner) == baseline + 1, (
        f' {kind} view must hold exactly one keep-alive reference to its owner'
    )
    del transient
    gc.collect()
    assert sys.getrefcount(owner) == baseline, (
        f' dropping a {kind} view must restore its owner refcount without a cycle'
    )

    names = tuple(view.names)
    if kind == 'atom_sites':
        del owner
    del project
    gc.collect()
    assert tuple(view.names) == names, (
        f' {kind} view must remain usable after every lender wrapper is dropped'
    )
    _create(view, kind, f'c34-owner-dropped-{kind}')
    assert len(view) == len(names) + 1, (
        f' retained {kind} view must still mutate live storage after owner deletion'
    )


def test_c34_t1a_background_view_lifetime_holds_in_both_directions() -> None:
    project = _project()
    owner = project.experiment
    baseline = sys.getrefcount(owner)
    transient = owner.background
    assert sys.getrefcount(owner) == baseline + 1, (
        ' background view must hold exactly one keep-alive reference to its experiment'
    )
    del transient
    gc.collect()
    assert sys.getrefcount(owner) == baseline, (
        ' dropping a background view must restore the experiment refcount'
    )

    view = owner.background
    expected = view[0].intensity.value
    del owner, project
    gc.collect()
    assert view[0].intensity.value == expected, (
        ' background view must remain usable after its experiment wrapper is dropped'
    )


@pytest.mark.parametrize('kind', KEYED_KINDS)
def test_c34_t1a_each_iterator_keeps_only_its_view_alive(kind: str) -> None:
    for query_name in QUERY_NAMES:
        for partially_consumed in (False, True):
            project = _project()
            view = _collection(project, kind)
            baseline = sys.getrefcount(view)
            iterator = getattr(view, query_name)()
            assert sys.getrefcount(view) == baseline + 1, (
                f' {kind}.{query_name} iterator must retain exactly its immediate view'
            )
            if partially_consumed:
                next(iterator)
            del iterator
            gc.collect()
            assert sys.getrefcount(view) == baseline, (
                f' dropping a {kind}.{query_name} iterator must restore the view refcount'
            )
            assert len(view) > 0 and tuple(view.names), (
                f' {kind} view must remain usable after its {query_name} iterator dies'
            )

            iterator = getattr(view, query_name)()
            if partially_consumed:
                next(iterator)
            del project, view
            gc.collect()
            try:
                next(iterator)
            except StopIteration:
                assert partially_consumed, (
                    f' fresh {kind}.{query_name} iterator must yield after lenders die'
                )


def _weakref_item_cases(project: edi.Project) -> tuple[tuple[str, object, object], ...]:
    return (
        ('Structure', project.structures, project.structures[0]),
        ('BraggPdExperiment', project.experiments, project.experiments[0]),
        ('AtomSite', project.structure.atom_sites, project.structure.atom_sites[0]),
        ('LineSegment', project.experiment.background, project.experiment.background[0]),
    )


def test_c34_t1a_only_the_four_item_wrappers_are_runtime_weakrefable() -> None:
    project = _project()
    cases = _weakref_item_cases(project)
    for label, _view, item in cases:
        assert weakref.ref(item)() is item, (
            f' lifetime instrumentation requires {label} to support weakref.ref'
        )

    forbidden = (
        ('Project', project),
        ('collection view', project.structures),
        ('iterator', project.structures.values()),
        ('Parameter', project.structure.cell.length_a),
        ('Cell', project.structure.cell),
        ('instrument lens', project.experiment.instrument),
    )
    for _label, value in forbidden:
        with pytest.raises(TypeError, match='weak reference'):
            weakref.ref(value)


def test_c34_t1a_collection_items_release_wrappers_without_losing_storage() -> None:
    for case_index in range(4):
        project = _project()
        label, view, item = _weakref_item_cases(project)[case_index]
        remembered = _item_probe(item, label)
        witness = weakref.ref(item)
        del item
        gc.collect()
        assert witness() is None, (
            f' retained {label} collection storage must not retain its Python wrapper'
        )
        fresh = view[0]
        assert _item_probe(fresh, label) == remembered, (
            f' {label} C++ object must survive wrapper reclamation in owning storage'
        )


@pytest.mark.parametrize(
    ('case_index', 'label'),
    enumerate(('Structure', 'BraggPdExperiment', 'AtomSite', 'LineSegment')),
)
def test_c34_t1a_collection_items_outlive_dropped_collection_wrappers(
    case_index: int, label: str
) -> None:
    project = _project()
    case_label, view, item = _weakref_item_cases(project)[case_index]
    assert case_label == label, ' item lifetime fixture order must remain explicit'
    expected = _item_probe(item, label)
    del project, view
    assert _item_probe(item, label) == expected, (
        f' held {label} must remain usable after owner and view wrappers are dropped'
    )


def _leaf_cases(project: edi.Project) -> tuple[tuple[str, object, str], ...]:
    return (
        ('AtomSite.adp_iso', project.structure.atom_sites[0], 'adp_iso'),
        ('LineSegment.intensity', project.experiment.background[0], 'intensity'),
        ('Cell.length_a', project.structure.cell, 'length_a'),
        (
            'Instrument.setup_twotheta_bank',
            project.experiment.instrument,
            'setup_twotheta_bank',
        ),
    )


@pytest.mark.parametrize('case_index', range(4))
def test_c34_t1a_parameter_leaves_hold_and_release_each_named_lender(
    case_index: int,
) -> None:
    project = _project()
    label, holder, attribute = _leaf_cases(project)[case_index]
    baseline = sys.getrefcount(holder)
    leaf = getattr(holder, attribute)
    assert sys.getrefcount(holder) == baseline + 1, (
        f' {label} must retain exactly one reference to its immediate holder'
    )
    expected = leaf.value
    del leaf
    assert sys.getrefcount(holder) == baseline, (
        f' dropping {label} must restore its holder refcount without a cycle'
    )
    reread = getattr(holder, attribute)
    assert reread.value == expected, f' holder must re-read {label} after leaf release'
    assert reread.is_attached(), f' live {label} leaf must remain attached'
    reread.free = not reread.free
    assert getattr(holder, attribute).free == reread.free, (
        f' retained holder must still mutate {label} after an earlier wrapper dies'
    )


@pytest.mark.parametrize('case_index', range(4))
def test_c34_t1a_parameter_leaves_outlive_dropped_intermediate_lenders(case_index: int) -> None:
    label, holder, attribute = _leaf_cases(_project())[case_index]
    leaf = getattr(holder, attribute)
    expected = leaf.value
    del holder
    assert leaf.value == expected, (
        f' {label} must remain usable after its immediate lender wrapper is dropped'
    )


def test_c34_t1a_python_exposes_no_unreviewed_copy_protocol() -> None:
    project = _project()
    values = (
        project,
        project.structure,
        project.experiment,
        project.structure.atom_sites[0],
        project.experiment.background[0],
    )
    for value in values:
        for copier in (copy.copy, copy.deepcopy):
            with pytest.raises(TypeError):
                copier(value)
