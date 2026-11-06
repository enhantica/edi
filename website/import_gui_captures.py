#!/usr/bin/env python3
"""Import a validated native walkthrough and generate its illustrated documentation."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from itertools import starmap
from pathlib import Path

from checks.gui_capture import validate_bundle
from render_interfaces import screenshot_radius

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'
LABELS = {
    'appBar': (
        'Workflow navigation',
        'Move between Home, Project, Structure, Experiment, Analysis and Report.',
    ),
    'statusBar': (
        'Status bar',
        'Read project counts, messages, calculation and fitting state here.',
    ),
    'home.start': ('Start', 'Begin a new analysis on the Project page.'),
    'project.create': ('Create a new project', 'Open the project-details form.'),
    'group.getStarted': ('Get started', 'Create a project or open an existing one.'),
    'createProject.name': ('Name', 'Use a short project identifier.'),
    'createProject.title': ('Title', 'Give the analysis a descriptive title.'),
    'createProject.description': ('Description', 'Record the sample, measurement and purpose.'),
    'createProject.location': ('Location', 'Choose where the project will be saved.'),
    'structures.load': ('Load structure', 'Import the structure file for this example.'),
    'structures.list': (
        'Structures',
        'Select the structure whose cell and atom sites you want to inspect.',
    ),
    'experiments.load': (
        'Load experiment',
        'Import the experiment file, including measured intensities and instrument settings.',
    ),
}

LABELS.update({
    'instrument.setup_wavelength': (
        'Wavelength',
        'Enter the wavelength used for this measurement, in ångströms.',
    ),
    'peak.type': ('Profile', 'Choose the peak-shape model for this measurement.'),
    'peak.broad_gauss_u': ('U', 'Set the starting Gaussian width coefficient U.'),
    'peak.broad_gauss_v': ('V', 'Set the starting Gaussian width coefficient V.'),
    'peak.broad_gauss_w': ('W', 'Set the starting Gaussian width coefficient W.'),
    'background_estimate.n_points': (
        'Number of points',
        'Choose the number of background anchors before estimating the baseline.',
    ),
    'group.parameters': (
        'Parameters',
        'Inspect values, uncertainties, bounds and the free parameter set.',
    ),
    'parameters.freeHeader': (
        'Free parameters',
        'Open the free header menu to fix or free the parameters matching the current filters.',
    ),
    'group.examples': (
        'Built-in examples',
        'Search or filter the example catalogue and select a case.',
    ),
    'project.openChoice': ('Project source', 'Choose a folder or a zip archive.'),
    'project.saveChoice': ('Save options', 'Choose the output format and whether to save a copy.'),
    'structures.create': ('Create structure', 'Add a starting structure to edit.'),
    'structures.duplicate': ('Duplicate structure', 'Copy the selected structure.'),
    'spaceGroup.itNumber': ('Space-group number', 'Select the symmetry of your model.'),
    'spaceGroup.nameHM': ('Space-group symbol', 'Check the Hermann-Mauguin symbol and setting.'),
    'cell.length_a': ('Cell length a', 'Inspect the cell length and its uncertainty.'),
    'cell.length_b': ('Cell length b', 'Values controlled by symmetry are linked.'),
    'cell.length_c': ('Cell length c', 'Use the cell convention of the selected space group.'),
    'atomSites.list': (
        'Atom sites',
        'Inspect atom types, fractional coordinates and occupancies.',
    ),
    'experiments.list': ('Experiments', 'Select the measurement to inspect.'),
    'experiments.loadData.0': (
        'Measured-data file',
        'Load the observed intensities for this experiment.',
    ),
    'experiments.create': (
        'Create experiment',
        'Add an experiment and choose its measurement type.',
    ),
    'background.type': ('Background model', 'Choose the background representation.'),
    'background.rows': (
        'Background values',
        'Inspect or edit the values in the selected representation.',
    ),
    'excludedRegions.list': (
        'Excluded intervals',
        'Set the boundaries of regions omitted from fitting.',
    ),
    'linkedStructure.list': (
        'Linked structures',
        'Inspect phase links, scales and derived fractions.',
    ),
    'fittingMode.type': ('Fitting mode', 'The available choices depend on the project.'),
    'report.writesHtml': ('HTML report', 'Select an HTML document.'),
    'report.writesPdf': ('PDF report', 'Select a PDF document.'),
    'report.writesCif': ('CIF report', 'Select a crystallographic report.'),
    'report.save': ('Save report', 'Write the selected report formats.'),
    'group.su_format': (
        'Standard uncertainties',
        'Choose how values and their standard uncertainties are written.',
    ),
    'group.appearance': (
        'Appearance',
        'Choose atom sizes, display scale and displacement ellipsoids.',
    ),
    'group.scattering_length': (
        'Scattering lengths',
        'Set custom neutron scattering lengths for atom types in this structure.',
    ),
    'group.scattering_source': (
        'Scattering source',
        'Choose the neutron scattering-length reference used by the experiment.',
    ),
    'group.instrument': (
        'Instrument',
        'Inspect the measurement conditions and calibration parameters.',
    ),
    'group.peak': ('Peak profile', 'Choose the peak shape and edit its profile parameters.'),
    'group.data': ('Measured data', 'Inspect the measured range, intensities and uncertainties.'),
    'group.absorption': (
        'Absorption',
        'Choose the sample absorption model and its physical parameters.',
    ),
    'group.preferred_orientation': (
        'Preferred orientations',
        'Set preferred directions and March parameters for linked structures.',
    ),
    'group.alias': ('Aliases', 'Give parameters short names for use in constraint expressions.'),
    'group.constraint': (
        'Constraints',
        'Define relations between aliased parameters and enable the relations to apply.',
    ),
    'group.minimizer': ('Minimizer', 'Choose the descent strategy and convergence settings.'),
    'group.shownParameters': (
        'Parameters shown',
        'Choose which additional parameter groups appear alongside free parameters.',
    ),
    'group.patternUpdates': (
        'Pattern updates during a scan',
        'Choose how often the display updates while a scan is fitted.',
    ),
    'peak.cutoff_fwhm': (
        'Peak cutoff',
        'Set the peak calculation window in multiples of the full width at half maximum.',
    ),
    'fitStart.list': (
        'Fit start values',
        'Inspect the free parameters before the last fit; use Undo to restore that state.',
    ),
})


PAGE_INTRODUCTIONS = {
    'project': 'Create or open a project and keep its details together.',
    'structure': 'Inspect the crystal structure and edit its symmetry, cell and atom sites.',
    'experiment': (
        'Compare the measured pattern with the calculation and configure the measurement model.'
    ),
    'analysis': (
        'Choose parameters to refine, run the fit and inspect the pattern and parameter '
        'correlations.'
    ),
    'report': 'Review the results and choose what to include in an exported report.',
}
MAIN_VIEW_DESCRIPTIONS = {
    'project': {
        'Project': ('Read the project details, location, structures and experiments in one view.')
    },
    'structure': {
        'Structure': (
            'Inspect the selected crystal structure and its unit cell in the interactive view.'
        )
    },
    'experiment': {
        'Pattern': (
            'Compare measured and calculated intensities, reflection marks and the '
            'residual pattern.'
        )
    },
    'analysis': {
        'Pattern': (
            'Inspect the fitted pattern, residual and agreement factors for the selected '
            'experiment.'
        ),
        'Correlations': (
            'Inspect correlations between refined parameters to identify strongly coupled values.'
        ),
    },
    'report': {
        'Report': (
            'Read the report preview for the current model and results before exporting it.'
        )
    },
}
SIDEBAR_DESCRIPTIONS = {
    (
        'project',
        'Main',
    ): 'Create or open a project, browse built-in examples and return to recent work.',
    (
        'structure',
        'Main',
    ): ('Select a structure and edit its symmetry, cell, atom sites and displacement parameters.'),
    (
        'experiment',
        'Main',
    ): (
        'Choose an experiment and edit its instrument, profile, background and linked structures.'
    ),
    (
        'analysis',
        'Main',
    ): ('Choose free parameters, inspect their values and bounds, and adjust the selected value.'),
    (
        'report',
        'Main',
    ): 'Choose output formats, save locations and the sections included in the report.',
    (
        'project',
        'Extra',
    ): 'Choose how standard uncertainties are displayed in the project data.',
    ('structure', 'Extra'): 'Adjust the structure appearance and scattering-length settings.',
    (
        'experiment',
        'Extra',
    ): 'Configure intensity corrections, scattering sources and background estimation.',
    (
        'analysis',
        'Extra',
    ): 'Configure fitting modes, minimizers, parameter aliases and constraints.',
}
SHARED_SIDEBAR_DESCRIPTIONS = {
    'Text': "Inspect or edit this page's project data in its text representation.",
    'Settings': (
        'Choose which parameters are shown and how the displayed pattern updates during a scan.'
    ),
}


def label(target: str, page: str, native_label: str = '') -> tuple[str, str]:
    if target in LABELS:
        return LABELS[target]
    if target.endswith('.mainContent'):
        return (
            'Main workspace',
            (
                f'Inspect the {page} view here. Its content changes with the active page and '
                'selection.'
            ),
        )
    if target.endswith('.manualSidebar'):
        return (
            'Sidebar',
            'Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.',
        )
    if target.endswith('.page'):
        return (
            'Workflow page',
            'The selected toolbar tab opens this workspace and its sidebar together.',
        )
    if target.startswith('group.'):
        title = native_label or re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', target[6:]).replace('_', ' ')
        return title[:1].upper() + title[1:], ''
    return native_label or target, ''


def _main_view_parts(meta: dict, target: str) -> list[list[float]]:
    _, name, key = target.split('.')
    tab = meta['items'][f'mainArea.{name}.tab.{key}']
    x, y, width, height = meta['items'][f'workflow.{name}.mainContent']['visible_bounds']
    tx, ty, tw, th = tab['visible_bounds']
    bottom = ty + th
    if not tab['enabled'] or not (
        x <= tx < tx + tw <= x + width and y <= ty < bottom < y + height
    ):
        raise ValueError('A main-view tab must be enabled and inside its workspace')
    return [[x, bottom, width, y + height - bottom], [tx, ty, tw, th]]


def _page_parts(meta: dict, target: str) -> list[list[float]]:
    name = target.split('.')[1]
    main = meta['items'][f'workflow.{name}.mainContent']['visible_bounds']
    tab = meta['items'][f'appBar.tab.{name}']['visible_bounds']
    if name == 'home':
        return [main, tab]
    sidebar = meta['items'][f'workflow.{name}.manualSidebar']['visible_bounds']
    x, y, width, height = main
    sx, sy, sw, sh = sidebar
    if abs(x + width - sx) > 0.1 or abs(y - sy) > 0.1 or abs(height - sh) > 0.1:
        raise ValueError('Workflow regions must form one adjoining page')
    return [[x, y, width + sw, height], tab]


def _sidebar_parts(meta: dict, bounds: list[float]) -> list[list[float]]:
    selected = [tab for tab in meta['state']['sidebar_tabs'] if tab['checked']]
    if len(selected) != 1:
        raise ValueError('A sidebar outline requires one selected native tab')
    tab = meta['items'].get(selected[0]['id'], {})
    if tab.get('ambiguous') or 'visible_bounds' not in tab:
        raise ValueError('The selected native tab has no unique visible geometry')
    tx, ty, tw, th = tab['visible_bounds']
    x, y, width, height = bounds
    bottom = ty + th
    if not (x <= tx < tx + tw <= x + width and y <= ty < bottom < y + height):
        raise ValueError('The selected tab must sit inside its sidebar')
    return [[x, bottom, width, y + height - bottom], [tx, ty, tw, th]]


def region_parts(meta: dict, target: str) -> list[list[float]]:
    """Join a sidebar's active tab to its body using this capture's Qt bounds."""
    if target.startswith('mainView.'):
        return _main_view_parts(meta, target)
    if target.endswith('.page'):
        return _page_parts(meta, target)
    bounds = meta['items'][target]['visible_bounds']
    if not target.endswith('.manualSidebar'):
        return [bounds]
    return _sidebar_parts(meta, bounds)


def region_path(parts: list[list[float]], padding: float = 2) -> str:
    """Trace a square outline; the browser adjusts padding to display pixels."""
    x, y, width, height = parts[0]
    left, top, right, bottom = x - padding, y - padding, x + width + padding, y + height + padding
    points = [(left, top)]
    if len(parts) == 2:
        tx, ty, tw, _ = parts[1]
        points += [
            (tx - padding, top),
            (tx - padding, ty - padding),
            (tx + tw + padding, ty - padding),
            (tx + tw + padding, top),
        ]
    points += [(right, top), (right, bottom), (left, bottom)]
    return 'M' + ' L'.join(f'{px:.3f} {py:.3f}' for px, py in points) + ' Z'


def gui_icon(item: dict) -> str:
    name = item.get('icon', '')
    if not name:
        return ''
    glyphs = json.loads((DOCS / 'assets/gui-icons/glyphs.json').read_text())
    code = ord(name) if len(name) == 1 and 0xE000 <= ord(name) <= 0xF8FF else glyphs.get(name)
    if code is None:
        raise ValueError(f'GUI icon is absent from the bundled Font Awesome 5 face: {name}')
    return f'<span class="gui-fa" aria-hidden="true">&#{code};</span>'


def pane(title: str, content: str) -> str:
    title = title.replace('"', "'")
    return (
        '\n=== "'
        + title
        + '"\n\n'
        + '\n'.join('    ' + line if line else '' for line in content.splitlines())
        + '\n'
    )


def viewer(panes: list[tuple[str, str]]) -> str:
    content = ''.join(starmap(pane, panes)) if len(panes) > 1 else panes[0][1]
    return '<div class="gui-viewer" markdown="1">\n\n' + content + '\n</div>\n'


def area_icon(area: str) -> str:
    icons = {
        'navigation': 'fa5-window-maximize',
        'main': 'fa5-desktop',
        'sidebar': 'fa5-columns',
        'status': 'fa5-window-minimize',
    }
    return (
        f'<span class="gui-area-icon" data-gui-area="{area}" '
        f'aria-hidden="true">:{icons[area]}:</span> '
    )


def highlight_area(meta: dict, target: str, page: str) -> str:
    """Use native item bounds to keep screenshot colours tied to the four app areas."""
    if target.startswith('appBar'):
        return 'navigation'
    if target.startswith('statusBar'):
        return 'status'
    if target.startswith('mainView.') or target.endswith(('.mainContent', '.page')):
        return 'main'
    if target.endswith('.manualSidebar'):
        return 'sidebar'
    x, y, width, height = meta['items'][target]['visible_bounds']
    centre_x, centre_y = x + width / 2, y + height / 2
    for name, area in [
        ('appBar', 'navigation'),
        ('statusBar', 'status'),
        (f'workflow.{page}.manualSidebar', 'sidebar'),
        (f'workflow.{page}.mainContent', 'main'),
    ]:
        item = meta['items'].get(name)
        if not item:
            continue
        left, top, width, height = item['visible_bounds']
        if (
            width > 0
            and height > 0
            and left <= centre_x <= left + width
            and top <= centre_y <= top + height
        ):
            return area
    raise ValueError('No native app area contains highlight: ' + target)


def _figure_targets(scene: dict, meta: dict, view: str, selection: str) -> list[str]:
    targets = (
        [f'workflow.{scene["page"]}.manualSidebar']
        if view == 'sidebar'
        else (
            [f'workflow.{scene["page"]}.mainContent']
            + ([f'workflow.{scene["page"]}.manualSidebar'] if scene['page'] != 'home' else [])
            if view == 'workflow'
            else meta['highlights']
        )
    )
    if view == 'main':
        targets = [f'mainView.{scene["page"]}.{selection.rsplit(".", 1)[1]}']
    return targets


def _navigation_outline(
    scene: dict, meta: dict, view: str, targets: list[str]
) -> tuple[list[str], str]:
    """Leave the page tab out of the highlights and outline it separately."""
    targets = [target for target in targets if target != 'appBar']
    empty = (
        scene['page'] == 'home'
        or (scene['page'] == 'structure' and not meta['state']['structures'])
        or (scene['page'] == 'experiment' and not meta['state']['experiments'])
    )
    if empty and view == 'overview':
        targets = [target for target in targets if not target.endswith('.mainContent')]
    tab = f'appBar.tab.{scene["page"]}'
    parts = region_parts(meta, tab)
    data = html.escape(json.dumps(parts, separators=(',', ':')), quote=True)
    navigation = (
        f'<path data-gui-navigation data-gui-area="navigation" data-gui-parts="{data}" '
        f'd="{region_path(parts)}" />'
    )
    return targets, navigation


def _interactive_figure(
    scene: dict, meta: dict, view: str, instance: str, targets: list[str]
) -> str:
    """Return one tab per highlighted region, each showing the same screenshot."""
    panes = []
    if view == 'layout':
        panes.append((
            'Overview',
            figure(
                scene,
                view=view,
                instance=instance,
                interactive=False,
                explanation=(
                    'The page bar, main view, sidebar and status bar stay in the same '
                    'places as you work.'
                ),
            ),
        ))
    for target in targets:
        item = meta['items'].get(target, {})
        title, text = label(target, scene['page'], item.get('label', ''))
        panes.append((
            (
                area_icon(highlight_area(meta, target, scene['page']))
                if view == 'layout'
                else gui_icon(item)
            )
            + html.escape(title),
            figure(
                scene,
                view=view,
                instance=instance,
                selection=target,
                interactive=False,
                description=title,
                explanation=text or scene['description'].rstrip('.') + '.',
            ),
        ))
    return viewer(panes)


def _region_paths(
    scene: dict, meta: dict, view: str, identity: str, targets: list[str]
) -> list[str]:
    paths = []
    for number, target in enumerate(targets, 1):
        inset = view in {'layout', 'flow'}
        parts = [meta['items'][target]['visible_bounds']] if inset else region_parts(meta, target)
        key = f'{identity}-{number}'
        data = html.escape(json.dumps(parts, separators=(',', ':')), quote=True)
        area = highlight_area(meta, target, scene['page'])
        active = 'is-active' if number == 1 or view in {'layout', 'flow', 'workflow'} else ''
        paths.append(
            (f'<path class="{active}" data-gui-region="{key}" data-gui-area="{area}" ')
            + ('data-gui-inset="2" ' if inset else '')
            + f'data-gui-parts="{data}" d="{region_path(parts, -2 if inset else 2)}" />'
        )
    return paths


def _flow_arrows(scene: dict, meta: dict) -> str:
    arrows = ''
    half = meta['items']['appBar']['visible_bounds'][3] * 0.18
    for axis, name in [
        ('x', 'appBar.workflow'),
        ('y', f'workflow.{scene["page"]}.manualSidebar'),
    ]:
        x, y, width, height = meta['items'][name]['visible_bounds']
        if axis == 'x':
            start, end, centre = (
                x + width * 0.08,
                x + width * 0.92,
                y + height * 0.5,
            )
            points = [
                (start, centre - half),
                (end - half * 2, centre - half),
                (end - half * 2, centre - half * 2),
                (end, centre),
                (end - half * 2, centre + half * 2),
                (end - half * 2, centre + half),
                (start, centre + half),
            ]
        else:
            start, end, centre = (
                y + height * 0.12,
                y + height * 0.88,
                x + width * 0.5,
            )
            points = [
                (centre - half, start),
                (centre + half, start),
                (centre + half, end - half * 2),
                (centre + half * 2, end - half * 2),
                (centre, end),
                (centre - half * 2, end - half * 2),
                (centre - half, end - half * 2),
            ]
        data = 'M' + ' L'.join(f'{px:.2f} {py:.2f}' for px, py in points) + ' Z'
        arrows += (
            '<path class="gui-direction is-active" data-gui-direction '
            f'data-gui-axis="{axis}" d="{data}" aria-hidden="true" />'
        )
    return arrows


def figure(
    scene: dict,
    *,
    view: str = 'overview',
    instance: str = '',
    description: str = '',
    explanation: str = '',
    selection: str = '',
    interactive: bool = True,
) -> str:
    meta = scene['layout']
    image = (
        '../assets/gui/'
        + scene.get('asset_folder', 'y2o3')
        + '/'
        + scene['image']
        + '?v='
        + meta['image_sha256'][:12]
    )
    description = html.escape(description or scene['description'], quote=True)
    identity = f'{scene["id"]}-{view}' + (f'-{instance}' if instance else '')
    if selection:
        identity += '-' + selection.replace('.', '-')
    targets = _figure_targets(scene, meta, view, selection)
    navigation = ''
    if view in {'overview', 'workflow'}:
        targets, navigation = _navigation_outline(scene, meta, view, targets)
    if interactive and view in {'overview', 'layout'}:
        return _interactive_figure(scene, meta, view, instance, targets)
    if selection and view != 'main':
        targets = [selection]
    paths = _region_paths(scene, meta, view, identity, targets)
    arrows = _flow_arrows(scene, meta) if view == 'flow' else ''
    clip = f'gui-clip-{identity}'
    return (
        '<figure class="gui-figure" data-gui-figure>\n'
        + (
            f'<p class="gui-view-description">{html.escape(explanation)}</p>\n'
            if explanation
            else ''
        )
        + f'<a class="gui-image-link" href="{image}" data-gui-open aria-haspopup="dialog" '
        f'aria-label="Enlarge screenshot: {description}">'
        f'<svg class="gui-capture" data-gui-view="{view}" viewBox="0 0 1480 800" '
        f'width="1480" height="800" role="img" aria-label="{description}">'
        f'<title>{description}</title><defs><clipPath id="{clip}"><rect width="1480" '
        f'height="800" rx="{screenshot_radius(1480):g}" /></clipPath></defs>'
        f'<image href="{image}" width="1480" height="800" clip-path="url(#{clip})" />'
        '<rect class="gui-image-frame" width="1480" height="800" '
        f'rx="{screenshot_radius(1480):g}" />'
        + ''.join(paths)
        + navigation
        + arrows
        + '</svg></a>\n'
        + '\n</figure>\n'
    )


def page(title: str, body: str, icon: str = '') -> str:
    meta = f'icon: {icon}\n' if icon else ''
    return f'---\n{meta}template: gui.html\n---\n\n# {title}\n\n{body.rstrip()}\n'


def native_options(text: str, by_id: dict[str, dict]) -> str:
    """Keep authored choice lists bound to the captured native selector model."""
    models = {
        (entry['category'], entry['id']): entry['explanation_url']
        for entry in json.loads((DOCS / 'physics/catalogue.json').read_text())['models']
    }

    def replace(match: re.Match[str]) -> str:
        scene, target, category = match.group(1, 2, 3)
        options = by_id[scene]['layout']['items'][target].get('options', [])
        if not options or len({item['token'] for item in options}) != len(options):
            raise ValueError(f'{scene}: {target} needs unique native options')
        rows = []
        for item in options:
            name = html.escape(item['label']).replace('|', '&#124;')
            if category:
                route = models[category, item['token']]
                name = f'[{name}](../physics/{route})'
            rows.append(f'- {name}')
        return match[0].split('\n', 1)[0] + '\n' + '\n'.join(rows) + '\n<!-- /gui-options -->'

    return re.sub(
        r'<!-- gui-options:([\w-]+):([\w.]+):([\w]*) -->\n.*?<!-- /gui-options -->',
        replace,
        text,
        flags=re.DOTALL,
    )


def _guide_figures(
    by_id: dict[str, dict], filename: str, source: Path, slug: str, scenes: list | dict
) -> list[str]:
    """Return the figures for one guide section; named scenes become tabs of one viewer."""
    figures = []
    choices = (
        list(scenes.items())
        if isinstance(scenes, dict)
        else [('', identity) for identity in scenes]
    )
    for index, (title, identity) in enumerate(choices):
        if identity not in by_id:
            raise ValueError(f'{filename}: required capture {identity} is missing')
        figures.append(
            figure(
                by_id[identity],
                instance=f'{source.stem}-{slug}-{index}',
                interactive=not title,
                explanation=by_id[identity]['description'] if title else '',
            )
        )
    if isinstance(scenes, dict):
        titles = []
        for title, identity in scenes.items():
            meta = by_id[identity]['layout']
            item = meta['items'][meta['highlights'][0]]
            titles.append(gui_icon(item) + html.escape(title))
        figures = [viewer(list(zip(titles, figures, strict=True)))]
    return figures


def illustrate_guides(by_id: dict[str, dict]) -> None:
    """Place source-matched scenes after their corresponding how-to instructions."""
    if 'guide-project-open' not in by_id:
        return
    registry = json.loads((ROOT / 'gui-guide-scenes.json').read_text())
    for filename, sections in registry.items():
        source = DOCS / filename
        text = native_options(source.read_text(), by_id)
        text = re.sub(r'<!-- gui-guide:.*?<!-- /gui-guide -->\n?', '', text, flags=re.DOTALL)
        text = re.sub(r'<figure class="gui-figure".*?</figure>\n?', '', text, flags=re.DOTALL)
        headings = list(re.finditer(r'^## (.+)$', text, re.MULTILINE))
        present = {match[1] for match in headings}
        missing = set(sections) - present
        if missing:
            raise ValueError(f'{filename}: missing authored headings {sorted(missing)}')
        for number in reversed(range(len(headings))):
            match = headings[number]
            if match[1] not in sections:
                continue
            scenes = sections[match[1]]
            if isinstance(scenes, str):
                scenes = [scenes]
            slug = re.sub(r'[^a-z0-9]+', '-', match[1].lower()).strip('-')
            figures = _guide_figures(by_id, filename, source, slug, scenes)
            end = headings[number + 1].start() if number + 1 < len(headings) else len(text)
            content = (
                f'\n<!-- gui-guide:{slug} -->\n' + '\n'.join(figures) + '<!-- /gui-guide -->\n\n'
            )
            text = text[:end].rstrip() + '\n' + content + text[end:]
        if not text.startswith('---\n'):
            text = '---\ntemplate: gui.html\n---\n\n' + text
        source.write_text(text.rstrip() + '\n')


def copy_bundle(bundle: Path, manifest: dict, scenes: list[dict], folder: str) -> None:
    destination = DOCS / 'assets/gui' / folder
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {'manifest.json', 'walkthrough.js'}
    artifacts.update(item['file'] for item in manifest['inputs'].values())
    artifacts.update(item['file'] for item in manifest.get('dependencies', []))
    if 'data' in manifest['inputs']:
        artifacts.update(
            str(path.relative_to(bundle))
            for path in (bundle / 'checkpoints').rglob('*')
            if path.is_file()
        )
    for scene in scenes:
        artifacts.update((scene['image'], scene['metadata']))
    for artifact in sorted(artifacts):
        target = destination / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        if (bundle / artifact).resolve() != target.resolve():
            shutil.copy2(bundle / artifact, target)


def capture_inventory() -> None:
    """Expose the executed action sequence without a second hand-maintained scene list."""
    lines = [
        '# GUI screenshot and action inventory',
        '',
        'Generated from the committed native capture manifests. Change `EXAMPLE_ID` in the',
        'corresponding native plan, run it, validate the bundle and import it again.',
        'The creation run starts empty and imports separate inputs. Reference runs open',
        'their declared example to illustrate controls specific to that project type.',
        '',
    ]
    for folder in ('y2o3', 'scan', 'joint'):
        directory = DOCS / 'assets/gui' / folder
        if not (directory / 'manifest.json').is_file():
            continue
        manifest = json.loads((directory / 'manifest.json').read_text())
        base = 'surfaces/docs/assets/gui/' + folder
        lines += [
            f'## {manifest["example"]}',
            '',
            f'[Executed plan]({base}/walkthrough.js) · [Native manifest]({base}/manifest.json)',
            '',
            '| Scene | Page / sidebar | Actions before capture | Highlights / result |',
            '| --- | --- | --- | --- |',
        ]
        scenes = {scene['id']: scene for scene in manifest['scenes']}
        identities = dict.fromkeys(
            [action['scene'] for action in manifest['actions']] + list(scenes)
        )
        current_page = 'home'
        for identity in identities:
            scene = scenes.get(identity, {'id': identity, 'status': 'action only'})
            actions = []
            for item in manifest['actions']:
                if item['scene'] != scene['id']:
                    continue
                action = item['action']
                if action.startswith('appBar.tab.'):
                    current_page = action.rsplit('.', 1)[1]
                if action.startswith('fill:'):
                    action = action.split('=', 1)[0]
                elif action.startswith(('import-structure:', 'import-experiment:')):
                    action = action.split(':', 1)[0] + ':<selected input>'
                actions.append('`' + action.replace('|', '&#124;') + '`')
            title = scene['id']
            current_page = scene.get('page', current_page)
            result = scene['status']
            if result == 'captured':
                metadata = json.loads((directory / scene['metadata']).read_text())
                title = f'[{title}]({base}/{scene["image"]})'
                result = ', '.join('`' + target + '`' for target in metadata['highlights'])
            lines.append(
                f'| {title} | {current_page} / {scene.get("sidebar") or "—"} | '
                + ' → '.join(actions)
                + f' | {result} |'
            )
        lines.append('')
    (ROOT / 'GUI-SCENES.md').write_text('\n'.join(lines))


def _import_references(reference: Path | None, joint: Path | None, by_id: dict) -> None:
    """Copy the scan and joint-fit reference bundles and name their examples in the guides."""
    for folder, provided in (('scan', reference), ('joint', joint)):
        reference_path = provided or DOCS / 'assets/gui' / folder
        if provided is None and not (reference_path / 'manifest.json').is_file():
            continue
        reference_manifest, reference_scenes = validate_bundle(
            reference_path, workflow='reference'
        )
        copy_bundle(reference_path, reference_manifest, reference_scenes, folder)
        for scene in reference_scenes:
            if scene['id'] in by_id:
                raise ValueError('Reference and creation scene ids must be distinct')
            by_id[scene['id']] = {**scene, 'asset_folder': folder}
        source = DOCS / (
            'application/scans.md' if folder == 'scan' else 'application/fitting-modes.md'
        )
        text = source.read_text()
        text = re.sub(
            r'<!-- ' + folder + r'-example -->.*?<!-- /' + folder + r'-example -->',
            '<!-- '
            + folder
            + '-example -->\nThis example is **'
            + reference_manifest['example']
            + '**: '
            + ' + '.join(reference_manifest['fixture']['samples'])
            + ', '
            + reference_manifest['fixture']['origin']
            + '.\n<!-- /'
            + folder
            + '-example -->',
            text,
            flags=re.DOTALL,
        )
        source.write_text(text)


def _creation_steps(manifest: dict, fixture: dict) -> tuple[str, list]:
    """Return the introduction and steps for a walkthrough that imports two project files."""
    structure_file = Path(manifest['inputs']['structure']['file']).name
    experiment_file = Path(manifest['inputs']['experiment']['file']).name
    intro = f"""Build a project from its separate inputs, refine the model and review the report. \
