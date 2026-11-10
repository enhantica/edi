#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the app capture plan of a case's Application tutorial.

    python tools/docs/app_tutorial_plan.py CASE OUTPUT.js

The plan follows the case's Python tutorial: a new project, its structures and experiments loaded
with Load > From web... from the EasyDiffraction collection, the relations the project starts with,
then the same fit stages. Which parameters a stage frees comes from the case's Command line page,
whose stage outputs list the free parameters by the paths the app's parameter table filters on.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'website'))

from app_groups import Parameter, groups, load_case  # noqa: E402
from render_cli_tutorials import stages  # noqa: E402

# The case that also shows loading measured data from a file on disk (owner record 2026-11-08).
FROM_FILE = {'pd-neut-tof_si-sepd'}
CLI_PAGES = ROOT / 'website/surfaces/docs/cli/tutorials/cases'
PROJECTS = ROOT / 'docs/user/cli'


def blocks(source: str) -> tuple[dict[str, str], list[str], list[str]]:
    """The tutorial's block names (`structure` -> `cosio`), its structures and experiments."""
    named, structures, experiments = {}, [], []
    for var, kind, name in re.findall(
        r"^(\w+) = project\.(structures|experiments)\['([^']+)'\]$", source, flags=re.MULTILINE
    ):
        named[var] = name
        (structures if kind == 'structures' else experiments).append(name)
    return named, structures, experiments


def free_lists(case: str) -> list[tuple[str, set[str]]]:
    """Each fit on the case's Command line page: its section title and the paths it had free."""
    text = (CLI_PAGES / f'{case}.md').read_text(encoding='utf-8')
    out = []
    for section in re.split(r'^## ', text, flags=re.MULTILINE)[1:]:
        title = section.split('\n', 1)[0].strip()
        table = section.split('refined parameters', 1)
        if len(table) < 2:
            continue
        paths = set()
        for line in table[1].split('```', 1)[0].splitlines()[2:]:
            found = re.search(r'\s((?:structures?|experiments?)[\w.\[\]\-]*)\s', line)
            if found:
                paths.add(found.group(1))
        out.append((title, paths))
    return out


