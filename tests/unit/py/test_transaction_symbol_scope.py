"""Boundary observers select the public definition despite similarly named helpers."""

import pytest

from tests.fixtures.project_transactions.build import (
    global_function_symbols,
    observed_function_symbols,
)


@pytest.mark.parametrize('leading', ['_', '__'], ids=['elf', 'macho'])
@pytest.mark.parametrize(
    ('name', 'public', 'nested'),
    [
        (
            'write_project_archive',
            'ZN3edi21write_project_archiveERKxS1_',
            'ZN3edi6detail27write_project_archive_freshERKxS1_',
        ),
        (
            'fresh_archive_directory',
            'ZN3edi23fresh_archive_directoryERKx',
            'ZN3edi6detail26fresh_archive_directory_atERKxS1_',
        ),
    ],
)
def test_archive_observer_keeps_the_public_boundary_among_helper_symbols(
    leading, name, public, nested
):
    expected = leading + public
    defined = '\n'.join([
        '0000 T ' + leading + nested,
        '0010 t ' + expected + '.cold',
        '0015 T ' + expected + '.constprop.0',
        '0020 W ' + expected,
        '0030 T ' + expected,
        '0040 T ' + leading + public.replace('3edi', '6crysta', 1),
    ])
    assert global_function_symbols(defined, 'edi', name) == [expected], (
        'Archive observers select public definitions, excluding nested, cold or foreign helpers'
    )
    references = '\n'.join([' U ' + expected, '0000 T ' + expected, '0001 W ' + expected])
    assert global_function_symbols(references, 'edi', name, kind='U') == [expected], (
        'Typed call interception selects undefined references over definitions or weak names'
    )


def test_boundary_symbol_lookup_refuses_an_absent_public_definition():
    symbols = '0000 T _ZN3edi6detail26fresh_archive_directory_atERKxS1_'
    assert global_function_symbols(symbols, 'edi', 'fresh_archive_directory') == [], (
        'A similarly named nested helper never stands in for an absent public boundary'
    )


@pytest.mark.parametrize('missing', ['wrapper', 'public'])
def test_every_public_overload_requires_its_matching_typed_wrapper(missing):
    legacy = '0000 T _ZN3edi12load_projectERKx'
    extra = '0010 T _ZN3edi12load_projectERKxi'
    complete = legacy + '\n' + extra
    actual, wrappers = (complete, legacy) if missing == 'wrapper' else (legacy, complete)
    with pytest.raises(RuntimeError, match=r'overloads.*typed observer'):
        observed_function_symbols(actual, wrappers, 'edi', 'load_project')


def test_complete_typed_overload_set_is_admitted_without_dropping_an_entry():
    symbols = '0000 T _ZN3edi12load_projectERKx\n0010 T _ZN3edi12load_projectERKxi'
    assert observed_function_symbols(symbols, symbols, 'edi', 'load_project') == [
        '_ZN3edi12load_projectERKx',
        '_ZN3edi12load_projectERKxi',
    ], 'All typed public overloads remain observed, including the earlier entry point'


@pytest.mark.parametrize('leading', ['_', '__'], ids=['elf', 'macho'])
def test_const_publication_methods_retain_their_actual_const_receiver(leading):
    mutable = leading + 'ZN4QDir6renameERK7QStringS2_'
    constant = leading + 'ZNK4QDir6renameERK7QStringS2_'
    source = '\n'.join([
        ' U ' + mutable,
        ' U ' + constant,
        ' U ' + leading + 'ZNK4QDir6detail6renameEv',
    ])
    assert global_function_symbols(source, 'QDir', 'rename', kind='U') == [mutable, constant], (
        'The publication observer includes const and mutable public methods without helper aliases'
    )


@pytest.mark.parametrize('leading', ['_', '__'], ids=['elf', 'macho'])
def test_explicit_nested_publication_namespace_has_its_own_typed_boundary(leading):
    expected = leading + 'ZN3edi6detail26publish_fresh_project_pathERKxS2_'
    actual = (
        '0000 T ' + expected + '\n0001 T ' + leading + 'ZN3edi26publish_fresh_project_pathERKxS2_'
    )
    assert global_function_symbols(actual, 'edi::detail', 'publish_fresh_project_path') == [
        expected
    ], 'An explicitly named nested native publication entry resolves only its exact typed scope'