This example is **{manifest['example']}**: {' + '.join(fixture['samples'])}, {fixture['origin']}.

Use the tabs to highlight parts of the interface. The [application layout](workspace.md) \
introduces the workspace and every enabled sidebar tab.

## Download the inputs

- [Crystal structure: {structure_file}](\
../assets/gui/y2o3/{manifest['inputs']['structure']['file']})
- [Experiment and measured intensities: {experiment_file}](\
../assets/gui/y2o3/{manifest['inputs']['experiment']['file']})

The experiment input contains the measured pattern, instrument, profile, background and starting \
free parameters. Import these files separately; start with an empty project.
"""
    sections = [
        ('Home', 'Open EasyDiffraction and press **Start**.', '01-home'),
        ('Create a project', 'Choose **Create a new project**.', '02-project-start'),
        (
            'Enter the project details',
            (
                'Enter a name, title, authors and description for the analysis. Choose a '
                'location on your computer, then confirm.'
            ),
            '03-project-details',
        ),
        (
            'Inspect the project',
            (
                'The Project page keeps the analysis details together. The enabled sidebar '
                'tabs offer additional views of this state.'
            ),
            '04-project-created',
        ),
        (
            'Load the structure',
            (
                'Open **Structure**, expand **Structures**, choose **Load structure from '
                f'file** and select **{structure_file}**.'
            ),
            '06-structure-import',
        ),
        (
            'Inspect the crystal structure',
            (
                'Inspect the cell, symmetry and atom sites. See '
                '[crystallography](../physics/crystallography.md) and [atomic displacement '
                'parameters](../physics/displacement.md) for their physical meaning.'
            ),
            '07-structure-loaded',
        ),
        (
            'Load the experiment',
            (
                'Open **Experiment**, expand **Experiments**, choose **Load experiment** '
                f'and select **{experiment_file}**.'
            ),
            '09-experiment-import',
        ),
        (
            'Inspect the initial pattern',
            (
                'Compare the measured and calculated intensities before fitting. Review the '
                '[peak profile](../physics/profiles/cw.md), '
                '[background](../physics/background.md), reflection marks and residual.'
            ),
            '10-experiment-loaded',
        ),
        (
            'Refine the model',
            (
                'Open **Analysis**, inspect the free parameters and press **Fit**. Wait for '
                'fitting to finish, review the result and close the results popup. The '
                'calculated peaks should follow the measured pattern and the residual should '
                'be smaller. See [Rietveld refinement](../physics/rietveld.md), '
                '[uncertainties](../physics/minimization.md) and [reliability '
                'factors](../physics/reliability.md).'
            ),
            '13-analysis-basic',
        ),
        (
            'Review the report',
            (
                'Open **Report** to review the structure, measurement and fitted results. '
                'Use the sidebar to choose the report contents and export format.'
            ),
            '14-report-basic',
        ),
    ]
    return intro, sections


def _exclusion_intervals(by_id: dict, exclusion_scenes: list[str]) -> list[str]:
    intervals = []
    for name in exclusion_scenes:
        index = name.rsplit('-', 1)[1]
        items = by_id[name]['layout']['items']
        intervals.append(
            items[f'excludedRegion.start.{index}']['label']
            + ' to '
            + items[f'excludedRegion.end.{index}']['label']
            + '°'
        )
    return intervals


def _experiment_type_labels(by_id: dict) -> list[str]:
    type_items = by_id['09-experiment-type']['layout']['items']
    return [
        next(
            option['label']
            for option in type_items[key]['options']
            if option['token'] == type_items[key]['selected']
        )
        for key in [
            'experimentType.sampleForm',
            'experimentType.beamMode',
            'experimentType.radiationProbe',
        ]
    ]


def _measured_data_steps(manifest: dict, fixture: dict, by_id: dict) -> tuple[str, list]:
    """Return the introduction and steps for a walkthrough that starts from measured data."""
    structure_file = Path(manifest['inputs']['structure']['file']).name
    measured_file = Path(manifest['inputs']['data']['file']).name
    wavelength = by_id['09-wavelength']['layout']['items']['instrument.setup_wavelength']['label']
    background_items = by_id['09-background-settings']['layout']['items']
    points = background_items['background_estimate.n_points']['label']
    intro = f"""Create a refinement from a crystal-structure CIF and a measured diffraction \
