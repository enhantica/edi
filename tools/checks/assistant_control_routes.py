"""Check that every control the assistant reaches lies where its route says.

The routes are app/src/assistant_control_routes.hpp: each control's page, sidebar tab,
group and table. The place of a control is read from the app's QML, not from its name: a
page (app/qml/Pages/*/*Page.qml) lists its groups in the component of each sidebar tab,
either a named group (`group.experiments`) or one group a category (CategoryGroup), whose
content is the page's component for that category, in the tab the app keeps that category
on (app/src/category_list_model.cpp). What a group's file declares, or a component it
uses declares, lies in that group; what a dialog holds lies in no group.

The ids are the control names in the assistant's input steps
(app/src/assistant_view_model.cpp), and every name declared on a page that a route covers.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('app/src/assistant_view_model.cpp')
ROUTES = Path('app/src/assistant_control_routes.hpp')
CATEGORIES = Path('app/src/category_list_model.cpp')
QML = Path('app/qml')
TABS = {'basicItem': 'basic', 'extrasItem': 'extras'}
TIERS = {'basic': 'Basic', 'extras': 'Extras'}
# Strings in the same expressions that name no control: run state, readers,
# workflow and group lookups.
NOT_CONTROLS = ('codex.', 'measurement.', 'workflow.', 'group.')
# Ids the input steps use: a Kind's target, or a target an operation chooses.
STEP = re.compile(
    r'(?:Kind::(?:Navigate|FileLoadCue|Choose|Text|FormText)\s*,\s*|(?:target|name)\s*=\s*|[?:]\s*)'
    r'(?:QString(?:Literal)?\()?"([a-zA-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.%]*)"'
)
# Ids the source looks a route up by.
LOOKUP = re.compile(r'\bu"([a-zA-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.]*)"')
# A page, sidebar tab or tier written in the source is a second authority beside the routes.
WRITTEN = re.compile(
    r'"(?:appBar\.tab\.(?:project|structure|experiment|analysis)|sideBar\.tab\.(?:basic|extras)'
    r'|workflow\.(?:project|structure|experiment|analysis)\.manualSidebar)"'
    r'|tier\.toString\(\)\s*[!=]=\s*"(?:Basic|Extras)"'
)
NAME = re.compile(r'(?:objectName|editorObjectName)\s*[:=]\s*("[^"\n]+"|`[^`\n]+`)')
USED = re.compile(r'(?:[A-Z]\w*\.)?([A-Z]\w*)\s*$')


@dataclass(frozen=True)
class Place:
    """A page, its sidebar tab and the group there; no group for a dialog over it."""

    page: str
    tab: str
    group: str

    def described(self) -> str:
        """The place in words."""
        return f'{self.page}, {self.tab}, {self.group or "no group"}'


@dataclass
class Block:
    """An object of a QML file: its type, what it declares itself and its children."""

    type: str = ''
    prefix: str = ''
    text: str = ''
    names: list[str] = field(default_factory=list)
    children: list[Block] = field(default_factory=list)

    def walk(self) -> Iterator[Block]:
        """The block and all its descendants."""
        yield self
        for child in self.children:
            yield from child.walk()


def without_comments(text: str) -> str:
    return re.sub(
        r'("(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`[^`]*`)|//[^\n]*|/\*.*?\*/',
        lambda match: match.group(1) or ' ',
        text,
        flags=re.DOTALL,
    )


def parse(text: str) -> Block:
    """The objects of a QML file, nested as written; a brace inside a string is no block."""
    root = Block()
    stack = [root]
    body = ['']
    for piece in re.findall(
        r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`[^`]*`|[{}]|[^{}"\'`]+|.',
        without_comments(text),
        flags=re.DOTALL,
    ):
        if piece == '{':
            used = USED.search(body[-1])
            prefix = re.search(r'(\w+)\s*:\s*(?:[A-Z]\w*\.)?[A-Z]\w*\s*$', body[-1])
            block = Block(
                type=used.group(1) if used else '', prefix=prefix.group(1) if prefix else ''
            )
            stack[-1].children.append(block)
            stack.append(block)
            body.append('')
        elif piece == '}':
            if len(stack) > 1:
                stack.pop().text = body.pop()
        else:
            body[-1] += piece
    root.text = body[0]
    for block in root.walk():
        block.names = [
            re.sub(r'\$\{[^}]*\}', '%', name[1:-1]) for name in NAME.findall(block.text)
        ]
        # A grid of a category's fields names each `<prefix>.<item>`.
        if block.type == 'ParameterGrid':
            block.names += [
                f'{prefix}.%' for prefix in re.findall(r'\bprefix\s*:\s*"([^"]+)"', block.text)
            ]
    return root


class Tree:
    """The app's QML: each component's objects, and where each page puts what."""

    def __init__(self, root: Path) -> None:
        self.files = {}
        for path in sorted((root / QML).rglob('*.qml')):
            self.files[path.stem] = parse(path.read_text(encoding='utf-8'))
        self.tiers, self.parts = category_tiers((root / CATEGORIES).read_text(encoding='utf-8'))
        self.places: dict[str, set[Place]] = {}
        self.names = {
            name for tree in self.files.values() for block in tree.walk() for name in block.names
        }
        for path in sorted((root / QML / 'Pages').rglob('*Page.qml')):
            self.page(path)

    def page(self, path: Path) -> None:
        tree = self.files[path.stem]
        top = next((child for child in tree.children if child.type == 'WorkflowPage'), None)
        if top is None:
            return
        page = re.search(r'\bpageName\s*:\s*"([^"]+)"', top.text).group(1)
        components = {}
        for child in top.children:
            named = re.search(r'\bid\s*:\s*(\w+)', child.text)
            if child.type == 'Component' and named:
                components[named.group(1)] = child
        maps = content_maps(path.read_text(encoding='utf-8'))
        for item in top.children:
            if item.prefix in TABS:
                for child in item.children:
                    self.tab(page, TABS[item.prefix], child, components, maps)

    def tab(self, page: str, tab: str, block: Block, components: dict, maps: dict) -> None:
        for child in block.children:
            if child.type == 'CategoryGroup':
                shown = re.search(r'\bshownTier\s*:\s*"(\w+)"', child.text)
                used = re.search(r'\bcontents\s*:\s*page\.(\w+)', child.text)
                if shown is None or shown.group(1) != TIERS[tab] or used is None:
                    continue
                for category, contents in maps[used.group(1)].items():
                    tier = self.tiers.get(category, 'Extras')
                    if tier != TIERS[tab] and not (tab == 'extras' and category in self.parts):
                        continue
                    for component in contents:
                        self.put(components[component], Place(page, tab, f'group.{category}'), ())
            elif child.type in self.files:
                group = next(iter(self.files[child.type].children), Block())
                named = [name for name in group.names if name.startswith('group.')]
                if named:
                    self.put(group, Place(page, tab, named[0]), (child.type,))
            else:
                self.tab(page, tab, child, components, maps)

    def put(self, block: Block, place: Place, seen: tuple[str, ...]) -> None:
        if block.type.endswith('Dialog'):
            place = Place(place.page, place.tab, '')
        for name in block.names:
            self.places.setdefault(name, set()).add(place)
        if block.type in self.files and block.type not in seen:
            for child in self.files[block.type].children:
                self.put(child, place, (*seen, block.type))
        for child in block.children:
            self.put(child, place, seen)


def content_maps(text: str) -> dict[str, dict[str, list[str]]]:
    """Each of a page's maps from category to content, and what extends another."""
    maps: dict[str, dict[str, list[str]]] = {}
    for match in re.finditer(
        r'readonly property var (\w+): (?:\(\{|Object\.assign\(\{\}, (\w+), \{)(.*?)\}\)',
        without_comments(text),
        flags=re.DOTALL,
    ):
        name, base, body = match.groups()
        own = dict(maps.get(base, {}))
        for category, value in re.findall(r'"(\w+)"\s*:\s*([^,"]+)', body):
            own[category] = re.findall(r'\b(\w+Content)\b', value)
        maps[name] = own
    return maps


