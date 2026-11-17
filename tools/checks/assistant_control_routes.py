"""Check that every control id the assistant reaches has a route whose group and table exist.

The ids are the control names in the assistant's input steps
(app/src/assistant_view_model.cpp); the routes are app/src/assistant_control_routes.hpp.
A group is a named group or a category group (`group.<category>`, made by CategoryGroup
from the category's id); a table is an objectName in the app's QML.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'app/src/assistant_view_model.cpp'
ROUTES = ROOT / 'app/src/assistant_control_routes.hpp'
QML = ROOT / 'app/qml'
CATEGORY_GROUPS = {
    'group.space_group',
    'group.atom_site',
    'group.atom_site_aniso',
    'group.linked_structure',
    'group.excluded_region',
    'group.instrument',
    'group.peak',
    'group.background',
    'group.extinction',
    'group.absorption',
    'group.joint_fit',
}
# Strings in the same expressions that name no control: run state, readers,
# workflow and group lookups.
NOT_CONTROLS = ('codex.', 'measurement.', 'workflow.', 'group.')
# Ids the input steps use: a Kind's target, or a target an operation chooses.
STEP = re.compile(
    r'(?:Kind::(?:Navigate|FileLoadCue|Choose|Text|FormText)\s*,\s*|(?:target|name)\s*=\s*|[?:]\s*)'
    r'(?:QString(?:Literal)?\()?"([a-zA-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.%]*)"'
)


def routes() -> list[tuple[str, str, str, str]]:
    text = ROUTES.read_text()
    return [
        (prefix, page, group, table)
        for prefix, page, group, table in re.findall(
            r'\{"([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)"\}', text
        )
    ]


def route_of(name: str, table: list) -> tuple | None:
    best = None
    for row in table:
        prefix = row[0]
        if (name == prefix or (prefix.endswith('.') and name.startswith(prefix))) and (
            best is None or len(prefix) > len(best[0])
        ):
            best = row
    return best


def qml_names() -> set[str]:
    names = set()
    for path in QML.rglob('*.qml'):
        text = path.read_text()
        names.update(re.findall(r'(?:objectName|editorObjectName)\s*[:=]\s*"([^"]+)"', text))
        # A templated name stands for every row: experiments.loadData.${row.index}
        # is experiments.loadData.%.
        names.update(
            re.sub(r'\$\{[^}]*\}', '%', name)
            for name in re.findall(r'objectName:\s*`([^`]+)`', text)
        )
    return names


def main() -> int:
    table = routes()
    ids = sorted(
        name for name in set(STEP.findall(SOURCE.read_text())) if not name.startswith(NOT_CONTROLS)
    )
    names = qml_names()
    problems = []
    for name in ids:
        if name.startswith(('appBar.tab.', 'sideBar.tab.')) and route_of(name, table):
            continue
        route = route_of(name, table)
        if route is None:
            problems.append(f'{name}: no route')
            continue
        _prefix, _page, group, rows = route
        if group and group not in names and group not in CATEGORY_GROUPS:
            problems.append(f'{name}: group {group} is in no QML file')
        if rows and rows not in names:
            problems.append(f'{name}: table {rows} is in no QML file')
        control = re.sub(r'%\d', '%', name)
        row_form = re.sub(r'\.0$', '.%', control)
        if not name.endswith('.') and control not in names and row_form not in names:
            problems.append(f'{name}: control is in no QML file')
    for problem in problems:
        print(problem)
    print(f'{len(ids)} control ids, {len(table)} routes, {len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
