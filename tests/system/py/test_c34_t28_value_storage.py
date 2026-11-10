"""F23: read physical native layouts, not wrapper/schema names or census labels.

A loop item may retain a read image for stable native references. Its table
must own typed value columns for every schema cell,
including caller-defined schemas. Clang supplies the actual expanded layouts;
this independent witness never treats the census's `form` as storage evidence.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_compiler import crysta_headers
from tests.fixtures.c34_t28_compiler import standard_headers as _standard_headers

standard_headers = _standard_headers
ROOT = Path(__file__).resolve().parents[3]
ROWS = [
    'AtomSite',
    'LineSegment',
    'PrefOrient',
    'SequentialExtractRule',
    'Structure',
    'BraggPdExperiment',
]
PUBLIC = """
namespace edi {
struct C34StorageRow {
    detail::Written<double> value{1.25};
    detail::WrittenText label;
    Parameter scale{31.25};
};
}
namespace crysta {
template <>
struct RowSchema<edi::C34StorageRow> {
    static constexpr const char* name = "_c34_storage_row";
    static constexpr auto fields = std::tuple{
        &edi::C34StorageRow::value, &edi::C34StorageRow::label, &edi::C34StorageRow::scale};
    static constexpr std::array items{"value", "label", "scale"};
};
namespace detail {
template <>
struct ForeignTable<edi::C34StorageRow> {
    using type = edi::ItemVec<edi::C34StorageRow>;
};
}  // namespace detail
}  // namespace crysta
"""


def layouts(text):
    result = {}
    for block in text.split('*** Dumping AST Record Layout'):
        lines = [line.partition('|')[2] for line in block.splitlines() if '|' in line]
        if not lines:
            continue
        name = lines[0].strip()
        if name.startswith(('class ', 'struct ', 'union ')):
            result[name] = lines[1:]
    return result


def expanded_standard_aliases(text):
    # A standard-defined alias, applied equally to AST and layout spellings.
    return re.sub(r'\bstd::(?:__\w+::)?string\b', 'std::basic_string<char>', text)


def inline_payload(lines):
    # Record-layout expansion follows by-value subobjects only, never pointer
    # targets. A column-owned node reached by a handle does not appear inline.
    scalar = re.compile(r'^(?:double|float|int|bool|_Bool)\s+\w+(?:\[|$)')
    container = re.compile(
        r'^class std::(?:basic_string|vector|map|deque|list|set|unordered_map)<'
    )
    return [
        expanded_standard_aliases(line.strip())
        for line in lines
        if scalar.match(line.strip()) or container.match(expanded_standard_aliases(line.strip()))
    ]


def concrete_payload_types(dump):
    # Before: a spelling heuristic excluded the primary template. libc++ uses
    # a dependent __remove_cvref spelling instead. After: the AST's concrete
    # specialization boundary, and only its directly owned value field, count.
    result, specialization = [], None
    for line in dump.splitlines():
        tree = re.match(r'([| `-]*)(.*)', line)
        depth, entry = len(tree[1]) // 2, tree[2]
        if specialization is not None and depth <= specialization:
            specialization = None
        if entry.startswith('ClassTemplateSpecializationDecl ') and re.search(
            r'\bC34SchemaPayload definition\b', entry
        ):
            specialization = depth
        elif specialization is not None and depth == specialization + 1:
            field = re.match(r"FieldDecl.*\bvalue '(.+)'", entry)
            if field:
                spellings = re.findall(r"'([^']+)'", entry)
                # Standard string is a defined alias for basic_string<char>;
                # Clang 19/libc++ can retain the alias in a concrete AST type.
                result.append(expanded_standard_aliases(spellings[-1]))
    return result


def physical(root, owner, directory, standard_headers):
    source = directory / 'storage.cpp'
    # Force each schema member's concrete layout separately, excluding nested
    # categories a Structure/Experiment carries but this loop does not own.
    source.write_text(
        '#include "edi/model.hpp"\n'
        + (PUBLIC if owner == 'C34StorageRow' else '')
        + 'template<class C> decltype(auto) payload(const C& cell) {\n'
        'if constexpr (requires { cell.get(); }) return cell.get();\n'
        'else if constexpr (requires { cell.value(); }) return cell.value();\n'
        'else return cell.value.get(); }\n'
        'template<class R, std::size_t I> struct C34SchemaPayload {\n'
        'using C = std::remove_cvref_t<decltype(std::declval<R&>().*\n'
        'std::get<I>(crysta::RowSchema<R>::fields))>;\n'
        'std::remove_cvref_t<decltype(payload(std::declval<const C&>()))> value; };\n'
        'template<class R, std::size_t I> struct C34SchemaCell {\n'
        'using Cell = std::remove_cvref_t<decltype(std::declval<R&>().*\n'
        'std::get<I>(crysta::RowSchema<R>::fields))>; Cell cell; };\n'
        'template<class R, std::size_t... I> constexpr auto cells(std::index_sequence<I...>) {\n'
        'return ((sizeof(C34SchemaCell<R,I>) + sizeof(C34SchemaPayload<R,I>)) + ...); }\n'
        + f'constexpr auto bytes = cells<edi::{owner}>(std::make_index_sequence<\n'
        + f'std::tuple_size_v<decltype(crysta::RowSchema<edi::{owner}>::fields)>>{{}});\n'
        + f'void probe() {{ edi::ItemVec<edi::{owner}> rows; '
        + f'rows.push_back(std::make_shared<edi::{owner}>()); }}\n'
    )
    compiler = shutil.which('clang++')
    assert compiler, ' F23 physical storage requires the actual Clang layout reader'
    result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-fsyntax-only',
            '-include-pch',
            str(standard_headers),
            '-Xclang',
            '-fdump-record-layouts',
            '-Xclang',
            '-ast-dump',
            '-Xclang',
            '-ast-dump-filter=C34SchemaPayload',
            '-I' + str(root / 'core/include'),
            '-I' + str(crysta_headers()),
            '-I' + str(ROOT / '.pixi/envs/default/include'),
            str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        ' F23 both schema cells and their actual admission route must compile: ' + result.stderr
    )
    parsed = layouts(result.stdout)
    cells = [lines for name, lines in parsed.items() if re.match(r'^struct C34SchemaCell<', name)]
    assert cells, ' F23 the reader must resolve actual schema-member layouts'
    table = [
        lines
        for name, lines in parsed.items()
        if re.fullmatch(
            r'(?:class|struct) edi::ItemVec<(?:struct |class )?edi::' + owner + r'>::Table', name
        )
    ]
    assert len(table) == 1, ' F23 the reader must resolve the actual collection table'
    payloads = concrete_payload_types(result.stdout)
    assert len(payloads) == len(cells), (
        ' F23 each actual schema cell must have an independently compiled payload type'
    )
    return cells, table[0], payloads


@pytest.mark.parametrize('owner', [*ROWS, 'C34StorageRow'])
def test_every_loop_stores_all_schema_cells_in_typed_value_columns(
    tmp_path, owner, standard_headers
):
    _cells, table, payload_types = physical(ROOT, owner, tmp_path, standard_headers)
    columns = [
        expanded_standard_aliases(line)
        for line in table
        if re.search(r'\bcrysta::(?:OwnedColumn|Column)<', line)
    ]
    assert columns, (
        ' I14/F23 each actual ItemVec table owns typed value columns rather than only '
        'anchors, column stamps and hold records: ' + owner
    )
    for payload in payload_types:
        # Leaf types are read from concrete payload layouts. Merely converting
        # metadata stamps to Column<uint64_t> cannot satisfy a value column.
        wanted = re.findall(r'\b(?:double|float|int|bool|_Bool|basic_string|optional)\b', payload)
        assert wanted, ' F23 every independently read schema payload needs a storage type'
        wanted = ['unsigned char' if word in {'bool', '_Bool'} else word for word in wanted]
        assert any(all(word in column for word in wanted) for column in columns), (
            ' F23 the table must hold typed columns for every schema payload: '
            + owner
            + ': '
            + payload
        )


def census_copy(directory):
    root = directory / 'census'
    for relative in (
        'core/include',
        'core/src',
        'lib/src',
        'app/src',
        'cli',
        'tools/checks',
        'data',
    ):
        source = ROOT / relative
        if source.is_dir():
            shutil.copytree(source, root / relative, ignore=shutil.ignore_patterns('__pycache__'))
    return root


@pytest.mark.parametrize('owner', ROWS)
def test_census_refuses_a_table_that_has_lost_its_value_columns(tmp_path, owner):
    root = census_copy(tmp_path)
    header = root / 'core/include/edi/model.hpp'
    source = header.read_text()
    assert source.count('        Columns columns;') == 1, (
        ' F23 the accident plant must reach the actual table value storage'
    )
    header.write_text(
        source.replace('        Columns columns;', '        // Accident: value storage omitted.')
    )
    result = subprocess.run(
        [sys.executable, str(root / 'tools/checks/category_census.py'), '--write'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert result.returncode != 0, (
        ' I14/F23 metadata-only tables cannot generate a complete storage census'
    )
    assert owner in result.stdout + result.stderr, (
        ' F23 a missing value-column refusal must name every affected category: ' + owner
    )


def test_physical_reader_distinguishes_values_from_stable_column_handles():
    held = ['    class std::shared_ptr<struct Cell<double>> cell', '      element_type * _M_ptr']
    embedded = ['    double value', '    class std::basic_string<char> text']
    assert not inline_payload(held), ' F23 an owning cell handle is not an inline row value'
    assert len(inline_payload(embedded)) == 2, (
        ' F23 actual embedded values cannot be hidden by cell names'
    )
    assert len(inline_payload(['    class std::string text'])) == 1, (
        ' F23 a standard string alias cannot conceal an embedded physical value'
    )
    for dependent in ('typename dependent::type', '__remove_cvref(decltype(dependent))'):
        dump = (
            'ClassTemplateDecl 0 C34SchemaPayload\n'
            '|-CXXRecordDecl 0 struct C34SchemaPayload definition\n'
            f"| `-FieldDecl 0 value 'alias':'{dependent}'\n"
            '|-ClassTemplateSpecializationDecl 0 struct C34SchemaPayload definition\n'
            "| |-FieldDecl 0 value 'alias':'std::string'\n"
            '| `-CXXRecordDecl 0 struct Nested definition\n'
            "|   `-FieldDecl 0 value 'int'\n"
            '`-ClassTemplateSpecializationDecl 0 struct C34SchemaPayload definition\n'
            "  `-FieldDecl 0 value 'alias':'std::optional<double>'\n"
        )
        assert concrete_payload_types(dump) == [
            'std::basic_string<char>',
            'std::optional<double>',
        ], ' F23 only concrete directly owned schema payload fields count on either ABI'


def test_census_checks_value_storage_of_a_caller_declared_loop(tmp_path):
    root = census_copy(tmp_path)
    header = root / 'core/include/edi/model.hpp'
    header.write_text(header.read_text() + PUBLIC)
    # --write removes the trivial stale-JSON reason: only the actual storage
    # validity can authorize generating a census for this added public schema.
    result = subprocess.run(
        [sys.executable, str(root / 'tools/checks/category_census.py'), '--write'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert result.returncode == 0, (
        ' F23 a caller schema with actual value columns can generate its storage census: '
        + result.stdout
        + result.stderr
    )

    census = json.loads((root / 'data/category-census.json').read_text())
    assert '_c34_storage_row' in repr(census), (
        ' F23 the generated census must contain the added caller schema'
    )