pattern. This example uses {' + '.join(fixture['samples'])} measured on {fixture['origin']}.

The [application layout](workspace.md) introduces the controls. Follow the steps below in the web \
or desktop app.

## Download the inputs

- [Crystal structure: {structure_file}](\
../assets/gui/y2o3/{manifest['inputs']['structure']['file']})
- [Measured data: {measured_file}](../assets/gui/y2o3/{manifest['inputs']['data']['file']}) — \
scattering angle, intensity and standard uncertainty.

Start with an empty project. Set up the experiment in the app; the measured-data file does not \
supply the wavelength, profile or background.
"""
    profile_scenes = ['09-profile'] + [
        name for name in by_id if name.startswith('09-profile-broad-')
    ]
    exclusion_scenes = [name for name in by_id if name.startswith('09-exclusion-')]
    intervals = _exclusion_intervals(by_id, exclusion_scenes)
    type_labels = _experiment_type_labels(by_id)
    sections = [
        ('Home', 'Press **Start** to begin.', '01-home'),
        ('Create a project', 'Choose **Create a new project**.', '02-project-start'),
        (
            'Enter project details',
            (
                'Give the analysis a name, title and description, choose where to keep '
                'it, then confirm.'
            ),
            '03-project-details',
        ),
        (
            'Inspect the project',
            'Check the project details before adding a structure and measurement.',
            '04-project-created',
        ),
        (
            'Load the structure',
            (
                'Open **Structure → Main**, expand **Structures**, choose **Load '
                f'structure from file** and select **{structure_file}**.'
            ),
            '06-structure-import',
        ),
        (
            'Inspect the crystal structure',
            (
                'Check the cell, space group and atom sites. The [structure '
                'model](../physics/crystallography.md) describes their meaning.'
            ),
            '07-structure-loaded',
        ),
        (
            'Create an experiment',
            (
                'Open **Experiment → Main**, expand **Experiments** and choose **Create '
                'experiment**.'
            ),
            '09-experiment-import',
        ),
        (
            'Choose the measurement type',
            'Before loading data, choose '
            + ', '.join('**' + value + '**' for value in type_labels)
            + (
                ' for this measurement. [Experiment '
                'labels](../user-guide/glossary.md#experiment-types-and-labels) distinguish these attributes.'
            ),
            '09-experiment-type',
        ),
        (
            'Load measured data',
            (
                'Choose **Load data…** in the experiment row and select '
                f'**{measured_file}**. Check the measured range and intensities.'
            ),
            '09-experiment-data',
        ),
        (
            'Set the wavelength',
            (
                f'Expand **Instrument** and enter **{wavelength} Å** for this '
                'measurement. Use the wavelength from your own measurement when working '
                'with other data.'
            ),
            '09-wavelength',
        ),
        (
            'Choose the peak profile',
            (
                'Expand **Peak profile**, choose the profile shown below and set its '
                'starting coefficients. These values are starting estimates; refine the '
                'widths later. See [constant-wavelength '
                'profiles](../physics/profiles/cw.md).'
            ),
            profile_scenes,
        ),
        (
            'Exclude unwanted regions',
            'Expand **Excluded regions**, use **Append new region** and enter '
            + ', '.join(intervals)
            + (
                ' for this example. Exclude a region for a stated reason, rather than to '
                'hide disagreement.'
            ),
            exclusion_scenes[-1],
        ),
        (
            'Estimate the background',
            (
                'On **Experiment → Extra**, expand **Background estimation** and set '
                'the number of points to '
                f'**{points}**. '
                'Return to **Main**, expand **Background** and press **Estimate**. '
                'Inspect the baseline between peaks before refining. See [background '
                'models](../physics/background.md).'
            ),
            ['09-background-settings', '09-background-estimate'],
        ),
        (
            'Inspect the starting pattern',
            (
                'Compare peak positions, widths, intensities and the residual. Correct '
                'the experiment setup before freeing more parameters.'
            ),
            '10-experiment-loaded',
        ),
        (
            'Fit the scale and cell',
            (
                'Open **Analysis → Main**. Use the **free** header to fix all '
                'parameters. Filter by `scale`, choose **free → Free · all …**, then '
                'repeat for `length_a`. Clear the filters, press **Fit**, inspect the '
                'result and close the popup.'
            ),
            ['12-analysis-choose', '12-fit-scale-cell'],
        ),
        (
            'Refine widths and calibration',
            (
                'Keep the scale and cell free. Repeat the filter-and-free action for '
                '`broad_gauss_` and `calib_twotheta_offset` to add the Gaussian widths '
                'and 2θ offset. Clear the filters and press **Fit** again. Inspect the '
                'peak shapes and residual before continuing.'
            ),
            '12-fit-profile',
        ),
        (
            'Refine the structural model',
            (
                'Repeat the filter-and-free action for `background` and `fract_` to add '
                'background values and independent atom coordinates. Clear the filters. '
                'Keep displacement parameters fixed in this first fit; their [advanced '
                'refinement](displacement.md) requires additional physical checks. Press '
                '**Fit**, inspect the outcome and close the result popup. '
                'Symmetry-related quantities remain linked. See '
                '[refinement](../physics/rietveld.md) and [fit '
                'assessment](../user-guide/analysis-workflow/analysis.md#fit-quality).'
            ),
            '13-analysis-basic',
        ),
        (
            'Inspect correlations',
            (
                'Choose **Correlations** in the main view. Strong correlations show '
                'parameters that are difficult to distinguish using these observations; '
                'review the free set and physical model.'
            ),
            '12-correlations',
        ),
        (
            'Review the report',
            (
                'Open **Report**. Check the fitted structure, measurement and results, '
                'then choose the report contents and export format.'
            ),
            '14-report-basic',
        ),
    ]
    return intro, sections


def _write_first_refinement(manifest: dict, by_id: dict) -> None:
    fixture = manifest.get('fixture', {'samples': ['Y₂O₃'], 'origin': 'SPODI @ FRM II'})
    if 'data' in manifest['inputs']:
        intro, sections = _measured_data_steps(manifest, fixture, by_id)
    else:
        intro, sections = _creation_steps(manifest, fixture)
    checkpoints = {
        '04-project-created': 'The Project page now shows your project name and details.',
        '07-structure-loaded': (
            'The structure appears in the main view and the Structures count is one.'
        ),
        '10-experiment-loaded': (
            'The measured pattern, calculated curve, reflection marks and residual are visible.'
        ),
        '13-analysis-basic': (
            'Check the fit status, agreement factors and parameter uncertainties before '
            'continuing.'
        ),
    }
    body = intro
    for title, explanation, identity in sections:
        body += f'\n## {title}\n\n{explanation}\n\n'
        if isinstance(identity, list):
            body += viewer([
                (
                    {
                        '09-profile': 'Profile',
                        '12-analysis-choose': 'Free parameters',
                        '12-fit-scale-cell': 'Result',
                        '09-background-settings': 'Estimation settings',
                        '09-background-estimate': 'Estimated background',
                    }.get(key, key.rsplit('-', 1)[-1].upper()),
                    figure(by_id[key], instance='walkthrough-' + key),
                )
                for key in identity
            ])
        else:
            body += figure(by_id[identity])
        if identity == '13-analysis-basic':
            body += '\n<!-- learning-comparison -->\n<!-- /learning-comparison -->\n'
        if isinstance(identity, str) and identity in checkpoints:
            body += f'\n{checkpoints[identity]}\n'
    body += (
        '\n## Save the project\n\nReturn to **Project** and choose **Save project as…**. '
        'Keep the complete project as a folder or zip archive; the report is a separate '
        'export.\n\n'
    ) + figure(by_id['guide-project-save'], instance='walkthrough-save')
    body += (
        '\n!!! note "Keep the project as well as the report"\n\n    A report is an export of '
        'the result. Keep the saved project to reopen the model, change parameters or repeat '
        'the fit. In the browser, [check the save '
        'location](browser.md#open-and-save-files).\n'
    )
    body += (
        '\n## Try it\n\nChange the cell length **a** slightly on **Structure** and watch the '
        'peak positions move. Use **Undo** to restore the fitted model.\n\n??? tip "Where to '
        'look"\n\n    Expand **Cell** on **Structure → Main**. A cell change affects peak '
        'positions; compare several peaks across the pattern.\n'
    )
    body += (
        '\n## Continue with the same project\n\nOpen the saved project in '
        '[Python](../python/examples/index.md) or run it from the [Command '
        'Line](../cli/examples/index.md). Try [joint refinement](refine.md) or a [scan](scans.md) '
        'when you are ready for several measurements.\n'
    )
    (DOCS / 'application/first-refinement.md').write_text(page('Example refinement', body))


def _page_panes(name: str, modes: list[dict], by_id: dict, manifest: dict) -> list:
    """Return the overview, main-view and sidebar tabs that illustrate one workflow page."""
    base = modes[0]
    panes = [
        (
            'Overview',
            figure(
                base,
                view='workflow',
                description=f'{name.title()} overview',
                explanation=PAGE_INTRODUCTIONS[name],
            ),
        )
    ]
    tabs = sorted(
        (
            (key, item)
            for key, item in base['layout']['items'].items()
            if key.startswith(f'mainArea.{name}.tab.') and item['enabled']
        ),
        key=lambda pair: pair[1]['visible_bounds'][0],
    )
    for index, (key, item) in enumerate(tabs):
        selected = base
        if index:
            captures = [
                by_id[action['scene']]
                for action in manifest['actions']
                if action['action'] == key and action['scene'] in by_id
            ]
            if not captures:
                raise ValueError(f'Enabled main-view tab has no capture: {key}')
            selected = captures[-1]
        title = html.escape(item['label'])
        panes.append((
            area_icon('main') + f"<span class='gui-sr-only'>Main view: </span>{title}",
            figure(
                selected,
                view='main',
                selection=key,
                instance=key.rsplit('.', 1)[1],
                description=f'{name.title()} — Main view: {item["label"]}',
                explanation=MAIN_VIEW_DESCRIPTIONS[name].get(
                    item['label'], PAGE_INTRODUCTIONS[name]
                ),
            ),
        ))
    panes.extend(
        (
            area_icon('sidebar') + f"<span class='gui-sr-only'>Sidebar: </span>{scene['sidebar']}",
            figure(
                scene,
                view='sidebar',
                description=f'{name.title()} — Sidebar: {scene["sidebar"]}',
                explanation=SIDEBAR_DESCRIPTIONS.get(
                    (name, scene['sidebar']),
                    SHARED_SIDEBAR_DESCRIPTIONS.get(scene['sidebar'], PAGE_INTRODUCTIONS[name]),
                ),
            ),
        )
        for scene in modes
    )
    return panes


def _write_workspace(manifest: dict, scenes: list[dict], by_id: dict) -> None:
    workspace = """The interface follows the same analysis workflow as the [User \
guide](../user-guide/analysis-workflow/index.md). The top bar selects a page, the central \
workspace shows its main view, and the sidebar contains the related controls.

