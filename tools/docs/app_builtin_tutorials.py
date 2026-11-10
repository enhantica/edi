#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the app's built-in tutorials from the cases' docs plans (edi ADR-0082).

Each case's docs plan (tools/docs/app_tutorial_plan.py) is the walkthrough its app page shows. This
turns each plan step into the steps the tutorial panel runs (TutorialPanel.qml): a control to point
at, the app page's sentence, and a check, one of the panel's step kinds, that the user's action
satisfies and Next performs. The Interface tour stays as written; the cases follow it, LBCO on HRPT
first.

    python tools/docs/app_builtin_tutorials.py          # write app/tutorials/manifest.json
    python tools/docs/app_builtin_tutorials.py --check  # refuse a manifest that differs
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/docs'))
sys.path.insert(0, str(ROOT / 'website'))

from app_groups import Tracker, load_case  # noqa: E402
from app_tutorial_plan import plan  # noqa: E402
from render_app_tutorials import stage_sentence  # noqa: E402
from render_cli_tutorials import stages  # noqa: E402

MANIFEST = ROOT / 'app/tutorials/manifest.json'
METADATA = ROOT / 'app/examples/metadata.json'
TUTORIALS = ROOT / 'docs/user/tutorials'
CLI = ROOT / 'docs/user/cli'
GETTING_STARTED = 'pd-neut-cwl_lbco-hrpt'
BUILT_INS = ('interface',)
# The LBCO simulation teaches building a simulation by hand (owner record 70c8d4339): these steps
# stand in for opening its example.
BY_HAND_SIMULATION = ROOT / 'app/tutorials/lbco-simulation-by-hand.json'
SIMULATION_CASE = 'pd-neut-cwl_lbco_simulation'
# The stop rules' names as the Minimizer group's selector shows them.
STOP_RULES = {'chi_square_change': 'χ² change', 'shift_su': 'Shift/s.u.'}
# Each kind's From web… entry in its Load ▾ menu (TutorialPanel.webEntries).
WEB_ENTRIES = {
    'structure': 'structures.load.web',
    'experiment': 'experiments.load.experimentWeb',
    'data': 'experiments.load.dataWeb',
}
TAG_FACETS = ('purpose', 'fittingMode', 'sampleForm', 'probe', 'beamMode', 'scatteringType')


def step(title: str, text: str, page: str, target: str, check: str, **extra: object) -> dict:
    """One tutorial step as the manifest holds it."""
    out = {'title': title, 'text': text, 'page': page, 'target': target}
    if check:
        out['check'] = check
    out.update(extra)
    return out


def need(where: str, actions: list[str], prefix: str) -> list[str]:
    """The step's actions starting with `prefix`; none is a refusal naming it."""
    found = [action for action in actions if action.startswith(prefix)]
    if not found:
        raise SystemExit(f'{where}: no {prefix!r} action')
    return found


def fills(actions: list[str]) -> dict[str, str]:
    """The values a plan step types: control name to text."""
    return dict(a.removeprefix('fill:').split('=', 1) for a in actions if a.startswith('fill:'))


def minimizer_steps(actions: list[str]) -> list[dict]:
    """The stop rule and the iteration limit the case's project declares."""
    out = []
    for action in actions:
        if action.startswith('choose-token:minimizer.descent='):
            descent = action.split('=', 1)[1]
            text = f'On **Analysis → Extra**, choose **{descent}** as the **Descent**.'
            out.append(
                step(
                    'Descent',
                    text,
                    'analysis',
                    'minimizer.descent',
                    f'descent:{descent}',
                    tab='extras',
                )
            )
        if action.startswith('fill:minimizer.chiSquareTolerance='):
            tolerance = action.split('=', 1)[1]
            text = f'Set the **χ² change** tolerance to **{tolerance}** in **Minimizer**.'
            out.append(
                step(
                    'Tolerance',
                    text,
                    'analysis',
                    'minimizer.stopRule',
                    f'chi-tolerance:{tolerance}',
                    tab='extras',
                )
            )
        if action.startswith('choose-token:minimizer.stopRule='):
            rule = action.split('=', 1)[1]
            label = STOP_RULES.get(rule, rule)
            text = f'On **Analysis → Extra**, choose **{label}** as the **Stop rule**.'
            out.append(
                step(
                    'Stop rule',
                    text,
                    'analysis',
                    'minimizer.stopRule',
                    f'stop-rule:{rule}',
                    tab='extras',
                )
            )
    bound = fills(actions).get('minimizer.maxIterations')
    if bound:
        text = f'Set **Max iterations** to **{bound}** in **Minimizer**.'
        out.append(
            step(
                'Iteration limit',
                text,
                'analysis',
                'minimizer.maxIterations',
                f'max-iterations:{bound}',
                tab='extras',
            )
        )
    return out


