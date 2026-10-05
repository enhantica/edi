#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Every category is one table, declared once (ADR-0018).

Each category of edi's model has one schema in ``core/include/edi/model.hpp``: a
``crysta::RowSchema<edi::Row>`` for a loop of items, and a ``…Category`` struct for every other
category. This tool reads the schemas and the model classes from the source, generates
``data/category-census.json`` from them, and refuses:

* a data member of a model class that no schema names and that is not a part of a table — a
  holder of categories, a table of schema rows, a row's link, identity or token — or a record
  listed in ``NOT_STORAGE``;
* a class of ``model.hpp`` that is neither a model class nor listed in ``NOT_MODEL`` with its
  reason (a storage primitive, a fit report, a computed result);
* a member that two schemas name;
* a category with more than one schema, unless it is a type-switched category: one non-loop
  schema holding the selector (its ``type`` item) and one loop schema per alternative, each
  listing in ``variants`` the selector tokens it serves, no token twice;
* a schema whose storage is not a table: a cell of a loop row that is not a cell view
  (``ItemKey``, ``detail::Written<T>``, ``detail::WrittenText``, ``Parameter``), a column that is
  a standard container, or an aggregate that is not behind ``detail::Written``. A plain scalar is
  a cell of a non-loop category only, where the cell stands in place;
* a loop category whose table does not store its cells in value columns. The storage is read
  from the table class itself: ``ItemVec``'s table must hold ``detail::RowColumns<T>``, the
  tuple of ``detail::FieldColumns<Field>::type`` over the schema's fields, and the value column
  of every cell — each ``FieldColumns`` specialisation, and each member of a column bundle such
  as ``detail::ParameterColumns`` — must be a ``crysta::Column<V>``. The census records the
  value columns of each loop column (``storage``);
* a ``Parameter`` attribute that is not a cell view;
* a category on file — a ``"_name.item"`` tag anywhere in the sources — that is no schema's name
  and no schema's ``legacy`` spelling, and a CIF tag (a ``"_name"`` literal without a dot in
  ``core/``) that no schema lists in its ``cif``;
* a non-loop category whose owner has no row token, or whose table view (``OneRow<Category>``)
  ``core/src/canonical_encoding.cpp`` does not instantiate;
* a committed census that differs from the generated one.

Run: ``python tools/checks/category_census.py`` (in ``verify-quick``, ``verify-full`` and CI);
``--write`` regenerates the census; ``--root DIR`` checks another tree. Exit 0 when clean, 1 with
one line per problem.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

HERE = Path(__file__).resolve().parent
MODEL = 'core/include/edi/model.hpp'
CENSUS = 'data/category-census.json'
INSTANTIATIONS = 'core/src/canonical_encoding.cpp'
TAG_SOURCES = ('core', 'lib/src', 'app/src', 'cli')
# Where a tag without a dot is a CIF tag: the loader and the model headers.
CIF_SOURCES = ('core/',)
# The item suffixes the loader composes `_data_range.<axis>_min`, `_max` and `_step` from.
TAG_FRAGMENTS = {'_min', '_max', '_step'}