def relations(case: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The aliases (id, unique name) and constraints (id, expression) the project starts with."""
    aliases, constraints = [], []
    for path in sorted((PROJECTS / case / 'project').rglob('analysis*.edi')):
        text = path.read_text(encoding='utf-8')
        for loop in re.split(r'^loop_\s*$', text, flags=re.MULTILINE)[1:]:
            lines = [line.strip() for line in loop.strip().splitlines()]
            keys = [line for line in lines if line.startswith('_')]
            rows = [line for line in lines[len(keys) :] if line and not line.startswith('_')]
            if keys and keys[0].startswith('_alias.'):
                for row in rows:
                    parts = row.split()
                    if len(parts) >= 2:
                        aliases.append((parts[0], parts[1]))
            elif keys and keys[0].startswith('_constraint.'):
                for row in rows:
                    parts = re.findall(r"'[^']*'|\"[^\"]*\"|\S+", row)
                    if len(parts) >= 2:
                        constraints.append((parts[0], parts[1].strip('\'"')))
                    if parts and parts[0].startswith(('_', 'data_')):
                        break
    return aliases, constraints


def unique_name(expression: str, named: dict[str, str]) -> str:
    """`structure.atom_sites['La'].adp_iso` as its unique name, `lbco.atom_site.La.adp_iso`."""
    found = re.match(r"(\w+)\.atom_sites\['([^']+)'\]\.(\w+)$", expression)
    if not found:
        raise SystemExit(f'cannot name the alias parameter {expression}')
    var, site, item = found.groups()
    return f'{named[var]}.atom_site.{site}.{item}'


def free(path: str) -> list[str]:
    return [
        'reveal:parameters.nameFilter',
        'fill:parameters.nameFilter=' + path,
        'parameters.freeHeader',
        'parameters.freeHeader.free',
        'parameters.clearFilters',
    ]


def adp_types(case: str, kind: str) -> list[str]:
    """Every site's displacement type set to `kind`, row by row in the Structure page's ADP table.

    A tutorial's loop over the atom sites setting `adp_type` (one structure; its project gives
    how many sites it has).
    """
    folder = ROOT / 'docs/user/cli' / case / 'project/structures'
    files = sorted(folder.glob('*.edi'))
    if len(files) != 1:
        raise SystemExit(f'{case}: an adp_type loop needs one structure, not {len(files)}')
    text = files[0].read_text(encoding='utf-8')
    block = re.search(
        r'^loop_\n((?:_atom_site\.\w+\n)+)((?:(?!loop_|_)\S.*\n)+)', text, re.MULTILINE
    )
    if block is None:
        raise SystemExit(f'{case}: no atom-site loop in {files[0].name}')
    sites = len(block[2].splitlines())
    actions = ['appBar.tab.structure', 'sideBar.tab.basic']
    actions += ['reveal:group.atom_site_aniso', 'expand:group.atom_site_aniso']
    for row in range(sites):
        # The row at the top of the table, whole, then its type selector, as the app's demo does.
        actions += [
            f'show:atomSiteAdps.list:{row}:begin',
            f'atomSiteAdp.type.{row}',
            'choose:' + kind,
        ]
    return actions


def set_category(
    title: str, state: str, datablock: str = '', word: str = '', unword: str = ''
) -> list[str]:
    """A whole group in one action: the table filtered to its category, then the Free header.

    The owner's rules (records 7101f0fd9 and b8df97176): a group is fixed or freed in one action,
    by its category, never parameter by parameter. In a project of several structures or
    experiments the table is first filtered to the group's datablock. `word` narrows the action to
    part of the category by one name-filter word; `unword` sets the part it names back after the
    whole category is set (app_groups.py chooses both).
    """
    narrowed = (
        ['reveal:parameters.datablock', 'parameters.datablock', 'choose:' + datablock]
        if datablock
        else []
    )
    named = ['reveal:parameters.nameFilter', 'fill:parameters.nameFilter=' + word] if word else []
    other = 'fixed' if state == 'free' else 'free'
    again = [
        action
        for rest in unword.split()
        for action in (
            'reveal:parameters.nameFilter',
            'fill:parameters.nameFilter=' + rest,
            'parameters.freeHeader',
            'parameters.freeHeader.' + other,
        )
    ]
    return [
        *narrowed,
        'reveal:parameters.category',
        'parameters.category',
        'choose:' + title,
        *named,
        'parameters.freeHeader',
        'parameters.freeHeader.' + state,
        *again,
        'parameters.clearFilters',
    ]


def as_parameter(path: str, roots: dict[str, str]) -> Parameter:
    """A table path (`structures[cosio].atom_sites[Co1].adp_iso`) as app_groups names it."""
    for name, prefix in sorted(roots.items(), key=lambda item: -len(item[1])):
        if path.startswith(prefix):
            match = re.fullmatch(r'(\w+)(?:\[([^\]]+)\])?\.(\w+)', path[len(prefix) :])
            if match:
                return Parameter(name, match[1], match[2] or '', match[3])
    raise SystemExit(f'{path}: not a parameter the app tutorial can name by its category')


def by_category(
    project: object,
    paths: list[str],
    free_now: set[str],
    roots: dict[str, str],
    state: str,
    *,
    several: bool,
) -> list[str]:
    """The actions that set `paths` to `state`: a category, or a one-word part of one."""
    chosen = [as_parameter(path, roots) for path in paths]
    now = {as_parameter(path, roots) for path in free_now}
    actions = []
    for group in groups(project, chosen, now, fixing=state == 'fixed'):
        if group.part:
            # A part no word selects: its rows one by one, as the page names it in words.
            for row in group.rows:
                path = next(p for p in paths if as_parameter(p, roots) == row)
                actions += free(path) if state == 'free' else fix(path)
            continue
        actions += set_category(
            group.title, state, group.block if several else '', group.word, group.unword
        )
    return actions


# The parameter table's category picker titles for the groups a tutorial frees in a loop.
BACKGROUND = 'Background'
DISPLACEMENT = 'Atomic displacement'
COORDINATES = 'Atomic coordinates'
# The one tutorial that shows the group action in screenshots.
GROUP_HOWTO = 'pd-neut-cwl_lbco-hrpt'
LINKED = 'Linked structures'


def fix(path: str) -> list[str]:
    return [
        'reveal:parameters.nameFilter',
        'fill:parameters.nameFilter=' + path,
        'parameters.freeHeader',
        'parameters.freeHeader.fixed',
        'parameters.clearFilters',
    ]


def estimate(args: str) -> list[str]:
    """An `auto_estimate(...)` call as the app's Background estimation settings and Estimate."""
    actions = ['appBar.tab.experiment', 'sideBar.tab.extras']
    actions += ['reveal:group.background_estimate', 'expand:group.background_estimate']
    model = re.search(r"use_model='(\w+)'", args)
    if model:
        actions += [
            'reveal:background_estimate.use_model',
            'background_estimate.use_model',
            'choose-token:background_estimate.use_model=' + model.group(1),
        ]
    points = re.search(r'n_points=(\d+)', args)
    if points:
        actions += [
            'reveal:background_estimate.n_points',
            'fill:background_estimate.n_points=' + points.group(1),
            'key:Return',
        ]
    return [
        *actions,
        'sideBar.tab.basic',
        'reveal:group.background',
        'expand:group.background',
        'reveal:background.estimate',
        'background.estimate',
    ]