# What a plan action may be without a step of its own: where the capture looks (a page, a
# sidebar tab, a scrolled or unfolded group, a key closing a field) or how it takes its picture.
# None of them changes the project, so the tutorial needs no step for them.
INERT = re.compile(
    r'(appBar\.tab\.\w+|sideBar\.tab\.\w+|reveal:.+|expand:.+|show:.+|key:(Return|Escape)'
    r'|platform:\w+|theme:\w+|pin-time:.+|wait-fit|wait-online|close-fit-results'
    r'|parameters\.clearFilters|mainArea\.analysis\.tab\.fitting)'
)
# The other actions of each plan step that its branch in plan_step turns into tutorial steps. A
# new project's title and folder are the capture's own (`@`), the tutorial's project is temporary.
TRANSLATED = {
    r'home': r'',
    r'example-open': r'home\.start|fill:examples\.search=.+|examples\.open\..+',
    r'project-details': (
        r'home\.start|project\.create|fill:createProject\.name=.+'
        r'|fill:createProject\.(title|location)=@\w+'
    ),
    r'project-created': r'createProject\.accept',
    r'(structure|experiment)-web-\d+|data-web': (
        r'structures\.load(\.web)?|experiments\.load(\.experimentWeb|\.dataWeb)?'
        r'|onlineLoad\.(source|search)|choose:EasyDiffraction Database'
        r'|fill:onlineLoad\.field\.id=.+'
    ),
    r'(structure|experiment)-loaded-\d+|data-loaded': r'onlineLoad\.row\.0',
    r'data-from-file': r'experiments\.load',
    r'data-from-file-closed': r'',
    r'fitting-mode-\w+|scan-mode': r'fittingMode\.type|choose-token:fittingMode\.type=\w+',
    r'minimizer': (
        r'minimizer\.stopRule|choose-token:minimizer\.(stopRule|descent)=\w+'
        r'|fill:minimizer\.maxIterations=\d+|fill:minimizer\.chiSquareTolerance=\S+'
    ),
    r'stage-\d+-fit|scan-fit': r'statusBar\.fit\.button',
    r'correlations': r'mainArea\.analysis\.tab\.correlations',
    r'calculated|report': r'',
}
# The plan steps whose actions set up a stage: walked action by action (setup_steps).
WALKED = re.compile(
    r'nothing-free|relations-start|background-estimate-.+|stage-\d+-free|group-filter|group-free-all'
    r'|structure-(created|cell|sites|adp)|experiment-(created|instrument|background|linked)'
)


def untranslated(case: str, item: dict) -> None:
    """Refuse a plan step holding an action no tutorial step performs and that is not inert."""
    ident = item['id']
    pattern = next((p for key, p in TRANSLATED.items() if re.fullmatch(key, ident)), None)
    if pattern is None:
        raise SystemExit(f'{case}: plan step {ident!r} has no translation into tutorial steps')
    for action in item['actions']:
        if not INERT.fullmatch(action) and not (pattern and re.fullmatch(pattern, action)):
            raise SystemExit(f'{case}: plan step {ident!r}: no tutorial step performs {action!r}')