# Classes of model.hpp that hold no model category, each with its reason.
NOT_MODEL = {
    'Membership': 'a collection membership record (ADR-0016)',
    'RowLink': "a row's link to its collection's record",
    'Epoch': 'a stamp: the identity of a write',
    'CategoryRow': 'the row token of a non-loop category',
    'Written': 'a cell view',
    'WrittenText': 'a cell view',
    'ItemKey': 'a cell view: the id of a keyed row',
    'Parameter': 'a parameter: the cells of one parameter column bundle',
    'TableNotes': "a loop table's columns as its rows' cells reach them, with their stamps",
    'Holding': 'one holding of a row: the table, and the position of the row in it',
    'RowHold': 'the tables that hold one row, whose columns its cells write',
    'ParameterColumns': 'the five value columns that store one parameter of every row of a table',
    'CarriedNames': 'the table behind a carried loop: its item names, as a column',
    'CarriedCells': "the table behind a carried loop: its rows' cells, a column per item",
    'DataSource': "a handed-out data object's link to its experiment",
    'CategoryRef': "a parameter's link to its category's row",
    'KeyedBase': 'the base of the table class',
    'ItemVec': 'the table class of a loop category',
    'State': "a cell view's state: its value, its last write and the tables that hold its row",
    'TextState': "a text cell's state: its text, its last write and the tables that hold its row",
    'Braced': 'one braced value on its way into a cell: a temporary of an assignment',
    'Store': "a table class's rows and the stamp of their last structural change",
    'Table': "a table class's value columns, row anchors, column stamps and hold records",
    'OneRow': 'the table view of a non-loop category',
    'ComputedColumn': 'a shared column crysta published',
    'EditRecord': "a project's editor record",
    'GeometrySource': 'what a stored geometry was computed from',
    'EditLog': "a project's handle on its editor record",
    'ProjectLink': 'the revocable record through which nested collections reach their project',
    'ProjectAnchor': "a project's own link record, made by every constructor and cleared on destruction",
    'ProjectTail': "a project's last member, which links its collections after a build or an assignment",
    'ComputedSource': "what an experiment's computed categories were computed from",
    'ViewWindow': 'view state passed to a geometry read, never stored in the model',
    'StructureGeometry': 'the computed structure categories, published whole',
    'WindowGeometry': 'a geometry computed for a view window',
    'IterationRecord': 'a fit report',
    'FitPreamble': 'a fit report',
    'ScanFileRecord': 'a fit report',
    'ScanPreamble': 'a fit report',
    'BankMetric': 'a fit report',
    'FitResultBase': 'a fit report',
    'LeastSquaresFitResult': 'a fit report',
}
# Members of a model class that are not model storage, each with its reason.
NOT_STORAGE = {
    'Structure::geometry_source': 'what the stored geometry was computed from',
    'ExperimentBase::computed_source': 'what the computed categories were computed from',
    'Project::edits_': "the project's editor record",
    'Project::tail_': "the project's last member, which links its collections to its record",
}
# Member types that are a part of a table, not a cell of it.
PARTS = {
    'detail::RowLink': "the row's link to its collection",
    'detail::Epoch': "the row's identity as a calculation input",
    'detail::CategoryRow': "the row token of the object's non-loop categories",
    'detail::DataSource': "a handed-out object's link to its experiment",
}

# Where a loop table's value storage is declared: the table's member, the tuple it is, and the
# value column of each kind of cell.
TABLE_COLUMNS = re.compile(r'using Columns = detail::RowColumns<T>;\s*\n\s*Columns columns;')
ROW_COLUMNS = re.compile(
    r'using RowColumns =\s*typename ColumnsFor<[^;]*crysta::RowSchema<Row>::fields[^;]*>::type;'
)
COLUMNS_FOR = re.compile(
    r'std::tuple<typename FieldColumns<typename MemberField<Members>::type>::type\.\.\.>'
)
FIELD_COLUMNS = re.compile(r'struct FieldColumns<([^{};]+)> \{\s*using type = ([^;]+);\s*\};')
COLUMN_VALUE = re.compile(r'struct ColumnValue<(\w+)> \{\s*using type = ([^;]+);\s*\};')
VALUE_COLUMN = re.compile(r'^crysta::Column<.+>$')

