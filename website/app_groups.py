# SPDX-License-Identifier: BSD-3-Clause
"""The app's parameter-table categories for the parameters a tutorial stage frees.

The owner's rule (records 7101f0fd9 and b8df97176, 2026-11-09): a stage frees a group in one
action, named as the app's category selector shows it, never as a list of parameters. Where a stage
frees only part of a category, the part is named once, by one word typed in the name filter. The
app page and the app replay plan both take their groups from here, so the sentence and the replay
cannot disagree.

The categories and their subsets are the parameter table's (app/src/parameter_table_model.cpp,
`matches_group`); the titles are crysta's dictionary's, as the selector shows them.
"""

from __future__ import annotations

import functools
import html
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# A Python attribute of a structure or an experiment and the dictionary category it holds.
OWNERS = {
    'cell': 'cell',
    'atom_sites': 'atom_site',
    'atom_site_aniso': 'atom_site_aniso',
    'atom_site_moment': 'atom_site_moment',
    'peak': 'peak',
    'instrument': 'instrument',
    'extinction': 'extinction',
    'absorption': 'absorption',
    'linked_structures': 'linked_structure',
    'background': 'background',
    'preferred_orientation': 'preferred_orientation',
}


@dataclass(frozen=True)
class Parameter:
    """One parameter as the table lists it: its block, owner attribute, row (or '') and name."""

    block: str
    owner: str
    row: str
    name: str


# The part of a category its rows, ticked one by one, are: what the app page says in words.
ROWS = 'rows the stage names'


@dataclass(frozen=True)
class Group:
    """One action on a category of one block.

    `word`, when set, is typed in the name filter so the action reaches only part of the category.
    `unword`, when set, is the part set back after the whole category is set: one word, or two
    separated by a space, each typed in the name filter in turn. `part`, when
    set, names in words a part no filter word selects; its `rows` are set one by one.
    """

    title: str
    block: str
    word: str = ''
    unword: str = ''
    part: str = ''
    rows: tuple[Parameter, ...] = ()


def load_case(case: str) -> object:
    """The case's project, which says which parameters each category holds."""
    import easydiffraction as edi  # noqa: PLC0415 - only the stage groups need the package

    return edi.Project.load(str(ROOT / 'docs/user/cli' / case / 'project'))


@functools.cache
def dictionary() -> dict:
    """The parameter dictionary, from crysta's source checkout (rendering needs it)."""
    crysta = Path(os.environ.get('CRYSTA_CONSUMER_SRC', ROOT.parent / 'crysta'))
    return yaml.safe_load((crysta / 'data/dictionary/parameters.yaml').read_text(encoding='utf-8'))


@functools.cache
def _titles() -> dict[str, str]:
    """The selector's category titles, from crysta's dictionary."""
    data = dictionary()
    categories = data.get('categories', data) if isinstance(data, dict) else data
    return {
        entry['id']: (entry.get('loop_title') if entry.get('loop') else None) or entry['title']
        for entry in categories
        if isinstance(entry, dict) and 'id' in entry and 'title' in entry
    }


# The selector's subsets of a category, by name prefix (`matches_group`), in its order.
SUBSETS = {
    'atom_site': (
        (('fract_',), 'Atomic coordinates'),
        (('occupancy',), 'Atomic occupancies'),
        (('adp_',), 'Atomic displacement'),
    ),
    'peak': (
        (('broad_',), 'Peak broadening'),
        (('mixing_',), 'Peak mixing'),
        (('asym_', 'rise_alpha_', 'decay_beta_'), 'Peak asymmetry'),
    ),
}


def category(parameter: Parameter) -> str:
    """The narrowest category the selector offers for this parameter."""
    owner = OWNERS.get(parameter.owner, parameter.owner)
    subset = next(
        (
            title
            for prefixes, title in SUBSETS.get(owner, ())
            if parameter.name.startswith(prefixes)
        ),
        None,
    )
    fixed = {'atom_site_aniso': 'Atomic displacement', 'linked_structure': 'Linked structures'}
    return subset or fixed.get(owner) or _titles().get(owner, owner.replace('_', ' ').capitalize())


def _is_parameter(value: object) -> bool:
    return hasattr(value, 'free') and hasattr(value, 'symmetry_constrained')


# By id, with the project kept: a project freed after its case could leave its id to the next one.
_FITTABLE: dict[int, tuple[object, set, set]] = {}