# The by-hand steps and every stage's setup, one tutorial step per control action (owner record
# 59bd5f473): a field typed, an option chosen, a button pressed, the Free header's menu opened and
# its choice made. Navigation (pages, tabs, reveals, commit keys, waits) moves the callout only.
NAVIGATION = re.compile(
    r'(appBar\.tab\.\w+|sideBar\.tab\.\w+|reveal:.+|expand:.+|show:.+|key:Return'
    r'|platform:\w+|theme:\w+|pin-time:.+|wait-fit|wait-online|close-fit-results'
    r'|mainArea\.analysis\.tab\.fitting)'
)
# A button that adds a row, and the field naming each new row's index.
APPENDS = {
    'aliases.append': 'alias.id',
    'constraints.append': 'constraint.id',
    'atomSites.append': 'atomSite.label',
    'background.append': 'background.position',
    'excludedRegions.append': 'excludedRegion.start',
    'structures.create': 'structures.name',
    'experiments.create': 'experiments.name',
}
WORDS = {
    'atomSite.label': 'the label of site {n}',
    'atomSite.typeSymbol': 'the element of site {n}',
    'atomSite.wyckoffLetter': 'the Wyckoff position of site {n}',
    'atomSite.fractX': 'x of site {n}',
    'atomSite.fractY': 'y of site {n}',
    'atomSite.fractZ': 'z of site {n}',
    'atomSite.occupancy': 'the occupancy of site {n}',
    'atomSiteAdp.iso': 'the isotropic displacement of site {n}',
    'atomSiteAdp.type': 'the ADP type of site {n}',
    'alias.id': 'the id of alias {n}',
    'alias.parameter': 'the parameter of alias {n}',
    'constraint.id': 'the id of constraint {n}',
    'constraint.expression': 'the expression of constraint {n}',
    'background.position': 'the position of background point {n}',
    'background.intensity': 'the intensity of background point {n}',
    'excludedRegion.start': 'the start of excluded region {n}',
    'excludedRegion.end': 'the end of excluded region {n}',
    'structures.name': 'the structure name',
    'experiments.name': 'the experiment name',
    'linkedStructure.scale': 'the scale',
    'parameters.nameFilter': 'the name filter above the **Parameters** table',
    'parameters.value': "the shown parameter's value",
    'parameters.category': 'the category filter above the **Parameters** table',
    'parameters.datablock': 'the datablock filter above the **Parameters** table',
    'spaceGroup.nameHM': 'the space group',
    'cell.length_a': 'the cell length a',
    'background_estimate.n_points': 'the number of points of **Background estimation**',
    'background_estimate.use_model': 'the model of **Background estimation**',
}
APPEND_WORDS = {
    'aliases.append': 'Click **+** under **Aliases** to add an alias.',
    'constraints.append': 'Click **+** under **Constraints** to add a constraint.',
    'atomSites.append': 'Click **+** under **Atom sites** to add a site.',
    'background.append': 'Click **+** under **Background** to add a point.',
    'excludedRegions.append': 'Click **+** under **Excluded regions** to add a region.',
    'structures.create': 'Click **Create** to add a structure.',
    'experiments.create': 'Click **Create** to add an experiment.',
}
PAGES = {'structure', 'experiment', 'analysis', 'project', 'report', 'home'}


def control_words(control: str) -> str:
    """How a callout names a control: its row's number and what it holds."""
    match = re.fullmatch(r'(.+)\.(\d+)', control)
    base, row = (match[1], int(match[2])) if match else (control, 0)
    if base in WORDS:
        return WORDS[base].format(n=row + 1)
    return f'`{control.split(".", 1)[-1]}`'