COMMENT_OR_STRING = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)
CLASS_HEAD = re.compile(
    r'^(?:template\s*<[^\n]*>\s*\n)?(class|struct)\s+(\w+)(?:\s+final)?\s*'
    r'(?::(?!:)\s*([^{;]*))?\{',
    re.MULTILINE,
)
# A class defined inside a class: its head is indented.
NESTED_HEAD = re.compile(
    r'^[ \t]+(?:template\s*<[^\n]*>\s*\n[ \t]+)?(class|struct)\s+(\w+)(?:\s+final)?\s*'
    r'(?::(?!:)\s*([^{;]*))?\{',
    re.MULTILINE,
)
SCHEMA = re.compile(
    r'^struct (RowSchema<(?:edi::)?(\w+)>|\w+Category) \{\n(.*?)\n\};', re.MULTILINE | re.DOTALL
)
ACCESS_LABEL = re.compile(r'\s*(public|private|protected)\s*:(?!:)')
# A tag is read from inside a string literal only: `"values"_a.none()` spells no category.
LITERAL = re.compile(r'"((?:\\.|[^"\\\n])*)"')
FILE_TAG = re.compile(r'(_[A-Za-z][A-Za-z_0-9]*)\.')
CIF_TAG = re.compile(r'(_[A-Za-z][A-Za-z0-9_-]*)')
VIEW = re.compile(r'^(?:ItemKey|Parameter|detail::WrittenText|detail::Written<.+>)$')
AGGREGATE = re.compile(
    r'^detail::Written<std::(?:vector<std::pair<.+>>|map<.+>|vector<std::string>'
    r'|vector<std::vector<std::string>>)>$'
)
# A whole column of a data table: a shared computed buffer, or a measured column, whose values a
# recording cell holds in place.
COLUMN = re.compile(
    r'^(?:ComputedColumn<.+>|detail::Written<std::vector<double>>'
    r'|detail::Written<std::optional<std::vector<double>>>)$'
)
CONTAINER = re.compile(r'\bstd::(?:vector|deque|list|map|set|unordered_map|unordered_set)\b')
SCALAR = re.compile(
    r'^(?:std::optional<)?(?:std::string|double|int|bool|\w+Enum)>?$|^std::optional<Parameter>$'
)


def source(path: Path) -> str:
    """Return C++ source without comments, keeping its string literals and line numbers."""

    def keep(match: re.Match) -> str:
        text = match.group(0)
        return text if text.startswith('"') else '\n' * text.count('\n')

    return COMMENT_OR_STRING.sub(keep, path.read_text(encoding='utf-8'))


def declarations(body: str, *, default_public: bool) -> Iterator[tuple[bool, str]]:
    """Yield (public, declaration) for each member declaration at class scope."""
    public, depth, current, index = default_public, 0, '', 0
    while index < len(body):
        char = body[index]
        access = ACCESS_LABEL.match(body, index) if depth == 0 and not current.strip() else None
        if access:
            public = access.group(1) == 'public'
            index = access.end()
            continue
        if char == '{':
            current += '{' if depth == 0 else ''
            depth += 1
        elif char == '}':
            depth -= 1
            # A function body ends its declaration; a brace initialiser (`x{...};`) does not.
            if depth == 0 and not body[index + 1 :].lstrip().startswith((';', ',')):
                yield public, current.strip() + '}'
                current = ''
            elif depth == 0:
                current += '}'
        elif depth == 0 and char == ';':
            yield public, current.strip()
            current = ''
        elif depth == 0:
            current += char
        index += 1


def data_members(declaration: str) -> list[tuple[str, str]]:
    """Return (name, type) for each data member one declaration declares, or nothing."""
    text = re.sub(r'\[\[[^\]]*\]\]', '', declaration).strip()
    head = re.sub(r'^template\s*<[^>]*>\s*', '', text)
    skipped = ('using ', 'friend ', 'static ', 'typedef ', 'enum ', 'struct ', 'class ', '{')
    if not head or head.startswith(skipped) or head.startswith('requires'):
        return []
    plain = re.sub(r'\{[^{}]*\}', '', head)  # brace initialisers
    if '(' in plain.split('=')[0] or 'operator' in plain:
        return []  # a function
    pieces, depth, current = [], 0, ''
    for char in plain:
        depth += {'<': 1, '>': -1}.get(char, 0)
        if char == ',' and depth == 0:
            pieces.append(current)
            current = ''
        else:
            current += char
    pieces.append(current)
    first = re.match(r'(.+?)\s*\b(\w+)\s*(?:=.*)?$', pieces[0].strip(), re.DOTALL)
    if not first:
        return []
    kind = re.sub(r'\s+', ' ', first.group(1)).strip()
    names = [first.group(2)] + [re.match(r'\s*(\w+)', piece).group(1) for piece in pieces[1:]]
    return [(name, kind) for name in names]