def category_tiers(text: str) -> tuple[dict[str, str], set[str]]:
    """The tab of each category, and the categories with a part on the other tab."""
    tiers, parts = {}, set()
    for category, tier, part in re.findall(
        r'\{QStringLiteral\("(\w+)"\), \{T::(Basic|Extras)(?:, (true|false))?', text
    ):
        tiers[category] = tier
        if part == 'true':
            parts.add(category)
    return tiers, parts


def routes(text: str) -> list[tuple[str, str, str, str, str]]:
    return re.findall(r'\{"([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)"\}', text)


def route_of(name: str, table: list) -> tuple | None:
    best = None
    for row in table:
        prefix = row[0]
        inside = (
            name == prefix
            or name.startswith(f'{prefix}.')
            or (prefix.endswith('.') and name.startswith(prefix))
        )
        if inside and (best is None or len(prefix) > len(best[0])):
            best = row
    return best


def place_of(route: tuple) -> Place:
    return Place(route[1], route[2], route[3])


def route_problems(table: list, tree: Tree) -> list[str]:
    """What is wrong with the table itself: a place no control has, a table that lies elsewhere."""
    problems = []
    covered: dict[tuple, set[Place]] = {}
    for name, places in tree.places.items():
        route = route_of(name, table)
        if route is not None and route[1]:
            covered.setdefault(route, set()).update(places)
            problems += [
                f'{name}: lies on {place.described()}, '
                f'its route {route[0]} says {place_of(route).described()}'
                for place in sorted(places, key=Place.described)
                # A group's dialog is over the page, outside the group it opens from.
                if place not in {place_of(route), Place(route[1], route[2], '')}
            ]
    for route in table:
        prefix, page, tab, _group, rows = route
        if not page:
            if not any(name == prefix or name.startswith(prefix) for name in tree.names):
                problems.append(f'{prefix}: no QML file declares it')
            continue
        for name in (f'appBar.tab.{page}', f'sideBar.tab.{tab}'):
            if name not in tree.names:
                problems.append(f'{prefix}: {name} is in no QML file')
        if route not in covered:
            problems.append(f'{prefix}: no control on a page has this route')
        if rows and place_of(route) not in tree.places.get(rows, set()):
            problems.append(f'{prefix}: table {rows} is not on {place_of(route).described()}')
    return problems