def _fittable_rows(project: object) -> tuple[set, set]:
    """The parameters the app offers to free, from the report's fittable table (crysta's rule).

    Each as (datablock, category, entry, name), and without the entry for a category of one row.
    """
    cached = _FITTABLE.get(id(project))
    if cached is None or cached[0] is not project:
        page = project.display.parameters.fittable().html
        rows_found = set()
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', page, re.DOTALL):
            cells = [
                html.unescape(re.sub(r'<[^>]+>', '', cell)).strip()
                for cell in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            ]
            if len(cells) >= 5 and cells[0].isdigit():
                rows_found.add(tuple(cells[1:5]))
        cached = (project, rows_found, {(b, c, n) for b, c, _e, n in rows_found})
        _FITTABLE[id(project)] = cached
    return cached[1], cached[2]


def forget(project: object) -> None:
    """Read the fittable parameters again after the project changed."""
    _FITTABLE.pop(id(project), None)


def _fittable(project: object, parameter: Parameter) -> bool:
    exact, loose = _fittable_rows(project)
    category = OWNERS.get(parameter.owner, parameter.owner)
    if parameter.row:
        return (parameter.block, category, parameter.row, parameter.name) in exact
    return (parameter.block, category, parameter.name) in loose


def _row_key(item: object) -> str:
    for attribute in ('label', 'id', 'structure_id', 'name'):
        value = getattr(item, attribute, None)
        if value is not None:
            return str(getattr(value, 'value', value))
    return ''


def rows(project: object, block: str, owner: str) -> list[tuple[Parameter, bool]]:
    """Every parameter of one owner attribute of one block, with whether it can be freed.

    The table lists them all; the app offers to free only the fittable ones.
    """
    blocks = {item.name: item for item in [*project.structures, *project.experiments]}
    holder = getattr(blocks[block], owner, None)
    # A Chebyshev background's terms are its rows, though the table names them under `background`.
    terms = getattr(blocks[block], 'background_terms', None) if owner == 'background' else None
    if terms:
        holder = terms
    if holder is None:
        return []
    items = (
        [('', holder)] if hasattr(holder, '__dict__') and not hasattr(holder, '__len__') else None
    )
    if items is None:
        try:
            items = [(_row_key(item), item) for item in holder]
        except TypeError:
            items = [('', holder)]
    found = []
    for row, item in items:
        for name in dir(item):
            value = getattr(item, name, None) if not name.startswith('_') else None
            if _is_parameter(value):
                found.append((Parameter(block, owner, row, name), False))
    return [(parameter, _fittable(project, parameter)) for parameter, _ in found]


def members(project: object, block: str, owner: str) -> set[Parameter]:
    """Every parameter of one owner attribute of one block that the app lets be freed."""
    return {parameter for parameter, fittable in rows(project, block, owner) if fittable}


def offered(project: object, parameter: Parameter) -> str:
    """The category the selector offers for a parameter.

    A subset only where it narrows its category (the app's `addSubset`), else the category itself.
    """
    title = category(parameter)
    owner = OWNERS.get(parameter.owner, parameter.owner)
    if owner not in SUBSETS or title not in {name for _, name in SUBSETS[owner]}:
        return title
    # The parent counts every row, freeable or not; the atom sites include their tensors.
    owners = ('atom_sites', 'atom_site_aniso') if owner == 'atom_site' else (parameter.owner,)
    parent = [p for name in owners for p, _ in rows(project, parameter.block, name)]
    inside = [p for p in parent if category(p) == title]
    if len(inside) < len(parent):
        return title
    return 'Atom sites' if owner == 'atom_site' else _titles().get(owner, owner)


def _table_order(parameter: Parameter) -> tuple:
    """Rows in the order a table lists them: coefficient 2 before 10."""
    return tuple(
        (0, int(part), '') if part.isdigit() else (1, 0, part)
        for part in re.split(r'(\d+)', str(parameter))
    )


def groups(
    project: object, freed: list[Parameter], free: set[Parameter], *, fixing: bool = False
) -> list[Group]:
    """The actions that free `freed` (or fix it, `fixing`), given the parameters free now.

    A category whose every row (two or more) is freed now or free already is one Free · all;
    any other part of a category is its rows, ticked one by one.
    """
    by_category: dict[tuple[str, str], list[Parameter]] = {}
    for parameter in freed:
        key = (parameter.block, offered(project, parameter))
        by_category.setdefault(key, []).append(parameter)
    out = []
    for (block, title), chosen in by_category.items():
        owners = {parameter.owner for parameter in chosen}
        everything = {
            parameter
            for owner in owners
            for parameter in members(project, block, owner)
            if offered(project, parameter) == title
        }
        # The category's parameters that must keep their state through the action.
        left = (everything & free if fixing else everything - free) - set(chosen)
        # The fewest actions a person takes (the owner, 2026-11-11): Free · all (Fixed · all) only
        # when the stage sets every row the category shows and there are at least two; otherwise
        # the category shown and each row ticked in turn. Never set all and then set some back,
        # never a typed name filter.
        if everything and set(chosen) <= everything and not left and len(chosen) >= 2:
            out.append(Group(title, block, ''))
        else:
            rows = tuple(sorted(chosen, key=_table_order))
            out.append(Group(title, block, part=ROWS, rows=rows))
    return _across_blocks(project, out, by_category, free, fixing=fixing)


