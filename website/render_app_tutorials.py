#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write each case's Application tutorial from its imported capture.

    python website/render_app_tutorials.py BUNDLE [--dark DARK_BUNDLE]

The capture is the case's tutorial plan (tools/docs/app_tutorial_plan.py) run in the app. Its
images go to assets/gui/cases/<case>/ and the page to application/tutorials/cases/<case>.md, with
the stage headings and text of the case's Python tutorial, so the four interfaces read alike.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app_groups import Tracker, load_case, symbols  # noqa: E402
from checks.gui_capture import validate_bundle  # noqa: E402
from import_gui_captures import (  # noqa: E402
    DOCS,
    figure,
    guide_figures,
    load_scenes,
    page,
    viewer,
)
from render_cli_tutorials import stages  # noqa: E402

sys.path.insert(0, str(ROOT.parent / 'tools/docs'))
from app_tutorial_plan import plan  # noqa: E402

PAGES = DOCS / 'application/tutorials/cases'


def copy_bundle(bundle: Path, dark: Path | None, folder: str) -> Path:
    """The captured images and sidecars under assets/gui/<folder>/, dark images in dark/."""
    target = DOCS / 'assets/gui' / folder
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    # The inputs stay out: a tutorial loads its blocks from the collection.
    for name in ('manifest.json', 'walkthrough.js'):
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle / name, target / name)
    for scene in manifest['scenes']:
        if scene.get('status') == 'captured':
            for name in (scene['image'], scene['metadata']):
                shutil.copy2(bundle / name, target / name)
    if dark:
        hashes = {}
        (target / 'dark').mkdir()
        for scene in json.loads((dark / 'manifest.json').read_text())['scenes']:
            if scene.get('status') == 'captured':
                data = (dark / scene['image']).read_bytes()
                (target / 'dark' / scene['image']).write_bytes(data)
                hashes[scene['image']] = hashlib.sha256(data).hexdigest()
        (target / 'dark/hashes.json').write_text(
            json.dumps(hashes, indent=2, sort_keys=True) + '\n'
        )
    return target


def scenes_of(folder: Path, relative: str) -> dict[str, dict]:
    _, scenes = validate_bundle(folder, workflow='tutorial')
    hashes = folder / 'dark/hashes.json'
    dark = json.loads(hashes.read_text()) if hashes.is_file() else {}
    return {
        scene['id']: {
            **scene,
            'asset_folder': relative,
            'dark_sha256': dark.get(scene['image'], ''),
        }
        for scene in scenes
    }


# A step whose screenshot is not captured yet (owner, 2026-11-10: a warning, never a broken image).
PLACEHOLDER = (
    '<figure class="gui-figure gui-placeholder"><div class="gui-placeholder-box">'
    'Screenshot coming soon</div></figure>\n'
)


class Scenes:
    """A page's scenes by plan step: the captured ones, a placeholder for each step not captured.

    The docs plan says which steps the page shows and the capture supplies their screenshots. A
    step the capture lacks is recorded in `missing` and shown as the placeholder.
    """

    def __init__(self, captured: dict[str, dict], planned: dict[str, str]) -> None:
        self.captured, self.planned = captured, planned
        self.missing: list[str] = []

    def __contains__(self, key: object) -> bool:
        """Whether the plan has the step."""
        return key in self.planned

    def __iter__(self) -> object:
        """The plan's step ids, in its order."""
        return iter(self.planned)

    def __getitem__(self, key: str) -> dict:
        """The step's captured scene, else its placeholder."""
        if key in self.captured:
            return self.captured[key]
        if key not in self.planned:
            raise KeyError(key)
        if key not in self.missing:
            self.missing.append(key)
        return {'id': key, 'placeholder': True, 'description': self.planned[key]}

    def get(self, key: str, default: object = None) -> object:
        """The step's scene, or `default` when the plan lacks it."""
        return self[key] if key in self.planned else default


def shown(scene: dict) -> str:
    """A figure for a page three folders below the docs root, or the placeholder."""
    if scene.get('placeholder'):
        return PLACEHOLDER
    return figure(scene, interactive=False).replace('../assets/gui/', '../../../assets/gui/')