def action_steps(case: str, item: dict, title: str, context: dict) -> list[dict]:  # noqa: PLR0912, PLR0915 - one branch per action family
    """A plan step's actions, each control action its own tutorial step; anything else refused."""
    actions = item['actions']
    out: list[dict] = []
    where = f'{case}: plan step {item["id"]!r}'

    def add(text: str, target: str, check: str) -> None:
        extra = {'tab': context['tab']} if context.get('tab') else {}
        out.append(step(title, text, context['page'], target, check, **extra))

    index = 0
    while index < len(actions):
        action = actions[index]
        following = actions[index + 1] if index + 1 < len(actions) else ''
        if match := re.fullmatch(r'appBar\.tab\.(\w+)', action):
            context['page'] = match[1] if match[1] in PAGES else context['page']
        elif match := re.fullmatch(r'sideBar\.tab\.(\w+)', action):
            context['tab'] = match[1]
        if NAVIGATION.fullmatch(action):
            index += 1
            continue
        if action in APPENDS:
            prefix = APPENDS[action]
            rows = [
                int(m[1])
                for a in actions[index + 1 :]
                if (m := re.fullmatch(rf'fill:{re.escape(prefix)}\.(\d+)=.*', a))
            ]
            if not rows:
                raise SystemExit(
                    f'{where}: {action!r} without a {f"fill:{prefix}.<row>"!r} after it'
                )
            add(APPEND_WORDS[action], action, f'rows:{action}={rows[0] + 1}')
            index += 1
        elif action.startswith('fill:'):
            control, value = action.removeprefix('fill:').split('=', 1)
            if control == 'parameters.nameFilter':
                context['word'] = value
            add(
                f'Enter **{value}** as {control_words(control)}.',
                control,
                f'field:{control}={value}',
            )
            index += 1
        elif following.startswith('type:') and not action.startswith(('fill:', 'type:', 'choose')):
            text = following.removeprefix('type:')
            add(
                f'Choose **{text.rstrip(":")}** as {control_words(action)}.',
                action,
                f'pick:{action}={text}',
            )
            index += 2
        elif following.startswith('choose:') and not action.startswith((
            'fill:',
            'type:',
            'choose',
        )):
            chosen = following.removeprefix('choose:')
            if action == 'parameters.category':
                context['category'] = chosen
            elif action == 'parameters.datablock':
                context['datablock'] = chosen
            add(
                f'Choose **{chosen}** as {control_words(action)}.',
                action,
                f'pick:{action}={chosen}',
            )
            index += 2
        elif action.startswith('choose-token:'):
            control, token = action.removeprefix('choose-token:').split('=', 1)
            add(
                f'Choose **{token}** as {control_words(control)}.',
                control,
                f'token:{control}={token}',
            )
            index += 1
        elif action == 'parameters.freeHeader':
            add(
                'Click the **Free** column header of the **Parameters** table.',
                action,
                'free-menu',
            )
            index += 1
        elif action in {'parameters.freeHeader.free', 'parameters.freeHeader.fixed'}:
            state = action.rsplit('.', 1)[1]
            spec = ':'.join([
                state,
                context.get('category') or 'All categories',
                context.get('datablock', ''),
                context.get('word', ''),
            ]).rstrip(':')
            add(f'Choose **{state.capitalize()} · all**.', action, 'free-choice:' + spec)
            index += 1
        elif action == 'parameters.clearFilters':
            if context.get('category') or context.get('datablock') or context.get('word'):
                add("Click the filters' **Clear** button.", action, 'filters-clear')
            context.update(category='', datablock='', word='')
            index += 1
        elif action == 'background.estimate':
            add('Press **Estimate** in the **Background** group.', action, 'background-estimated:')
            index += 1
        elif re.fullmatch(
            r'(background_estimate\.use_model|atomSiteAdp\.type\.\d+|alias\.parameter\.\d+|atomSite\.(typeSymbol|wyckoffLetter)\.\d+|spaceGroup\.nameHM|parameters\.(category|datablock)|experimentType\.\w+|minimizer\.\w+|fittingMode\.type)',
            action,
        ):
            index += 1  # the selector clicked open; its choice is the next action's step
        else:
            raise SystemExit(f'{where}: no tutorial step performs {action!r}')
    return out


def stage_texts(case: str, source: str) -> dict[int, tuple[str, str]]:
    """Each stage's title and the app page's sentence, with the page's groups."""
    if '## Perform the analysis' not in source:
        return {}
    declared = re.findall(
        r"^(\w+) = project\.(structures|experiments)\['([^']+)'\]$", source, flags=re.MULTILINE
    )
    kinds = [kind for _name, kind, _block in declared]
    several = kinds.count('structures') > 1 or kinds.count('experiments') > 1
    datablocks = {name: block for name, _kind, block in declared} if several else None
    tracker = Tracker(load_case(case), {name: block for name, _kind, block in declared})
    return {
        number: (
            stage['title'],
            stage_sentence(stage['edits'], tracker.stage(stage['edits']), datablocks),
        )
        for number, stage in enumerate(stages(source), start=1)
    }