def _across_blocks(
    project: object,
    found: list[Group],
    by_category: dict[tuple[str, str], list[Parameter]],
    free: set[Parameter],
    *,
    fixing: bool,
) -> list[Group]:
    """One Free · all over the datablocks where a stage sets a category's every row in all.

    The table without a datablock filter lists a category's rows from every block: six banks'
    scales are one category of six rows, not six of one.
    """
    names = [item.name for item in [*project.structures, *project.experiments]]
    out = list(found)
    for title in {title for _block, title in by_category}:
        blocks = [block for block, t in by_category if t == title]
        if len(blocks) < 2:
            continue
        chosen = {p for block in blocks for p in by_category[block, title]}
        owners = {p.owner for p in chosen}
        everything = {
            p
            for block in names
            for owner in owners
            for p in members(project, block, owner)
            if offered(project, p) == title
        }
        left = (everything & free if fixing else everything - free) - chosen
        if chosen <= everything and not left and len(chosen) >= 2:
            out = [g for g in out if not (g.title == title and g.block in blocks)]
            out.append(Group(title, ''))
    return out


LINE = re.compile(
    r"^(\w+)\.(\w+)(?:\[['\"]?([^\]'\"]+)['\"]?\])?\.(\w+)\.free = (True|False)$", re.MULTILINE
)
LOOP = re.compile(r'^for \w+ in (\w+)\.(\w+)(?:\[[^\]]*\])?\)?:$', re.MULTILINE)


class Tracker:
    """What a tutorial has freed so far, stage by stage, and each stage's line-by-line actions."""

    def __init__(self, project: object, blocks: dict[str, str]) -> None:
        """`blocks` maps the tutorial's names (`structure`, `experiment_300k`) to block names."""
        self.project = project
        self.blocks = blocks
        self.free: set[Parameter] = set()

    def stage(self, edits: list[str]) -> dict[str, list[Group]]:
        """The stage's free ('True') and fix ('False') actions for its line-by-line edits."""
        text = '\n'.join(edits)
        lines: dict[str, list[Parameter]] = {'True': [], 'False': []}
        for var, owner, row, name, state in LINE.findall(text):
            if var in self.blocks:
                lines[state].append(Parameter(self.blocks[var], owner, row or '', name))
        out = {
            'True': groups(self.project, lines['True'], self.free) if lines['True'] else [],
            'False': (
                groups(self.project, lines['False'], self.free, fixing=True)
                if lines['False']
                else []
            ),
        }
        self.free |= set(lines['True'])
        self.free -= set(lines['False'])
        # A loop over a collection frees the parameters it names in every item.
        for block_text in re.split(r'^(?=\S)', text, flags=re.MULTILINE):
            loop = LOOP.match(block_text)
            if not loop or loop[1] not in self.blocks or '.free' not in block_text:
                continue
            named = set(re.findall(r'\.(\w+)(?:\.free|,|\))', block_text))
            loose = 'for component in' in block_text or '.adp_' in block_text
            for parameter in members(self.project, self.blocks[loop[1]], loop[2]):
                if parameter.name in named or (loose and parameter.name.startswith('adp_')):
                    if '= False' in block_text and 'not ' not in block_text:
                        self.free.discard(parameter)
                    else:
                        self.free.add(parameter)
        return out


# A parameter as a sentence would show it: a table label (Greek letters, sub- and superscripts) or
# a word typed in the name filter.
LABEL = re.compile(r'[Ͱ-Ͽ⁰-₟²³¹]')
NAMED = re.compile(r'\*\*([^*]+)\*\*(?= in (?:their name|the name filter))')


def symbols(sentence: str) -> list[str]:
    """The parameter symbols a stage sentence shows (owner, 2026-11-09: at most two)."""
    bold = re.findall(r'\*\*([^*]+)\*\*', sentence)
    return [token for token in bold if LABEL.search(token)] + NAMED.findall(sentence)