def freed(manifest: dict, scene: str) -> tuple[list[str], list[str]]:
    """What a stage's scene set free and fixed, from the actions the capture ran.

    Each is a parameter path, or `@<category>` for a category chosen in the table's filter.
    """
    out: tuple[list[str], list[str]] = ([], [])
    current = ''
    picking = False
    for item in manifest['actions']:
        action = item['action']
        if item.get('scene') != scene:
            continue
        if action.startswith('fill:parameters.nameFilter='):
            current = action.split('=', 1)[1]
        elif action == 'parameters.category':
            picking = True
        elif picking and action.startswith('choose:'):
            current = '@' + action.split(':', 1)[1]
            picking = False
        elif action in {'parameters.freeHeader.free', 'parameters.freeHeader.fixed'} and current:
            out[action.endswith('fixed')].append(current)
            current = ''
    return out


LEARNING_CASE = 'pd-neut-cwl_y2o3-spodi'


def guided(case: str, text: str) -> str:
    """The extras text with each registered section's guide figures (gui-guide-scenes.json)."""
    page_path = f'application/tutorials/cases/{case}.md'
    sections = json.loads((ROOT / 'gui-guide-scenes.json').read_text(encoding='utf-8')).get(
        page_path, {}
    )
    if not sections:
        return text
    by_id = {scene['id']: scene for scene in load_scenes('scan')}
    root = '../' * page_path.count('/')
    headings = list(re.finditer(r'^## (.+)$', text, re.MULTILINE))
    for number in reversed(range(len(headings))):
        title = headings[number][1]
        if title not in sections:
            continue
        scenes = sections[title]
        scenes = [scenes] if isinstance(scenes, str) else scenes
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        figures = guide_figures(by_id, page_path, Path(page_path), slug, scenes)
        end = headings[number + 1].start() if number + 1 < len(headings) else len(text)
        block = (
            f'\n<!-- gui-guide:{slug} -->\n'
            + '\n'.join(figures).replace('"../assets/', f'"{root}assets/')
            + '<!-- /gui-guide -->\n\n'
        )
        text = text[:end].rstrip() + '\n' + block + text[end:]
    return text


def searched(manifest: dict, prefix: str) -> list[str]:
    """The collection entries the From web scenes starting with `prefix` searched for."""
    return [
        item['action'].split('=', 1)[1]
        for item in manifest['actions']
        if item.get('scene', '').startswith(prefix)
        and item['action'].startswith('fill:onlineLoad.field.id=')
    ]


# What a tutorial's loop over a group's items is in the app's category filter.
GROUPS = (
    (r'\.background(_terms)?:$', 'Background'),
    (r'(\.adp_iso\.free|for component in|\.atom_site_aniso:)', 'Atomic displacement'),
    (r'(for coordinate in|\.fract_[xyz]\.free)', 'Atomic coordinates'),
    (r'\.linked_structures\[', 'Linked structures'),
)