def value_path(expression: str, named: dict[str, str], roots: dict[str, str]) -> str:
    """`structure.atom_sites['Co1'].adp_iso` as its path, `structure.atom_sites[Co1].adp_iso`."""
    var, rest = expression.split('.', 1)
    return roots[named[var]] + re.sub(r"\['([^']+)'\]", r'[\1]', rest)


def by_hand(source: str) -> bool:
    """Whether the tutorial builds its structure and experiment itself, as LBCO HRPT does."""
    return 'project.structures.create(' in source


def _calls(source: str, name: str) -> list[dict]:
    """The keyword arguments of each `<...>.<name>(...)` call in the tutorial."""
    return [
        {
            k.arg: ast.literal_eval(k.value)
            for k in node.keywords
            if isinstance(k.value, ast.Constant)
        }
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == name
    ]


def _assigned(source: str, target: str) -> str:
    found = re.search(rf'^\w+\.{re.escape(target)} = (.+)$', source, flags=re.MULTILINE)
    return ast.literal_eval(found.group(1)) if found else None


def by_hand_steps(source: str) -> list[dict]:  # noqa: PLR0915 - one setup, step by step
    """A structure from its space group, cell and sites; an experiment from measured data."""

    def value(ident: str, number: object) -> list[str]:
        return ['reveal:' + ident, f'fill:{ident}={number}', 'key:Return']

    def step(ident, page, description, actions, highlights):
        return {
            'id': ident,
            'page': page,
            'description': description,
            'actions': actions,
            'highlights': highlights,
            'sidebar': '',
            'capture': True,
        }

    structure = _calls(source, 'create')[0]['name']
    actions = [
        'appBar.tab.structure',
        'sideBar.tab.basic',
        'expand:group.structures',
        'structures.create',
        f'fill:structures.name.0={structure}',
        'key:Return',
    ]
    steps = [
        step(
            'structure-created', 'structure', 'Create the structure', actions, ['structures.list']
        )
    ]
    actions = ['reveal:group.space_group', 'expand:group.space_group', 'spaceGroup.nameHM']
    actions += ['type:' + _assigned(source, 'space_group.name_h_m'), 'key:Return']
    actions += ['reveal:group.cell', 'expand:group.cell']
    actions += value('cell.length_a', _assigned(source, 'cell.length_a'))
    steps.append(
        step(
            'structure-cell',
            'structure',
            'Set the space group and the cell',
            actions,
            ['group.space_group', 'group.cell'],
        )
    )
    actions = ['reveal:group.atom_site', 'expand:group.atom_site']
    sites = _calls(source, 'create')
    sites = [site for site in sites if 'type_symbol' in site]
    for row, site in enumerate(sites):
        actions += ['atomSites.append', f'fill:atomSite.label.{row}={site["id"]}', 'key:Return']
        actions += [f'atomSite.typeSymbol.{row}', 'type:' + site['type_symbol'], 'key:Return']
        if site.get('wyckoff_letter'):
            # A special position's coordinates follow from its letter; `b:` finds `1b: ½, ½, ½`.
            letter = site['wyckoff_letter']
            actions += [f'atomSite.wyckoffLetter.{row}', f'type:{letter}:', 'key:Return']
        else:
            for axis in ('x', 'y', 'z'):
                actions += value(f'atomSite.fract{axis.upper()}.{row}', site[f'fract_{axis}'])
        if 'occupancy' in site:
            actions += value(f'atomSite.occupancy.{row}', site['occupancy'])
    steps.append(
        step('structure-sites', 'structure', 'Add the atom sites', actions, ['atomSites.list'])
    )
    actions = ['reveal:group.atom_site_aniso', 'expand:group.atom_site_aniso']
    for row, site in enumerate(sites):
        actions += value(f'atomSiteAdp.iso.{row}', site['adp_iso'])
    steps.append(
        step('structure-adp', 'structure', 'Set the displacements', actions, ['atomSiteAdps.list'])
    )

    kind = _calls(source, 'add_from_data_path')[0]
    data = re.search(r"download_data\('([^']+-data)'", source).group(1)
    actions = ['appBar.tab.experiment', 'sideBar.tab.basic', 'expand:group.experiments']
    actions += ['experiments.create']
    for control, key in (
        ('experimentType.sampleForm', 'sample_form'),
        ('experimentType.beamMode', 'beam_mode'),
        ('experimentType.radiationProbe', 'radiation_probe'),
    ):
        actions += [control, f'choose-token:{control}={kind[key]}']
    actions += [f'fill:experiments.name.0={kind["name"]}', 'key:Return']
    steps.append(
        step(
            'experiment-created',
            'experiment',
            'Create the experiment and choose its type',
            actions,
            ['experimentType'],
        )
    )
    actions = ['experiments.load', 'experiments.load.dataWeb']
    actions += ['fill:onlineLoad.field.id=' + data, 'onlineLoad.search', 'wait-online']
    steps.extend((
        step(
            'data-web',
            'experiment',
            'Find the measured data in the EasyDiffraction collection',
            actions,
            ['onlineLoad.field.id', 'onlineLoad.results'],
        ),
        step(
            'data-loaded',
            'experiment',
            'Load the measured data',
            ['onlineLoad.row.0', 'wait-online'],
            ['workflow.experiment.mainContent'],
        ),
    ))
    actions = ['reveal:group.instrument', 'expand:group.instrument']
    for item in ('setup_wavelength', 'calib_twotheta_offset'):
        number = _assigned(source, 'instrument.' + item)
        if number is not None:
            actions += value('instrument.' + item, number)
    actions += ['reveal:group.peak', 'expand:group.peak']
    for item in re.findall(r'^\w+\.peak\.(\w+) = ', source, flags=re.MULTILINE):
        actions += value('peak.' + item, _assigned(source, 'peak.' + item))
    steps.append(
        step(
            'experiment-instrument',
            'experiment',
            'Set the wavelength, 2θ zero and peak widths',
            actions,
            ['group.instrument', 'group.peak'],
        )
    )
    loop = re.search(
        r'^for position in \(([^)]*)\):\n\s+\w+\.background\.create\(position=position, '
        r'intensity=([\d.]+)\)',
        source,
        flags=re.MULTILINE,
    )
    actions = ['reveal:group.background', 'expand:group.background']
    for row, position in enumerate(p.strip() for p in loop.group(1).split(',')):
        actions += ['background.append']
        actions += value(f'background.position.{row}', position)
        actions += value(f'background.intensity.{row}', loop.group(2))
    actions += ['reveal:group.excluded_region', 'expand:group.excluded_region']
    regions = [region for region in _calls(source, 'create') if set(region) == {'start', 'end'}]
    for row, region in enumerate(regions):
        actions += ['excludedRegions.append']
        actions += value(f'excludedRegion.start.{row}', region['start'])
        actions += value(f'excludedRegion.end.{row}', region['end'])
    steps.append(
        step(
            'experiment-background',
            'experiment',
            'Add the background points and excluded regions',
            actions,
            ['excludedRegions.list'],
        )
    )
    link = next(c for c in _calls(source, 'create') if 'structure_id' in c)
    # A new experiment links the project's only structure itself; the step sets its scale.
    actions = [
        'reveal:group.linked_structure',
        'expand:group.linked_structure',
    ]
    actions += value('linkedStructure.scale.0', link['scale'])
    steps.append(
        step(
            'experiment-linked',
            'experiment',
            'Link the structure to the experiment',
            actions,
            ['linkedStructure.list', 'workflow.experiment.mainContent'],
        )
    )
    return steps


