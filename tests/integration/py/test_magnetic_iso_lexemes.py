"""ADR-0108 section 12: source lexemes, grammar and second-save preservation."""

import edi as api
import pytest

from tests.fixtures.magnetic_pnma import commensurate, iso_lexemes, reference


@pytest.mark.parametrize('route', ['project', 'factory'])
@pytest.mark.parametrize('syntax', ['native', 'magcif'])
@pytest.mark.parametrize('newline', ['lf', 'crlf'])
def test_raw_iso_lexemes_survive_each_reader_and_two_saves(tmp_path, route, syntax, newline):
    opaque, expected = iso_lexemes.declarations()
    source = commensurate.structure()
    if syntax == 'magcif':
        # Remove complete native declarations before converting their tag names.
        source = source.replace('\n_parent_space_group.derived false\n', '\n', 1)
        source = source.replace('\n_parent_space_group.reference_setting standard\n', '\n', 1)
        source = commensurate.magnetic_cif(source)
    # Opaque lexemes never enter a structural tag-renaming helper.
    source += opaque
    if newline == 'crlf':
        source = source.replace('\n', '\r\n')
    root = reference.project(tmp_path / 'input', source)
    if route == 'factory':
        created = api.StructureFactory.from_cif_str(source)
        assert list(created.iso_declarations) == expected, (
            'ADR-0108 the factory exposes source lexemes, not decoded or re-quoted values'
        )
    project = api.Project.load(root)
    assert list(project.structure.iso_declarations) == expected, (
        'ADR-0108 scalar and loop token kind, delimiters, whitespace and order survive load'
    )
    project.save_as(tmp_path / 'first')
    first = (tmp_path / 'first/structures/cosio.edi').read_text()
    # Every token is independently prescribed; a self-round-trip alone is insufficient.
    for lexeme in iso_lexemes.TOKENS:
        assert '\n' + lexeme + '\n' in first, (
            'ADR-0108 each saved lexeme is emitted verbatim on its own line'
        )
    reloaded = api.Project.load(tmp_path / 'first')
    assert list(reloaded.structure.iso_declarations) == expected, (
        'ADR-0108 native reload preserves missing markers versus quoted and text-field literals'
    )
    reloaded.save_as(tmp_path / 'second')
    assert (tmp_path / 'second/structures/cosio.edi').read_text() == first, (
        'ADR-0108 a second save preserves the exact first-save bytes'
    )


def test_mixed_iso_loop_refuses_instead_of_losing_non_iso_fields(tmp_path):
    source = commensurate.structure() + 'loop_\n_iso_contract_mix\n_other_contract_mix\n1 2\n'
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)iso|mix'):
        api.Project.load(reference.project(tmp_path / 'input', source))