def listed(items: list[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def loop_groups(text: str, state: str) -> list[str]:
    """The categories of a stage's loops that set `.free` to `state`; others refuse."""
    groups = []
    for block in re.split(r'^(?=\S)', text, flags=re.MULTILINE):
        frees = re.search(rf'\.free = (?:not .+|{state})$', block, flags=re.MULTILINE)
        if not block.startswith('for ') or not frees or (state == 'False' and 'not ' in block):
            continue
        if re.match(r'for \w+ in list\(\w+\.background_terms\)\[:\d+\]:', block):
            continue
        title = next(
            (title for pattern, title in GROUPS if re.search(pattern, block, re.MULTILINE)), ''
        )
        if not title:
            # A loop the app page cannot name would leave the stage without its action.
            raise SystemExit(f'a loop no category names:\n{block.strip()}')
        groups.append(f'**{title}**')
    return groups


def line_phrases(
    line_groups: list, groups: list[str], owners: set[str]
) -> tuple[list, list, list]:
    """Phrases for the line-by-line groups: one per category, naming the datablocks when several.

    Whole categories join `groups`; the rest come back as name-filter phrases, words to set back
    after a whole category, and parts set row by row.
    """
    merged: dict[tuple, list[str]] = {}
    for group in line_groups:
        key = (group.title, group.word, group.unword, group.part)
        merged.setdefault(key, []).append(group.block)
    names, again, again_rows = [], [], []
    for (title, filter_word, unword, part), blocks in merged.items():
        bold = listed([f'**{block}**' for block in blocks])
        where = f' of {bold}, choosing each in the datablock filter' if len(owners) > 1 else ''
        if filter_word:
            names.append(f'the **{title}** parameters with **{filter_word}** in their name{where}')
        elif part:
            again_rows.append(f'tick **Free** for the **{title}** {part}{where}')
        elif unword:
            names.append(f'the **{title}** parameters{where}')
            again.extend(unword.split())
        elif where:
            names.append(f'the **{title}** parameters{where}')
        elif f'**{title}**' not in groups:
            groups.append(f'**{title}**')
    return names, again, again_rows


def stage_sentence(
    edits: list[str],
    line_groups: dict[str, list] | None = None,
    datablocks: dict[str, str] | None = None,
) -> str:
    """A stage's free and fix actions in one sentence, in the app's words.

    The owner's rules (records b8df97176 and 7101f0fd9): every action is a category as the app's
    selector shows it, never a list of parameters. A loop over a group's items is its category;
    the parameters freed line by line come as `line_groups` (app_groups.py: a category, or part of
    one by one name-filter word), keyed by 'True' or 'False'. `datablocks` maps the tutorial's
    names to the structures and experiments of a project that has several: a stage on one of them
    filters the table to it first.
    """
    text = '\n'.join(edits)
    sentences: list[str] = []
    owners = {
        datablocks[name]
        for name in re.findall(r'^(?:for \w+ in )?(\w+)\.', text, flags=re.MULTILINE)
        if name in (datablocks or {})
    }
    # A loop setting every site's displacement type is a choice in each row on the Structure page.
    sentences += [
        f"on **Structure**, choose **{kind}** as every site's type in the **Atomic displacement** "
        'table'
        for _site, kind in re.findall(
            r"^for (\w+) in \w+\.atom_sites:\n\s+\1\.adp_type = '(\w+)'$", text, flags=re.MULTILINE
        )
    ]
    # A loop over a background's first terms frees them one by one, not the whole category.
    sentences += [
        f'tick **Free** for the first {count} **Background** coefficients'
        for count in re.findall(
            r'^for \w+ in list\(\w+\.background_terms\)\[:(\d+)\]:$', text, flags=re.MULTILINE
        )
    ]
    for state, word in (('True', 'Free · all'), ('False', 'Fixed · all')):
        groups = loop_groups(text, state)
        groups = list(dict.fromkeys(groups))
        names, again, again_rows = line_phrases((line_groups or {}).get(state, []), groups, owners)
        parts = []
        if groups:
            noun = 'parameters' if len(groups) == 1 else 'parameters, one category at a time,'
            parts.append(f'the {listed(groups)} {noun} using the category filter')
        parts.extend(
            f'{name} using the category filter'
            + (' and the name filter' if ' in their name' in name else '')
            for name in names
        )
        if parts:
            sentences.append(
                f'filter {listed(parts)}, click the **Free** column header and choose **{word}**'
            )
        sentences.extend(again_rows)
        other = 'Fixed · all' if state == 'True' else 'Free · all'
        sentences.extend(
            f'type **{rest}** in the name filter and choose **{other}** in the same menu'
            for rest in again
        )
    if not sentences:
        return 'Press **Fit** in the status bar.'
    joined = '; then '.join(sentences)
    if len(owners) == 1:
        joined = f'choose **{next(iter(owners))}** in the datablock filter, then {joined}'
    shown = symbols(joined)
    if len(shown) > 2:
        raise SystemExit(f'a stage sentence names {len(shown)} parameters, at most two: {shown}')
    return joined[0].upper() + joined[1:] + ', then press **Fit** in the status bar.'


def render(case: str) -> Path:  # noqa: PLR0912, PLR0914, PLR0915 - one page, section by section
    folder = DOCS / 'assets/gui/cases' / case
    steps = plan(case)['steps']
    captured = scenes_of(folder, f'cases/{case}') if (folder / 'manifest.json').is_file() else {}
    shot = {step['id']: step['description'] for step in steps if step.get('capture', True)}
    by_id = Scenes(captured, shot)
    # What the page says each step did comes from the plan, captured or not.
    manifest = {
        'actions': [{'action': a, 'scene': step['id']} for step in steps for a in step['actions']]
    }
    source = (ROOT.parent / 'docs/user/tutorials' / f'{case}.py').read_text(encoding='utf-8')
    title = re.search(r'^# # (.+)$', source, flags=re.MULTILINE).group(1)
    declared = re.findall(
        r"^(\w+) = project\.(structures|experiments)\['([^']+)'\]$", source, flags=re.MULTILINE
    )
    kinds = [kind for _name, kind, _block in declared]
    several = kinds.count('structures') > 1 or kinds.count('experiments') > 1
    datablocks = {name: block for name, _kind, block in declared} if several else None
    tracker = Tracker(load_case(case), {name: block for name, _kind, block in declared})
    shown_group = False
    body = [
        (
            'The same staged fit as the Python and Command line tutorials, in the app. Its '
            "structure and experiment come from EasyDiffraction's collection with **Load ▾ From "
            'web…**, and each stage frees its parameters in the **Parameters** table on '
            '**Analysis** before the fit.\n'
        ),
    ]
    if 'example-open' in by_id:
        body[0] = (
            "The same staged fit as the Python and Command line tutorials, in the app. A scan's "
            "patterns come with its project, so open it from EasyDiffraction's collection with "
            '**Project → Examples**; each stage frees its parameters in the **Parameters** table '
            'on **Analysis** before the fit.\n'
        )
        body += [
            '## Open the example\n',
            (
                f'Press **Start** on Home, search **Examples** on **Project** for **{case}** and '
                'open it.\n'
            ),
            shown(by_id['example-open']),
        ]
        if 'calculated' in by_id:
            # A calculation without data: nothing to fit.
            body[0] = (
                'The same calculation as the Python and Command line tutorials, in the app: open '
                "the example from EasyDiffraction's collection with **Project → Examples** and "
                'look at the pattern edi calculates from its model.\n'
            )
            body += [
                '## See the calculated pattern\n',
                (
                    'On **Analysis**, the main view draws the pattern calculated from the '
                    'structure and the instrument; there is nothing to fit.\n'
                ),
                shown(by_id['calculated']),
                '## Report\n',
                'The **Report** page collects the structure, the experiment and the pattern.\n',
                shown(by_id['report']),
            ]
            PAGES.mkdir(parents=True, exist_ok=True)
            out = PAGES / f'{case}.md'
            out.write_text(page(title, '\n'.join(body)), encoding='utf-8')
            return out
    else:
        panes = [
            (label, shown(by_id[key]))
            for key, label in (
                ('home', 'Start'),
                ('project-details', 'Details'),
                ('project-created', 'Created'),
            )
            if key in by_id
        ]
        body += [
            '## Create a project\n',
            'Press **Start** on Home, then **Create a new project**, and give it a name.\n',
            viewer(panes),
        ]
    built = [
        (key, label)
        for key, label in (
            ('structure-created', 'Structure'),
            ('structure-cell', 'Space group and cell'),
            ('structure-sites', 'Atom sites'),
            ('structure-adp', 'Displacements'),
        )
        if key in by_id
    ]
    if built:
        body += [
            '## Build the structure\n',
            (
                'On **Structure**, choose **Create structure** and name it, then set its space '
                'group and cell, add the atom sites and give each its displacement.\n'
            ),
            viewer([(label, shown(by_id[key])) for key, label in built]),
        ]
    made = [
        (key, label)
        for key, label in (
            ('experiment-created', 'Experiment'),
            ('data-web', 'Search'),
            ('data-loaded', 'Measured data'),
            ('experiment-instrument', 'Instrument and profile'),
            ('experiment-background', 'Background'),
            ('experiment-linked', 'Linked structure'),
        )
        if key in by_id
    ]
    if made:
        body += [
            '## Create the experiment\n',
            (
                'On **Experiment**, choose **Create experiment** and its type, load the measured '
                "data with **Load ▾ Measured data From web…** from EasyDiffraction's collection, "
                'then set the instrument, the peak widths, the background points and the excluded '
                'regions, and link the structure.\n'
            ),
            viewer([(label, shown(by_id[key])) for key, label in made]),
        ]
    for kind, page_name, menu in (
        ('structure', 'Structure', '**Load ▾ From web…**'),
        ('experiment', 'Experiment', '**Load ▾ Full experiment From web…**'),
    ):
        entries = searched(manifest, f'{kind}-web-')
        if not entries:
            continue
        listed = '\n'.join(f'- `{entry}`' for entry in entries)
        body.append(f'## Load the {kind}{"s" if len(entries) > 1 else ""}\n')
        body.append(
            f'On **{page_name}**, choose {menu}, search for each entry by its id and click it:'
            f'\n\n{listed}\n'
        )
        panes = [
            (label, shown(by_id[key]))
            for key, label in sorted(
                (key, 'Search' if '-web-' in key else 'Loaded')
                for key in by_id
                if key.startswith((f'{kind}-web-', f'{kind}-loaded-'))
            )
        ]
        body.append(viewer(sorted(panes, key=lambda pane: pane[0] != 'Search')))
    if 'data-from-file' in by_id:
        body += [
            '## Measured data from your own disk\n',
            (
                'Measured data can also come from a file on your own disk: on **Experiment**, '
                '**Load ▾ Measured data From file…** reads it into the selected experiment, or '
                'into a new one when none is selected.\n'
            ),
            shown(by_id['data-from-file']),
        ]
    if 'relations-start' in by_id:
        body += [
            '## Add the relations\n',
            (
                'The project ties some parameters together from the start. On **Analysis → '
                'Extra**, add the aliases and constraints.\n'
            ),
            shown(by_id['relations-start']),
        ]
    for key in sorted(k for k in by_id if k.startswith('background-estimate-')):
        body += [
            '## Estimate the background\n',
            (
                'On **Experiment → Extra**, set the number of points under **Background '
                'estimation**, then press **Estimate** in the **Background** group on **Main**.\n'
            ),
            shown(by_id[key]),
        ]
    if 'fitting-mode-single' in by_id:
        body += [
            '## Fit the template first\n',
            (
                'On **Analysis → Extra**, set the fitting mode to single, so the stages fit the '
                'template pattern alone.\n'
            ),
            shown(by_id['fitting-mode-single']),
        ]
    if 'fitting-mode-independent' in by_id:
        body += [
            '## Fit each experiment on its own\n',
            (
                'On **Analysis → Extra**, set the fitting mode to independent, so each experiment '
                'is fitted alone against its structure, with its own goodness of fit.\n'
            ),
            shown(by_id['fitting-mode-independent']),
        ]
    if 'minimizer' in by_id:
        body += [
            '## Set the minimizer\n',
            (
                "On **Analysis → Extra**, set the **Minimizer** as the case's project does: the "
                '**Shift/s.u.** stop rule and room for more iterations.\n'
            ),
            shown(by_id['minimizer']),
        ]
    body += [
        '## Start with nothing free\n',
        (
            'On **Analysis**, open the **Free** column header of the **Parameters** table and fix '
            'every parameter, so the stages below free one group at a time.\n'
        ),
        shown(by_id['nothing-free']),
    ]
    for number, stage in enumerate(stages(source), start=1):
        fit = by_id.get(f'stage-{number}-fit')
        if not fit:
            raise SystemExit(f'{case}: the docs plan has no stage {number}')
        body.append(f'## {stage["title"] or fit["description"]}\n')
        if stage['text']:
            body.append(' '.join(stage['text'].split()) + '\n')
        sentence = stage_sentence(stage['edits'], tracker.stage(stage['edits']), datablocks)
        if 'category filter' in sentence and 'group-filter' in by_id and not shown_group:
            # The one place the group action is shown (owner record b8df97176).
            shown_group = True
            body.append(
                'A group is freed in one action: choose it in the category filter above the '
                'table, then click the **Free** column header and choose **Free · all**.\n'
            )
            body.append(
                viewer([
                    ('Filter', shown(by_id['group-filter'])),
                    ('Free · all', shown(by_id['group-free-all'])),
                ])
            )
        body.append(sentence + '\n')
        body.append(shown(fit))
    if 'scan-fit' in by_id:
        body += [
            '## Fit the scan\n',
            (
                'Back on **Analysis → Extra**, set the fitting mode to sequential and press '
                '**Fit**: every pattern is fitted in turn, each from the fit before it.\n'
            ),
            viewer([('Mode', shown(by_id['scan-mode'])), ('Fitted', shown(by_id['scan-fit']))]),
        ]
    # A case's own extra sections (a scan's views and controls), with their guide figures.
    extras = ROOT / 'app_tutorial_extras' / f'{case}.md'
    if extras.is_file():
        body.append(guided(case, extras.read_text(encoding='utf-8')))
    if case == LEARNING_CASE:
        # render_learning.py writes the starting and fitted comparison here.
        body += [
            '## Starting and fitted patterns\n',
            '<!-- learning-comparison -->\n<!-- /learning-comparison -->\n',
        ]
    body += [
        '## Correlations\n',
        'The **Correlations** view on **Analysis** shows which fitted parameters move together.\n',
        shown(by_id['correlations']),
        '## Report\n',
        'The **Report** page collects the structure, the experiment and the fit.\n',
        shown(by_id['report']),
    ]
    PAGES.mkdir(parents=True, exist_ok=True)
    out = PAGES / f'{case}.md'
    out.write_text(page(title, '\n'.join(body)), encoding='utf-8')
    if by_id.missing:
        print(
            f'WARNING: {case}: no screenshot yet for {", ".join(by_id.missing)}', file=sys.stderr
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--dark', type=Path)
    args = parser.parse_args()
    case = json.loads((args.bundle / 'manifest.json').read_text())['example']
    copy_bundle(args.bundle, args.dark, f'cases/{case}')
    print(render(case))


if __name__ == '__main__':
    main()