def plan_step(  # noqa: PLR0911, PLR0912, PLR0914, PLR0915 - one branch per docs-plan step id
    case: str, item: dict, texts: dict, pending: list, context: dict
) -> list[dict]:
    """One docs-plan step as tutorial steps; a web search waits in `pending` for its load."""
    ident, actions = item['id'], item['actions']
    if WALKED.fullmatch(ident):
        if re.fullmatch(r'stage-\d+-free', ident):
            title, text = texts.get(int(ident.split('-')[1]), (item['description'], ''))
        elif ident == 'nothing-free':
            title = 'Start with nothing free'
            text = (
                'Open the **Free** column header of the **Parameters** table and fix every '
                'parameter.'
            )
        else:
            title, text = item['description'], ''
        del text
        return action_steps(case, item, title, context)
    untranslated(case, item)
    if ident == 'home':
        return [
            step(
                'Open Project',
                'Click **Start** to begin on the Project page.',
                'home',
                'home.start',
                'page:project',
            )
        ]
    if ident == 'example-open' and case == SIMULATION_CASE:
        return json.loads(BY_HAND_SIMULATION.read_text(encoding='utf-8'))['steps']
    if ident == 'example-open':
        return [
            step(
                'Find the example',
                f'In **Examples** on the Project page, type **{case}** in the search.',
                'project',
                'examples.search',
                f'examples-search:{case}',
            ),
            step(
                'Open the example',
                f'Click **{case}** to open it.',
                'project',
                f'examples.open.{case}',
                f'example:{case}',
            ),
        ]
    if ident == 'project-details':
        name = case if len(case) <= 31 else case.split('_', 1)[1]
        return [
            step(
                'New project',
                'Create a new project with **Create a new project**.',
                'project',
                'project.create',
                'creating',
            ),
            step(
                'Name the project',
                f'Give the project a name, for example **{name}**.',
                'project',
                'createProject.name',
                f'text:createProject.name={name}',
            ),
        ]
    if ident == 'project-created':
        return [
            step(
                'Create it',
                'Click **OK** to create the project.',
                'project',
                'createProject.accept',
                'project',
            )
        ]
    if re.fullmatch(r'(structure|experiment)-web-\d+', ident) or ident == 'data-web':
        # One visible action a step (owner record 59bd5f473): the Load menu, From web…, the search;
        # the row's click is the loaded step's.
        kind = 'data' if ident == 'data-web' else ident.split('-')[0]
        where = f'{case}: plan step {ident!r}'
        entry = need(where, actions, 'fill:onlineLoad.field.id=')[0].split('=', 1)[1]
        # The source the plan picks (structures), else the collection the dialog opens on.
        picked = [
            b for a, b in zip(actions, actions[1:], strict=False) if a == 'onlineLoad.source'
        ]
        if kind == 'structure' and not picked:
            raise SystemExit(f'{where}: no {"choose:"!r} action after onlineLoad.source')
        source = picked[0].removeprefix('choose:') if picked else 'EasyDiffraction'
        pending.append((kind, entry, item['description']))
        page = 'structure' if kind == 'structure' else 'experiment'
        button = 'structures.load' if kind == 'structure' else 'experiments.load'
        menu_entry = WEB_ENTRIES[kind]
        return [
            step('Open the Load menu', 'Click **Load ▾**.', page, button, f'menu:{menu_entry}'),
            step('From web', 'Choose **From web…**.', page, menu_entry, f'web-dialog:{kind}'),
            step(
                item['description'],
                f'With **{source}** as the **Source**, enter '
                f'**{entry}** as the **ID** and press **Search**.',
                page,
                'onlineLoad.search',
                f'web-search:{kind}:{entry}',
            ),
        ]
    if re.fullmatch(r'(structure|experiment)-loaded-\d+', ident) or ident == 'data-loaded':
        kind, entry, _description = pending.pop()
        name = entry.removeprefix(case + '-').removesuffix('-data')
        page = 'structure' if kind == 'structure' else 'experiment'
        text = f'Click the row of **{entry}** to load it.'
        return [
            step(
                item['description'],
                text,
                page,
                'onlineLoad.row.0',
                f'web-row:{kind}:{entry}={name}',
            )
        ]
    if ident.startswith('fitting-mode-') or ident == 'scan-mode':
        mode = 'sequential' if ident == 'scan-mode' else ident.removeprefix('fitting-mode-')
        text = f'On **Analysis → Extra**, choose the **{mode}** fitting mode.'
        return [
            step(
                'Fitting mode',
                text,
                'analysis',
                'group.fitting_mode',
                f'fitting-mode:{mode}',
                tab='extras',
            )
        ]
    if ident == 'minimizer':
        return minimizer_steps(actions)
    if ident == 'data-from-file':
        need(f'{case}: plan step {ident!r}', actions, 'experiments.load')
        return [
            step(
                'Open the Load menu',
                'Click **Load ▾**.',
                'experiment',
                'experiments.load',
                'menu:experiments.load.dataFile',
            )
        ]
    if ident == 'data-from-file-closed':
        need(f'{case}: plan step {ident!r}', actions, 'key:Escape')
        entry = 'experiments.load.dataFile'
        text = (
            'Measured data can also come from a file on your own disk: **From file…** reads it '
            'into the selected experiment. Press **Escape** to close the menu here.'
        )
        return [
            step('Measured data from a file', text, 'experiment', entry, f'menu-closed:{entry}')
        ]
    if re.fullmatch(r'stage-\d+-fit', ident) or ident == 'scan-fit':
        need(f'{case}: plan step {ident!r}', actions, 'statusBar.fit.button')
        return [
            step(
                item['description'],
                'Press **Fit** in the status bar.',
                'analysis',
                'statusBar.fit.button',
                'fit-done',
            ),
            step(
                'Fit results',
                'Read the fit results, then press **OK**.',
                'analysis',
                'fit.results.ok',
                'results-closed',
            ),
        ]
    if ident == 'correlations':
        text = 'The **Correlations** view shows which fitted parameters move together.'
        tab = 'mainArea.analysis.tab.correlations'
        return [step('Correlations', text, 'analysis', tab, 'open:' + tab)]
    if ident == 'calculated':
        text = 'On **Analysis**, the main view draws the pattern calculated from the model.'
        return [
            step(
                'The calculated pattern', text, 'analysis', 'appBar.tab.analysis', 'page:analysis'
            )
        ]
    if ident == 'report':
        text = 'The **Report** page collects the structure, the experiment and the fit.'
        return [step('Open Report', text, 'report', 'appBar.tab.report', 'page:report')]
    raise SystemExit(f'{case}: plan step {ident!r} has no translation into tutorial steps')