def control_problems(source: str, table: list, tree: Tree) -> tuple[int, list[str]]:
    """What is wrong with the ids the assistant uses."""
    problems = [
        f'{SOURCE.name}: {found} is not read from a route' for found in WRITTEN.findall(source)
    ]
    ids = sorted(name for name in set(STEP.findall(source)) if not name.startswith(NOT_CONTROLS))
    for name in ids:
        route = route_of(name, table)
        if route is None:
            problems.append(f'{name}: no route')
        elif route[1] and not name.endswith('.'):
            control = re.sub(r'%\d', '%', name)
            places = tree.places.get(control) or tree.places.get(re.sub(r'\.0$', '.%', control))
            if not places:
                problems.append(f'{name}: no page declares it')
            elif places != {place_of(route)}:
                where = '; '.join(sorted(map(Place.described, places)))
                problems.append(
                    f'{name}: lies on {where}, its route says {place_of(route).described()}'
                )
    problems += [
        f'{name}: looked up, but has no route'
        for name in set(LOOKUP.findall(source))
        if route_of(name, table) is None
    ]
    return len(ids), problems


def check(root: Path, table_text: str | None = None) -> tuple[int, int, list[str]]:
    table = routes(table_text or (root / ROUTES).read_text(encoding='utf-8'))
    tree = Tree(root)
    count, problems = control_problems((root / SOURCE).read_text(encoding='utf-8'), table, tree)
    return count, len(table), sorted({*problems, *route_problems(table, tree)})


def main() -> int:
    count, rows, problems = check(ROOT)
    for problem in problems:
        print(problem)
    print(f'{count} control ids, {rows} routes, {len(problems)} problem(s)')
    return 1 if problems or not count or not rows else 0


if __name__ == '__main__':
    sys.exit(main())