def grouped(paths: set[str], loops: list[str]) -> tuple[list[str], set[str]]:
    """Filters for whole background loops the stage frees, and the paths they leave."""
    filters, rest = [], set(paths)
    for root in loops:
        covered = {path for path in rest if path.startswith(root + 'background[')}
        if covered:
            filters.append(root + 'background[')
            rest -= covered
    return filters, rest


def plan(case: str) -> dict:  # noqa: PLR0912, PLR0914, PLR0915 - one plan, step by step
    source = (ROOT / 'docs/user/tutorials' / f'{case}.py').read_text(encoding='utf-8')
    named, structures, experiments = blocks(source)
    exp_root = {
        name: ('experiment.' if len(experiments) == 1 else f'experiments[{name}].')
        for name in experiments
    }
    roots = dict(exp_root)
    roots.update({
        name: ('structure.' if len(structures) == 1 else f'structures[{name}].')
        for name in structures
    })
    steps: list[dict] = []

    def shot(  # noqa: PLR0913
        ident, page, description, actions, highlights=(), sidebar='', *, capture=True, phase=''
    ):
        step = {
            'id': ident,
            'page': page,
            'description': description,
            'actions': actions,
            'highlights': list(highlights),
            'sidebar': sidebar,
            'capture': capture,
        }
        if phase:
            step['fitPhase'] = phase
        steps.append(step)

    shot('home', 'home', 'Start a new analysis', ['platform:light', 'theme:light'], ['home.start'])
    scan = "fitting_mode = 'sequential'" in source
    # A calculation without data loads its project and fits nothing: open the example, look at the
    # calculated pattern and the report.
    simulation = '## Perform the analysis' not in source
    if scan or simulation:
        # A scan's datasets come with its project: open the example from Project > Examples.
        shot(
            'example-open',
            'project',
            'Open the example from Examples',
            [
                'home.start',
                'sideBar.tab.basic',
                'reveal:group.examples',
                'expand:group.examples',
                'reveal:examples.search',
                f'fill:examples.search={case}',
                f'reveal:examples.open.{case}',
                f'examples.open.{case}',
                'pin-time:01 Jan 2026 12:00:00',
            ],
            ['workflow.project.mainContent'],
        )
        if simulation:
            shot(
                'calculated',
                'analysis',
                'See the calculated pattern',
                ['appBar.tab.analysis', 'sideBar.tab.basic', 'mainArea.analysis.tab.fitting'],
                ['workflow.analysis.mainContent'],
            )
            shot(
                'report',
                'report',
                'Review the report',
                ['appBar.tab.report', 'sideBar.tab.basic'],
                ['workflow.report.mainContent'],
                'Main',
            )
            for step in steps:
                step['capture'] = step['id'] != 'home'
            return {'example': case, 'steps': steps}
    else:
        shot(
            'project-details',
            'project',
            'Enter the project details',
            [
                'home.start',
                'project.create',
                # A project name has at most 31 characters.
                'fill:createProject.name=' + (case if len(case) <= 31 else case.split('_', 1)[1]),
                'fill:createProject.title=@title',
                'fill:createProject.location=@projectDirectory',
            ],
            ['createProject.name', 'createProject.title', 'createProject.location'],
        )
        shot(
            'project-created',
            'project',
            'Create the project',
            ['createProject.accept', 'pin-time:01 Jan 2026 12:00:00'],
            ['workflow.project.mainContent'],
        )
        if by_hand(source):
            steps += by_hand_steps(source)
        else:
            for index, name in enumerate(structures):
                entry = f'{case}-{name}'
                shot(
                    f'structure-web-{index}',
                    'structure',
                    f'Find the structure {name} in the EasyDiffraction collection',
                    [
                        'appBar.tab.structure',
                        'sideBar.tab.basic',
                        'expand:group.structures',
                        'structures.load',
                        'structures.load.web',
                        'onlineLoad.source',
                        'choose:EasyDiffraction Database',
                        'fill:onlineLoad.field.id=' + entry,
                        'onlineLoad.search',
                        'wait-online',
                    ],
                    ['onlineLoad.field.id', 'onlineLoad.results'],
                )
                shot(
                    f'structure-loaded-{index}',
                    'structure',
                    f'Load the structure {name}',
                    ['onlineLoad.row.0', 'wait-online'],
                    ['structures.list', 'workflow.structure.mainContent'],
                )
            for index, name in enumerate(experiments):
                entry = f'{case}-{name}'
                shot(
                    f'experiment-web-{index}',
                    'experiment',
                    f'Find the experiment {name} in the EasyDiffraction collection',
                    [
                        'appBar.tab.experiment',
                        'sideBar.tab.basic',
                        'expand:group.experiments',
                        'experiments.load',
                        'experiments.load.experimentWeb',
                        'fill:onlineLoad.field.id=' + entry,
                        'onlineLoad.search',
                        'wait-online',
                    ],
                    ['onlineLoad.field.id', 'onlineLoad.results'],
                )
                shot(
                    f'experiment-loaded-{index}',
                    'experiment',
                    f'Load the experiment {name}',
                    ['onlineLoad.row.0', 'wait-online'],
                    ['experiments.list', 'workflow.experiment.mainContent'],
                )

    aliases, constraints = relations(case)
    # A relation the tutorial adds in a stage is added there, not at the start.
    created = set(re.findall(r"\.(?:aliases|constraints)\.create\(id='([^']+)'", source))
    aliases = [item for item in aliases if item[0] not in created]
    constraints = [item for item in constraints if item[0] not in created]
    alias_count = constraint_count = 0

    if case in FROM_FILE:
        # Measured data can also come from a file on the user's own disk (Load > From file...).
        shot(
            'data-from-file',
            'experiment',
            'Measured data from a file on your own disk',
            [
                'appBar.tab.experiment',
                'sideBar.tab.basic',
                'reveal:experiments.load',
                'experiments.load',
            ],
            ['experiments.load.dataFile'],
        )
        shot(
            'data-from-file-closed',
            'experiment',
            'Close the menu',
            ['key:Escape'],
            [],
            capture=False,
        )

    def add_relations(new_aliases, new_constraints):
        nonlocal alias_count, constraint_count
        actions = ['appBar.tab.analysis', 'sideBar.tab.extras']
        if new_aliases:
            actions += ['reveal:group.alias', 'expand:group.alias']
        for ident, parameter in new_aliases:
            row = alias_count
            actions += [
                'aliases.append',
                f'show:aliases.list:{row}:begin',
                f'reveal:alias.id.{row}',
                f'fill:alias.id.{row}={ident}',
                'key:Return',
                f'alias.parameter.{row}',
                'type:' + parameter,
                'key:Return',
            ]
            alias_count += 1
        if new_constraints:
            actions += ['reveal:group.constraint', 'expand:group.constraint']
        for ident, expression in new_constraints:
            row = constraint_count
            # The list shows two rows; later ones are scrolled into view first.
            actions += ['constraints.append'] + (
                [f'show:constraints.list:{row}:begin'] if row >= 2 else []
            )
            actions += [
                f'reveal:constraint.id.{row}',
                f'fill:constraint.id.{row}={ident}',
                'key:Return',
                f'fill:constraint.expression.{row}={expression}',
                'key:Return',
            ]
            constraint_count += 1
        return actions

    if (aliases or constraints) and not scan:
        shot(
            'relations-start',
            'analysis',
            'Add the relations the project starts with',
            add_relations(aliases, constraints),
            ['group.constraint'] if constraints else ['group.alias'],
            'Extra',
            phase='setup',
        )

    start = source.index('## Perform the analysis')
    estimates = re.findall(
        r'^(\w+)\.background\.auto_estimate\((.*)\)$', source[:start], flags=re.MULTILINE
    )
    for var, args in estimates:
        shot(
            f'background-estimate-{named[var]}',
            'experiment',
            'Estimate the background',
            estimate(args),
            ['background.rows', 'background.estimate'],
        )
    if "fitting_mode = 'single'" in source[:start]:
        shot(
            'fitting-mode-single',
            'analysis',
            'Fit the template pattern alone first',
            [
                'appBar.tab.analysis',
                'sideBar.tab.extras',
                'reveal:group.fitting_mode',
                'expand:group.fitting_mode',
                'fittingMode.type',
                'choose-token:fittingMode.type=single',
            ],
            ['group.fitting_mode'],
            'Extra',
            phase='setup',
        )
    if "fitting_mode = 'independent'" in source[:start]:
        # Several experiments default to a joint fit; here each is fitted on its own.
        shot(
            'fitting-mode-independent',
            'analysis',
            'Fit each experiment on its own',
            [
                'appBar.tab.analysis',
                'sideBar.tab.extras',
                'reveal:group.fitting_mode',
                'expand:group.fitting_mode',
                'fittingMode.type',
                'choose-token:fittingMode.type=independent',
            ],
            ['group.fitting_mode'],
            'Extra',
            phase='setup',
        )

    # The minimizer settings the case's project declares: descent, tolerance, rule and iterations.
    analysis = PROJECTS / case / 'project/analysis/analysis.edi'
    declared = analysis.read_text(encoding='utf-8') if analysis.exists() else ''
    rule = re.search(r'(?m)^_minimizer\.stop_rules "?(\w+)"?$', declared)
    bound = re.search(r'(?m)^_minimizer\.max_iterations (\d+)$', declared)
    descent = re.search(r'(?m)^_minimizer\.descent (\w+)$', declared)
    tolerance = re.search(r'(?m)^_minimizer\.chi_square_tolerance (\S+)$', declared)
    if rule or bound or descent or tolerance:
        shot(
            'minimizer',
            'analysis',
            'Set the minimizer as the project does',
            [
                'appBar.tab.analysis',
                'sideBar.tab.extras',
                'reveal:group.minimizer',
                'expand:group.minimizer',
                *([f'choose-token:minimizer.descent={descent[1]}'] if descent else []),
                *([f'fill:minimizer.chiSquareTolerance={tolerance[1]}'] if tolerance else []),
                *([f'choose-token:minimizer.stopRule={rule[1]}'] if rule else []),
                *([f'fill:minimizer.maxIterations={bound[1]}'] if bound else []),
            ],
            ['group.minimizer'],
            'Extra',
            phase='setup',
        )

    shot(
        'nothing-free',
        'analysis',
        'Start with every parameter fixed',
        [
            'appBar.tab.analysis',
            'sideBar.tab.basic',
            'parameters.clearFilters',
            'parameters.freeHeader',
            'parameters.freeHeader.fixed',
        ],
        ['group.parameters', 'parameters.freeHeader'],
        'Main',
        phase='setup',
    )

    fits = free_lists(case)
    project = load_case(case)
    tutorial = stages(source)
    previous: set[str] = set()
    shown_howto = False
    for number, stage in enumerate(tutorial):
        if number >= len(fits):
            raise SystemExit(
                f'{case}: the Command line page has fewer fits than stage {number + 1}'
            )
        title, paths = fits[number]
        if stage['title'] and title != stage['title']:
            raise SystemExit(
                f'{case}: stage {number + 1} is {stage["title"]!r}, the page {title!r}'
            )
        edits = '\n'.join(stage['edits'])
        loops = [
            exp_root[named[var]]
            for var in re.findall(r'^for \w+ in (\w+)\.background:$', edits, flags=re.MULTILINE)
        ]
        filters, rest = grouped(paths - previous, loops)
        fix_filters, fix_rest = grouped(previous - paths, list(exp_root.values()))
        # One experiment: its background is the whole Background category. A loop over every
        # site's displacement is the Atomic displacement category.
        categories = []
        if len(experiments) == 1 and filters:
            categories.append((BACKGROUND, ''))
            filters = []
        # A loop over a group's items (the tutorial's one action) is its category in the app; the
        # extinction coefficients, freed together, are the Extinction category.
        several = len(structures) > 1 or len(experiments) > 1
        for category, in_group, loop in (
            (
                DISPLACEMENT,
                r'\.(adp_iso|adp_\d\d)$',
                r'^\s+(\w+\.adp_(iso|\d\d)\.free|for component in)',
            ),
            (COORDINATES, r'\.fract_[xyz]$', r'^\s+for coordinate in'),
            (LINKED, r'linked_structures\[[^\]]+\]\.scale$', r'^\s+\w+\.linked_structures'),
            (BACKGROUND, r'\.background\[\d+\]\.coef$', r'^for \w+ in \w+\.background_terms:$'),
        ):
            members = {path for path in rest if re.search(in_group, path)}
            if members and re.search(loop, edits, flags=re.MULTILINE):
                owners = {
                    match[1]
                    for match in (
                        re.match(r'(?:structures|experiments)\[([^\]]+)\]\.', path)
                        for path in members
                    )
                    if match
                }
                datablock = next(iter(owners)) if several and len(owners) == 1 else ''
                categories.append((category, datablock))
                rest -= members
        actions = []
        for _var, args in re.findall(
            r'^(\w+)\.background\.auto_estimate\((.*)\)$', edits, flags=re.MULTILINE
        ):
            actions += estimate(args)
        for _var, kind in re.findall(
            r"^for (\w+) in (?:\w+)\.atom_sites:\n\s+\1\.adp_type = '(\w+)'$",
            edits,
            flags=re.MULTILINE,
        ):
            actions += adp_types(case, kind)
        actions += ['appBar.tab.analysis', 'sideBar.tab.basic']
        for expression, value in re.findall(
            r'^([\w.\[\]\']+) = ([-\d.]+)$', edits, flags=re.MULTILINE
        ):
            actions += [
                'reveal:parameters.nameFilter',
                'fill:parameters.nameFilter=' + value_path(expression, named, roots),
                'fill:parameters.value.0=' + value,
                'key:Return',
                'parameters.clearFilters',
            ]
        if case == GROUP_HOWTO and categories and not shown_howto:
            # The getting-started tutorial shows the group action once, in two shots (owner record
            # b8df97176): the table filtered to the category, then the Free header's menu.
            shown_howto = True
            category, _datablock = categories.pop(0)
            shot(
                'group-filter',
                'analysis',
                f'Filter the table to {category}',
                [
                    *actions,
                    'reveal:parameters.category',
                    'parameters.category',
                    'choose:' + category,
                ],
                ['parameters.category'],
                'Main',
                phase='setup',
            )
            shot(
                'group-free-all',
                'analysis',
                'Free all from the Free column header',
                ['parameters.freeHeader'],
                ['parameters.freeHeader'],
                'Main',
                phase='setup',
            )
            actions = ['parameters.freeHeader.free', 'parameters.clearFilters']
        for category, datablock in categories:
            actions += set_category(category, 'free', datablock)
        # Whole backgrounds of chosen experiments: their datablock's Background category.
        for root in filters:
            block = next(name for name, prefix in exp_root.items() if root.startswith(prefix))
            actions += set_category(BACKGROUND, 'free', block if several else '')
        if rest:
            actions += by_category(project, sorted(rest), previous, roots, 'free', several=several)
        if len(experiments) == 1 and fix_filters:
            actions += set_category(BACKGROUND, 'fixed')
            fix_filters = []
        for root in fix_filters:
            block = next(name for name, prefix in exp_root.items() if root.startswith(prefix))
            actions += set_category(BACKGROUND, 'fixed', block if several else '')
        if fix_rest:
            actions += by_category(
                project, sorted(fix_rest), previous, roots, 'fixed', several=several
            )
        new_aliases = [
            (ident, unique_name(param, named))
            for ident, param in re.findall(
                r"aliases\.create\(id='([^']+)', param=([^)]+)\)", edits
            )
        ]
        new_constraints = re.findall(
            r"constraints\.create\(id='([^']+)', expression='([^']+)'\)", edits
        )
        if new_aliases or new_constraints:
            actions += add_relations(new_aliases, new_constraints)
            actions += ['sideBar.tab.basic']
        shot(
            f'stage-{number + 1}-free',
            'analysis',
            title,
            actions,
            ['group.parameters'],
            'Main',
            phase='setup',
        )
        shot(
            f'stage-{number + 1}-fit',
            'analysis',
            f'Fit: {title}',
            ['statusBar.fit.button', 'wait-fit', 'close-fit-results'],
            ['workflow.analysis.mainContent', 'group.parameters'],
            'Main',
        )
        previous = paths
    if scan:
        shot(
            'scan-mode',
            'analysis',
            'Back to the sequential mode',
            [
                'sideBar.tab.extras',
                'reveal:group.fitting_mode',
                'expand:group.fitting_mode',
                'fittingMode.type',
                'choose-token:fittingMode.type=sequential',
            ],
            ['group.fitting_mode'],
            'Extra',
            phase='setup',
        )
        shot(
            'scan-fit',
            'analysis',
            'Fit the scan',
            ['sideBar.tab.basic', 'statusBar.fit.button', 'wait-fit', 'close-fit-results'],
            ['workflow.analysis.mainContent'],
            'Main',
        )
    shot(
        'correlations',
        'analysis',
        'Inspect the correlations',
        ['mainArea.analysis.tab.correlations'],
        ['workflow.analysis.mainContent'],
    )
    shot(
        'report',
        'report',
        'Review the report',
        ['mainArea.analysis.tab.fitting', 'appBar.tab.report', 'sideBar.tab.basic'],
        ['workflow.report.mainContent'],
        'Main',
    )
    # The images a reader needs, to keep each page light: the project form only where the
    # structure is built by hand, one search and one loaded frame per kind of block, and each
    # stage's fitted frame (the page lists what a stage frees).
    hidden = set() if by_hand(source) else {'home', 'project-details'}
    for kind in ('structure-web-', 'structure-loaded-', 'experiment-web-', 'experiment-loaded-'):
        found = [step['id'] for step in steps if step['id'].startswith(kind)]
        if found:
            keep = found[0] if 'web' in kind else found[-1]
            hidden.update(ident for ident in found if ident != keep)
    for step in steps:
        if step['id'] in hidden or re.fullmatch(r'stage-\d+-free', step['id']):
            step['capture'] = False
    return {'example': case, 'steps': steps}


SCRIPT = """// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of {case}, written by tools/docs/app_tutorial_plan.py.
(function () {{
    const EXAMPLE_ID = "{case}";
    const STEPS = {steps};
    return {{schema: 2, workflow: "tutorial", example: EXAMPLE_ID, build: function (capture) {{
        return STEPS.map(function (step) {{
            const actions = step.actions.map(function (action) {{
                return action.replace("@title", capture.title)
                    .replace("@projectDirectory", capture.projectDirectory);
            }});
            return Object.assign({{}}, step, {{actions: actions}});
        }});
    }}}};
}})();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = plan(args.case)
    args.output.write_text(
        SCRIPT.format(
            case=args.case, steps=json.dumps(data['steps'], ensure_ascii=False, indent=1)
        ),
        encoding='utf-8',
    )
    print(args.output, len(data['steps']), 'steps')


if __name__ == '__main__':
    main()