## Main regions

Choose a tab to inspect each region. These four areas stay in the same places on every workflow \
page.

"""
    workspace += figure(by_id['11-experiment-basic'], view='layout')
    workspace += (
        '\n## Following the workflow\n\nMove through the pages from left to right. Within '
        'each page, work down the sidebar from top to bottom.\n\n'
    )
    workspace += figure(
        by_id['11-experiment-basic'],
        view='flow',
        interactive=False,
        description=(
            'Follow the pages from left to right and the sidebar controls from top to bottom'
        ),
    )
    workspace += """
## Workflow pages

| Page | What you do here |
| --- | --- |
| Home | Start an analysis, learn the interface and find help. |
| Project | Create or open a project and record its details. |
| Structure | Load and inspect the crystal structure, cell and atom sites. |
| Experiment | Load measured intensities and configure the instrument, profile and background. |
| Analysis | Choose free parameters, run fitting and inspect the fitted pattern and results. |
| Report | Review and export a report of the analysis. |

## Sidebar tabs

**Main** contains the primary controls for the active page. **Extra** and **Settings** add \
controls where the page has them. Every page has a **Text** tab with the `.edi` text a save \
writes for what the page shows. Its **Show** box picks **Editable**, text you can change and \
apply with **✓**, or **Everything**, which adds the measured data and results and is read-only. A \
disabled tab has no available view in the current state.