def tutorial_steps(case: str) -> list[dict]:
    """The case's docs plan as tutorial steps."""
    source = (TUTORIALS / f'{case}.py').read_text(encoding='utf-8')
    texts = stage_texts(case, source)
    pending: list = []
    context = {'page': 'project', 'tab': '', 'category': '', 'datablock': '', 'word': ''}
    steps: list[dict] = []
    for item in plan(case)['steps']:
        steps += plan_step(case, item, texts, pending, context)
    return steps


def tags(case: str, metadata: dict) -> list[str]:
    """The case's curated tags, as the Examples list shows them."""
    values = metadata['examples'][case]['values']
    return [f'{facet}:{value}' for facet in TAG_FACETS for value in values.get(facet, []) if value]


def build() -> dict:
    """The manifest: the hand-written built-ins, then every case's tutorial, LBCO first."""
    current = json.loads(MANIFEST.read_text(encoding='utf-8'))
    # The Interface tour is written by hand and stays.
    kept = [entry for entry in current['tutorials'] if entry['id'] in BUILT_INS]
    metadata = json.loads(METADATA.read_text(encoding='utf-8'))
    cases = sorted(metadata['examples'], key=lambda case: case != GETTING_STARTED)
    tutorials = sorted(kept, key=lambda entry: BUILT_INS.index(entry['id']))
    for case in cases:
        entry = metadata['examples'][case]
        origin = f' · {entry["origin"]}' if entry.get('origin') else ''
        tutorials.append({
            'id': case,
            'title': ' / '.join(entry['samples']) + origin,
            'description': entry.get('detail', ''),
            'project': 'temporary',
            'start': 'aside',
            'completion': ['keep', 'discard'],
            'stop': 'restore-user-project',
            'tags': tags(case, metadata),
            'steps': tutorial_steps(case),
        })
    return {'schema': current['schema'], 'tutorials': tutorials}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if MANIFEST.read_text(encoding='utf-8') != text:
            print('app/tutorials/manifest.json differs from the docs plans; run this script')
            return 1
        print('built-in tutorials match the docs plans')
        return 0
    MANIFEST.write_text(text, encoding='utf-8')
    print(f'wrote {MANIFEST.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