def record(found: dict[str, dict], head: re.Match, text: str) -> None:
    """Record the class at `head` and every class defined inside it, each under its own name."""
    depth, index = 1, head.end()
    while depth and index < len(text):
        depth += {'{': 1, '}': -1}.get(text[index], 0)
        index += 1
    body = text[head.end() : index - 1]
    bases = [
        re.sub(r'<.*', '', b.split()[-1]).split('::')[-1]
        for b in (head.group(3) or '').split(',')
        if b.strip()
    ]
    # A census row names a member by its class, so two classes of one name are refused (`defined`).
    entry = found.setdefault(head.group(2), {'bases': bases, 'members': [], 'defined': 0})
    entry['defined'] += 1
    for _, decl in declarations(body, default_public=head.group(1) == 'struct'):
        for name, kind in data_members(decl):
            entry['members'].append({'name': name, 'type': kind})
    for nested in NESTED_HEAD.finditer(body):
        before = body[: nested.start()]
        if before.count('{') == before.count('}'):  # at the class's own scope, not in a function
            record(found, nested, body)


def classes(text: str) -> dict[str, dict]:
    """Map each class, nested ones included, to its bases and data members, in their order."""
    found: dict[str, dict] = {}
    for head in CLASS_HEAD.finditer(text):
        record(found, head, text)
    return found


def strings(text: str) -> list[str]:
    """Return the contents of every string literal in `text`, in order."""
    return [s[1:-1] for s in re.findall(r'"(?:\\.|[^"\\\n])*"', text)]


def schemas(text: str) -> list[dict]:
    """Return every schema the model declares, in declaration order."""
    found = []
    for match in SCHEMA.finditer(text):
        body = match.group(3)
        name = re.search(r'\bname\s*=\s*("(?:\\.|[^"\\\n])*")', body)
        columns = re.search(r'\b(?:columns|fields)\s*=\s*std::tuple\{(.*?)\};', body, re.DOTALL)
        lists = {
            key: re.search(rf'\b{key}\{{(.*?)\}};', body, re.DOTALL)
            for key in ('items', 'legacy', 'cif', 'variants')
        }
        derived = re.search(r'\bderived\s*=\s*((?:"(?:\\.|[^"\\\n])*"\s*)+);', body)
        owner = re.search(r'\busing Owner = ([\w:]+);', body)
        found.append({
            'schema': match.group(1),
            'row': match.group(2),
            'name': strings(name.group(1))[0] if name else None,
            'owner': owner.group(1).split('::')[-1] if owner else None,
            'columns': [
                (cls.split('::')[-1], member)
                for cls, member in re.findall(r'&([\w:]+)::(\w+)', columns.group(1))
            ]
            if columns
            else [],
            **{key: strings(found_.group(1)) if found_ else [] for key, found_ in lists.items()},
            'derived': ''.join(strings(derived.group(1))) if derived else None,
        })
    return found