The page views below introduce each enabled tab. Then follow [Example \
refinement](first-refinement.md) to build the analysis step by step.

## Selection and messages

Selecting a structure or experiment changes the model being inspected. The status bar reports the \
project state, messages and fitting progress. Its **Fit** button runs the fit from any page. Read \
messages after importing data or when an operation is refused.
"""
    gallery = (
        '\n## Page and sidebar views\n\nChoose **Overview** for the whole page. '
        + area_icon('main')
        + 'marks a main-view tab; '
        + area_icon('sidebar')
        + (
            'marks a sidebar tab. Only enabled tabs are shown. Analysis and Report show the '
            'completed refinement.\n'
        )
    )
    gallery += (
        '\n### :fa5-home: Home\n\nStart an analysis, learn the interface through '
        'built-in tutorials, read about EasyDiffraction, open the documentation or get in '
        'touch.\n\n'
    )
    gallery += figure(by_id['01-home'], view='workflow', description='Home overview')
    for name in ['project', 'structure', 'experiment', 'analysis', 'report']:
        icon = {
            'project': 'archive',
            'structure': 'layer-group',
            'experiment': 'microscope',
            'analysis': 'calculator',
            'report': 'clipboard-list',
        }[name]
        gallery += f'\n### :fa5-{icon}: {name.title()}\n'
        modes = [scene for scene in scenes if scene['page'] == name and scene['sidebar']]
        gallery += viewer(_page_panes(name, modes, by_id, manifest))
    (DOCS / 'application/workspace.md').write_text(
        page('Application layout', workspace + gallery, icon='fa5/columns')
    )


def _write_examples(by_id: dict) -> None:
    examples = (
        'The web and desktop applications both include built-in example projects. Go to '
        '**Project**, select **Main** and expand **Examples**. Use the search and '
        'filters to find a case.\n\n'
    )
    examples += figure(by_id['15-project-examples'])
    examples += (
        '\nChoose a **Fitting** example to analyse measured data, or a **Simulation** '
        'example to inspect a calculated pattern. Examples open as working copies; use '
        '**Save project as…** to keep your changes.\n\nFor a guided analysis, follow '
        '[Example refinement](../first-refinement.md). The shared [example '
        'catalogue](../../user-guide/examples/index.md#catalogue) lets you filter the '
        'scientific cases. '
        '[Experiment labels](../../user-guide/glossary.md#experiment-types-and-labels) '
        'explain the same tags shown in the app.\n'
    )
    (DOCS / 'application/examples/index.md').write_text(
        page('Example projects', examples.replace('"../assets/', '"../../assets/'))
    )


def _write_application_introduction(by_id: dict) -> None:
    introduction = DOCS / 'application/index.md'
    text = introduction.read_text()
    text = re.sub(
        r'<figure class="gui-figure".*?</figure>',
        figure(by_id['13-analysis-basic'], instance='application-introduction').rstrip(),
        text,
        count=1,
        flags=re.DOTALL,
    )
    introduction.write_text(text)


def render(bundle: Path, reference: Path | None = None, joint: Path | None = None) -> None:
    manifest, scenes = validate_bundle(bundle)
    copy_bundle(bundle, manifest, scenes, 'y2o3')
    by_id = {scene['id']: scene for scene in scenes}
    _import_references(reference, joint, by_id)
    _write_first_refinement(manifest, by_id)
    _write_workspace(manifest, scenes, by_id)
    if '15-project-examples' in by_id:
        _write_examples(by_id)
    _write_application_introduction(by_id)
    illustrate_guides(by_id)
    capture_inventory()
    print(json.dumps({'imported': len(scenes), 'source': manifest['source_revision']}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--reference-bundle', type=Path)
    parser.add_argument('--joint-bundle', type=Path)
    args = parser.parse_args()
    render(args.bundle.resolve(), args.reference_bundle, args.joint_bundle)


if __name__ == '__main__':
    main()