class Census:
    """The census of one tree, with the problems found while reading it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: list[str] = []
        text = source(root / MODEL)
        self.known = classes(text)
        self.schemas = schemas(text)
        self.text = text
        self.named: dict[tuple[str, str], str] = {}
        self.model = {
            name: record
            for name, record in self.known.items()
            if name not in NOT_MODEL and not name.endswith('Category') and record['members']
        }

    def member(self, cls: str, name: str) -> tuple[str, dict] | None:
        """Return the class that declares `cls::name` (itself or a base), and the member."""
        record = self.known.get(cls)
        if record is None:
            return None
        for member in record['members']:
            if member['name'] == name:
                return cls, member
        for base in record['bases']:
            found = self.member(base, name)
            if found:
                return found
        return None

    def table_stores_columns(self) -> bool:
        """Whether the loop table class holds the value columns of its schema's fields."""
        return all(p.search(self.text) for p in (TABLE_COLUMNS, ROW_COLUMNS, COLUMNS_FOR))

    def storage(self, cell: str) -> list[str] | None:
        """Return the value columns that store a loop cell of type `cell`, read from the code."""
        fields = {k.strip(): v.strip() for k, v in FIELD_COLUMNS.findall(self.text)}
        values = dict(COLUMN_VALUE.findall(self.text))
        written = re.match(r'^detail::Written<(.+)>$', cell)
        if written:
            kind = fields.get('Written<U>', '')
            value = values.get(written.group(1), written.group(1)).strip()
            kind = kind.replace('typename ColumnValue<U>::type', value)
        else:
            kind = fields.get(cell.removeprefix('detail::'), '')
        bundle = self.known.get(kind)
        if bundle is not None:  # a bundle of columns: one value column for each of its members
            return [f'{m["name"]}: {m["type"]}' for m in bundle['members']]
        return [kind] if kind else None

    def stored(self, label: str, schema: dict, columns: list[dict]) -> bool:
        """Record a loop schema's value columns; False, with the problem recorded, if none."""
        if not self.table_stores_columns():
            self.problems.append(
                f'{label} ({schema["name"]}): the loop table class does not hold '
                'detail::RowColumns<T>, the value columns of its schema'
            )
            return False
        for column in columns:
            stored = self.storage(column['type'])
            kinds = [s.split(': ')[-1] for s in stored or []]
            if not kinds or not all(VALUE_COLUMN.match(kind) for kind in kinds):
                self.problems.append(
                    f'{label}: {column["member"]} ({column["type"]}) is not stored in value '
                    f'columns: {stored}'
                )
                return False
            column['storage'] = stored
        return True

    @staticmethod
    def form(schema: dict, types: list[str]) -> str | None:
        """Return the storage form of a schema's columns, or None when it is not a table."""
        if schema['row']:
            return 'loop' if all(VIEW.match(t) and not AGGREGATE.match(t) for t in types) else None
        if types and all(COLUMN.match(t) for t in types):
            return 'columns'
        if types and all(AGGREGATE.match(t) for t in types):
            return 'aggregate'
        in_place = all(
            (VIEW.match(t) and not AGGREGATE.match(t)) or SCALAR.match(t) for t in types
        )
        if schema['owner'] and types and in_place:
            return 'one row'
        value = all(not CONTAINER.search(t) and not VIEW.match(t) for t in types)
        if types and not schema['owner'] and value:
            return 'computed value'
        return None

    def category(self, schema: dict) -> dict | None:
        """Return the census entry of one schema, or None with its problem recorded."""
        label = schema['schema']
        if schema['name'] is None:
            self.problems.append(f'{label} names no category')
            return None
        if schema['derived'] is not None:
            entry = {'name': schema['name'], 'form': 'derived', 'why': schema['derived']}
            return entry | ({'cif': schema['cif']} if schema['cif'] else {})
        if len(schema['items']) != len(schema['columns']):
            self.problems.append(f'{label}: one items entry per column')
            return None
        columns = []
        for (cls, name), items in zip(schema['columns'], schema['items'], strict=True):
            resolved = self.member(cls, name)
            if resolved is None:
                self.problems.append(f'{label} names {cls}::{name}, which is not a member')
                continue
            declared_in, member = resolved
            if (declared_in, name) in self.named:
                self.problems.append(
                    f'{declared_in}::{name} is named by two schemas: '
                    f'{self.named[declared_in, name]} and {schema["name"]}'
                )
            self.named[declared_in, name] = schema['name']
            columns.append({
                'member': f'{declared_in}::{name}',
                'type': member['type'],
                'items': items.split(),
            })
        form = self.form(schema, [column['type'] for column in columns])
        if form is None:
            self.problems.append(
                f'{label} ({schema["name"]}): its storage is not a table — columns '
                + ', '.join(f'{c["member"]} ({c["type"]})' for c in columns)
            )
        if form is None or (form == 'loop' and not self.stored(label, schema, columns)):
            return None
        entry = {'name': schema['name'], 'form': form, 'columns': columns}
        entry.update({
            key: schema[key]
            for key in ('row', 'owner', 'legacy', 'cif', 'variants')
            if schema[key]
        })
        return entry

    def categories(self) -> list[dict]:
        """Return the census entry of every schema, in declaration order."""
        found = [entry for entry in map(self.category, self.schemas) if entry is not None]
        names = [c['name'] for c in found]
        for name in sorted({n for n in names if names.count(n) > 1}):
            if not self.type_switched([c for c in found if c['name'] == name]):
                self.problems.append(f'category {name} has more than one schema')
        return found

    @staticmethod
    def type_switched(entries: list[dict]) -> bool:
        """Whether several schemas of one category are its selector and its alternatives."""
        selectors = [
            e
            for e in entries
            if e['form'] == 'one row' and any('type' in c['items'] for c in e['columns'])
        ]
        alternatives = [e for e in entries if e['form'] == 'loop']
        if len(selectors) != 1 or len(selectors) + len(alternatives) != len(entries):
            return False
        if selectors[0].get('variants') or any(not e.get('variants') for e in alternatives):
            return False
        tokens = [token for e in alternatives for token in e['variants']]
        return len(tokens) == len(set(tokens))

    def holds(self, kind: str, seen: frozenset = frozenset()) -> list[str]:
        """Return the categories a member of type `kind` holds, through its classes."""
        table = re.match(r'^ItemVec<(\w+)>$', kind)
        if table:
            return [s['name'] for s in self.schemas if s['row'] == table.group(1) and s['name']]
        inner = re.sub(r'\b(?:std::optional|detail::Written)<', '', kind).rstrip('>').strip()
        record = self.known.get(inner)
        if record is None or inner in seen or inner == 'Parameter':
            return []
        held: list[str] = []
        for member in record['members']:
            named = self.named.get((inner, member['name']))
            for name in [named] if named else self.holds(member['type'], seen | {inner}):
                if name not in held:
                    held.append(name)
        return held

    def members(self) -> list[dict]:
        """Return every data member of every class of the model with what it belongs to."""
        rows = []
        for cls, record in self.known.items():
            if cls.endswith('Category') and not record['members']:
                continue
            for member in record['members']:
                label = f'{cls}::{member["name"]}'
                row = {'member': label, 'type': member['type']}
                named = self.named.get((cls, member['name']))
                held = [] if named else self.holds(member['type'])
                if cls in NOT_MODEL:
                    row['not_storage'] = NOT_MODEL[cls]
                elif named:
                    row['category'] = named
                elif member['type'] in PARTS:
                    row['part'] = PARTS[member['type']]
                elif held:
                    row['holds'] = held
                elif label in NOT_STORAGE:
                    row['not_storage'] = NOT_STORAGE[label]
                else:
                    self.problems.append(
                        f'{label} ({member["type"]}) is a model field no schema names'
                    )
                    continue
                rows.append(row)
        listed = {r['member'] for r in rows}
        for label in sorted(set(NOT_STORAGE) - listed):
            self.problems.append(f'NOT_STORAGE lists {label}, which is not a model field')
        for name in sorted(set(NOT_MODEL) - set(self.known)):
            self.problems.append(f'NOT_MODEL lists {name}, which model.hpp does not define')
        return rows

    def name_problems(self) -> None:
        """Record a name that two classes of the model header share: their members share rows."""
        for name, record in self.known.items():
            if record['defined'] > 1:
                self.problems.append(
                    f'{name} names {record["defined"]} classes of model.hpp: a class defined '
                    'inside a class needs a name of its own, or its members share census rows'
                )

    def parameter_problems(self) -> None:
        """Record a parameter attribute that is not a cell view, as its value is."""
        cells = {'value', 'uncertainty', 'free', 'start_value', 'start_uncertainty'}
        for member in self.known.get('Parameter', {'members': []})['members']:
            if member['name'] in cells and not VIEW.match(member['type']):
                self.problems.append(
                    f'Parameter::{member["name"]} ({member["type"]}) is not a cell view'
                )

    def tags(self) -> list[tuple[bool, str, str]]:
        """Return (dotted, name, where) for each file tag the sources spell, first use only."""
        seen: dict[tuple[bool, str], str] = {}
        for top in TAG_SOURCES:
            for path in sorted((self.root / top).rglob('*')):
                if path.suffix not in {'.cpp', '.hpp'}:
                    continue
                where = path.relative_to(self.root).as_posix()
                text = source(path)
                cif_source = where.startswith(CIF_SOURCES) and where != MODEL  # not the schemas
                for literal in LITERAL.finditer(text):
                    dotted = FILE_TAG.match(literal.group(1))
                    plain = CIF_TAG.fullmatch(literal.group(1)) if cif_source else None
                    if dotted or plain:
                        line = text.count('\n', 0, literal.start()) + 1
                        name = (dotted or plain).group(1)
                        seen.setdefault((bool(dotted), name), f'{where}:{line}')
        return [(dotted, name, where) for (dotted, name), where in seen.items()]

    def cif_tags(self, categories: list[dict]) -> dict[str, str]:
        """Return the category of each CIF tag a schema lists."""
        cif: dict[str, str] = {}
        for category in categories:
            for tag in category.get('cif', []):
                if cif.setdefault(tag, category['name']) != category['name']:
                    self.problems.append(f'CIF tag {tag} is listed by two schemas')
        return cif

    def file_categories(self, categories: list[dict]) -> dict[str, list[str]]:
        """Return each category a file tag in the sources spells, with its schemas."""
        known: dict[str, list[str]] = {c['name']: [c['name']] for c in categories}
        for category in categories:
            for old in category.get('legacy', []):
                known.setdefault(old, []).append(category['name'])
        cif = self.cif_tags(categories)
        found: dict[str, list[str]] = {}
        unspelled = set(cif)
        for dotted, name, where in self.tags():
            if dotted and name in known:
                found[name] = known[name]
            elif dotted:
                self.problems.append(f'file category {name} has no schema ({where})')
            elif name in cif:
                unspelled.discard(name)
                found[cif[name]] = [cif[name]]
            elif name not in known and name not in TAG_FRAGMENTS:
                self.problems.append(f'CIF tag {name} is in no schema ({where})')
        for tag in sorted(unspelled):
            self.problems.append(f'{cif[tag]} lists the CIF tag {tag}, which no source spells')
        return {name: found[name] for name in sorted(found)}

    def one_row_problems(self, categories: list[dict]) -> None:
        """Each non-loop category has its row token and its instantiated table view."""
        instantiated = set(
            re.findall(
                r'^template class OneRow<(\w+)>;', source(self.root / INSTANTIATIONS), re.MULTILINE
            )
        )
        # A type-switched category's name is shared with its loop schemas: the one-row view is
        # the non-loop schema's.
        struct_of = {s['name']: s['schema'] for s in self.schemas if not s['row']}
        for category in categories:
            if category['form'] != 'one row':
                continue
            owner = category['owner']
            members = self.known.get(owner, {'members': []})['members']
            if not any(m['type'] == 'detail::CategoryRow' for m in members):
                self.problems.append(f'{category["name"]}: its owner {owner} has no row token')
            foreign = [
                c['member']
                for c in category['columns']
                if self.member(owner, c['member'].split('::')[1]) is None
            ]
            if foreign:
                self.problems.append(
                    f'{category["name"]}: {foreign} are not cells of its owner {owner}'
                )
            if struct_of[category['name']] not in instantiated:
                self.problems.append(
                    f'{category["name"]}: {INSTANTIATIONS} does not instantiate '
                    f'OneRow<{struct_of[category["name"]]}>'
                )

    def build(self) -> dict:
        """Return the census, recording every problem found on the way."""
        categories = self.categories()
        members = self.members()
        files = self.file_categories(categories)
        self.one_row_problems(categories)
        self.parameter_problems()
        self.name_problems()
        return {
            'about': 'Generated by tools/checks/category_census.py from the schemas in '
            'core/include/edi/model.hpp (ADR-0018). Do not edit.',
            'categories': categories,
            'members': members,
            'file_categories': files,
        }


def main(argv: list[str] | None = None) -> int:
    """Generate the census; check it, or write it."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    parser.add_argument('--write', action='store_true', help='regenerate the committed census')
    args = parser.parse_args(argv)
    census = Census(args.root)
    built = census.build()
    text = json.dumps(built, indent=2, ensure_ascii=False) + '\n'
    path = args.root / CENSUS
    if args.write and not census.problems:
        path.write_text(text, encoding='utf-8')
    elif not path.is_file() or path.read_text(encoding='utf-8') != text:
        census.problems.append(f'{CENSUS} is not the generated census (run with --write)')
    for problem in census.problems:
        sys.stdout.write(f'category_census: {problem}\n')
    if census.problems:
        return 1
    forms: dict[str, int] = {}
    for category in built['categories']:
        forms[category['form']] = forms.get(category['form'], 0) + 1
    sys.stdout.write(
        f'category_census: {len(built["categories"])} categories ('
        + ', '.join(f'{count} {form}' for form, count in sorted(forms.items()))
        + f'), {len(built["members"])} model members, '
        f'{len(built["file_categories"])} file categories; every one has its schema\n'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
