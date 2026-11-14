#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Render experiment tags and a searchable catalogue from native app metadata."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from itertools import starmap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'
ASSETS = DOCS / 'assets/reference'

sys.path.insert(0, str(ROOT.parent / 'tools/checks'))
from case_records import SECTIONS  # noqa: E402 - the sections, in the navigation's order


def badge(family: str, token: str, *, prefix: str = '../') -> str:
    definitions = json.loads((ASSETS / 'experiment-tags.json').read_text())
    item = definitions['tags'][family][token]
    glyph = item.get('glyph', '')
    symbol = (
        f'<span class="ed-reference-icon" aria-hidden="true">{html.escape(glyph)}</span>'
        if glyph
        else ''
    )
    return (
        f'<a class="ed-tag ed-tag--{item["tone"]}" data-ed-tag="{family}" '
        f'data-ed-token="{html.escape(token, quote=True)}" '
        f'href="{prefix}user-guide/glossary/#{item["anchor"]}" '
        f'title="{html.escape(item["meaning"], quote=True)}">'
        f'{symbol}{html.escape(item["label"])}</a>'
    )


def replace(path: Path, key: str, content: str) -> None:
    start, end = '<!-- ' + key + ' -->', '<!-- /' + key + ' -->'
    text = path.read_text(encoding='utf-8')
    if start not in text:
        text += '\n\n' + start + '\n' + end + '\n'
    text, count = re.subn(
        re.escape(start) + '.*?' + re.escape(end),
        lambda _: start + '\n' + content + '\n' + end,
        text,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f'Duplicate marker {key}: {path}')
    path.write_text(text, encoding='utf-8')


def _write_tag_css(registry: dict) -> None:
    css = [
        '/* Generated from the app experiment tag registry. */',
        (
            '.ed-tag {display:inline-flex;align-items:center;gap:.28em;white-space:nowrap;'
            'border-radius:3px;padding:.08em .38em;margin:.12em .16em .12em '
            '0;font-size:.82em;line-height:1.5;text-decoration:none!important}'
        ),
        '.ed-tag .ed-reference-icon {margin:0}',
        (
            '.ed-tag:hover,.ed-tag:focus-visible {text-decoration:underline!important;'
            'outline-offset:2px}'
        ),
        # Two controls to a line, each the same width and height; the reset is square, beside the
        # search field (the owner, 2026-11-08).
        (
            '.ed-example-filters {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));'
            'gap:.5rem;margin-block:.7rem}'
        ),
        (
            '.ed-example-filters input,.ed-example-filters select,.ed-example-filters button '
            '{font:inherit;box-sizing:border-box;height:2.4em;width:100%;min-width:0;'
            'padding:.4em .6em;border:1px solid var(--md-default-fg-color--lightest);'
            'border-radius:5px;background:var(--md-default-bg-color);'
            'color:var(--md-default-fg-color)}'
        ),
        '.ed-example-search {display:flex;gap:.5rem;min-width:0}',
        (
            '.ed-example-search button {flex:none;width:2.4em;padding:0;display:inline-flex;'
            'align-items:center;justify-content:center;cursor:pointer}'
        ),
        '.ed-example-search button svg {width:1em;height:1em;fill:currentColor}',
        '.ed-example-name {display:block}',
        '.ed-example-tags {display:block;margin-top:.25em}',
        '.ed-tutorial-section th {font-weight:700}',
        # The table spans the content at every filter state, and a section row reads as a heading:
        # no hover, no side borders, the line above it drawn as the previous row's bottom edge (the
        # owner, 2026-11-09).
        '.md-typeset [data-example-catalogue] table:not([class]) {border:none}',
        (
            '.md-typeset [data-example-catalogue] tr:not(.ed-tutorial-section) > :first-child '
            '{border-left:.05rem solid var(--md-typeset-table-color)}'
        ),
        (
            '.md-typeset [data-example-catalogue] tr:not(.ed-tutorial-section) > :last-child '
            '{border-right:.05rem solid var(--md-typeset-table-color)}'
        ),
        (
            '.md-typeset [data-example-catalogue] thead th '
            '{border-top:.05rem solid var(--md-typeset-table-color)}'
        ),
        # The closing line under the last visible row (example-catalogue.js marks it after each
        # filter); the last row without the script.
        (
            '.md-typeset [data-example-catalogue] tbody tr:last-child td,'
            '.md-typeset [data-example-catalogue] tbody tr.ed-last-visible td '
            '{border-bottom:.05rem solid var(--md-typeset-table-color)}'
        ),
        (
            '.md-typeset [data-example-catalogue] .ed-tutorial-section th '
            '{border-top:.05rem solid var(--md-typeset-table-color);background:none}'
        ),
        (
            '.md-typeset [data-example-catalogue] tbody tr.ed-tutorial-section:hover '
            '{background-color:transparent;box-shadow:none}'
        ),
        '.ed-tutorial-section .twemoji {margin-right:.35em}',
        # An interface column is one icon plus its padding wide; the tutorial text takes the rest.
        '.ed-tutorial-link {text-align:center;white-space:nowrap;width:1%}',
        '.ed-tutorial-link svg {flex:none;width:1.2em;height:1.2em;fill:currentColor}',
        '[data-example-row][hidden],[data-tutorial-section][hidden] {display:none}',
    ]
    for tone, colors in registry['tones'].items():
        for scheme, key in [('default', 'light'), ('slate', 'dark')]:
            color = colors[key]
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
                raise ValueError('Invalid tag colour')
            css.append(
                f'[data-md-color-scheme="{scheme}"] .ed-tag--{tone} '
                f'{{color:{color};background:{color}21}}'
            )
    (DOCS / 'assets/experiment-tags.css').write_text('\n'.join(css) + '\n')


def _write_experiment_types(registry: dict) -> None:
    prose = {
        'purpose': (
            'Purpose',
            'Choose whether to calculate a model alone or fit it to observations.',
        ),
        'fittingMode': (
            'Fitting mode',
            (
                'Choose how experiments contribute to a fit. This is separate from their '
                'measurement type.'
            ),
        ),
        'sampleForm': (
            'Sample form',
            (
                'Powder profiles contain overlapping reflections; single-crystal data '
                'identify individual reflections.'
            ),
        ),
        'probe': (
            'Probe',
            (
                'Neutrons and X-rays interact with the sample differently. Select the probe '
                'used for the measurement.'
            ),
        ),
        'beamMode': (
            'Beam mode',
            (
                'Constant-wavelength powder data use scattering angle; time-of-flight data '
                'use arrival time and an instrument calibration.'
            ),
        ),
        'scatteringType': (
            'Scattering type',
            'Bragg diffraction describes the crystalline contribution from lattice reflections.',
        ),
        'structure': (
            'Structure',
            (
                'A crystal structure describes the atoms in the unit cell. A magnetic structure '
                'also gives each magnetic atom a moment.'
            ),
        ),
        'interface': (
            'Interface',
            'A tutorial that works with an AI assistant, built in or your own.',
        ),
    }
    meanings = {
        'fitting': (
            'Compare a calculated model with measured intensities and fit its parameters.'
        ),
        'simulation': 'Calculate the pattern from the current model without measured intensities.',
        'bragg-diffraction': 'Model the crystalline contribution from lattice reflections.',
        'single-fit': 'Fit one experiment.',
        'joint-fit': 'Fit several experiments together with shared model quantities.',
        'sequential-fit': (
            'Fit a scan in order, using the preceding result as the next starting point.'
        ),
        'independent-fit': 'Fit each dataset from the same starting model.',
        'powder-diffraction': (
            'Diffraction from many crystallite orientations, usually measured as an '
            'intensity profile.'
        ),
        'single-crystal-diffraction': (
            'Diffraction from an oriented crystal, measured as individual reflection intensities.'
        ),
        'neutron-diffraction': (
            'Diffraction using neutrons; nuclear scattering and, where modelled, magnetic '
            'scattering contribute.'
        ),
        'x-ray-diffraction': (
            'Diffraction using X-rays; the scattering model depends on the electron distribution.'
        ),
        'constant-wavelength': (
            'A specified incident wavelength; powder patterns are commonly expressed against 2θ.'
        ),
        'crystal-structure': 'Atoms, their positions and displacements in the unit cell.',
        'magnetic-structure': (
            'A crystal structure whose magnetic atoms also carry moments, related by magnetic '
            'symmetry.'
        ),
        'time-of-flight': (
            'Neutron wavelengths are separated by arrival time. Calibration relates flight '
            'time to diffraction geometry.'
        ),
        'ai-assistant': (
            'An assistant such as ChatGPT or Claude sets up and fits the project from your '
            'request.'
        ),
    }
    intro = (
        'An experiment combines one label from each family below. For example, the first '
        'fitting is '
        + ' '.join(
            starmap(
                badge,
                [
                    ('sampleForm', 'powder'),
                    ('probe', 'neutron'),
                    ('beamMode', 'constant wavelength'),
                ],
            )
        )
        + '. Choose the measurement type before loading data; a listed attribute does not imply '
        'every combination is available.'
    )
    blocks = [intro]
    seen = set()
    for family, values in registry['tags'].items():
        title, _explanation = prose[family]
        rows = ['### ' + title, '', '| Label | Meaning |', '| --- | --- |']
        for token, item in values.items():
            if item['anchor'] in seen:
                continue
            seen.add(item['anchor'])
            rows.append(
                '| <span id="'
                + item['anchor']
                + '"></span>'
                + badge(family, token)
                + ' | '
                + meanings.get(item['anchor'], item['meaning'])
                + ' |'
            )
        blocks.append('\n'.join(rows))
    replace(DOCS / 'user-guide/glossary.md', 'experiment-type-tables', '\n\n'.join(blocks))


def _badge_models_table(source: str, relative: str) -> str:
    """Replace beam-mode abbreviations in the model table with labels."""
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if line.startswith('|') and not line.startswith('| ---'):
            cells = line.split('|')
            if len(cells) == 5:
                cells[2] = re.sub(
                    r'\b(?:CW|CWL|TOF)\b',
                    lambda match, relative=relative: badge(
                        'beamMode',
                        'time-of-flight' if match[0] == 'TOF' else 'constant wavelength',
                        prefix=relative,
                    ),
                    cells[2],
                )
                lines[index] = '|'.join(cells)
    return '\n'.join(lines) + '\n'


# The Features page's experiment-type tags (owner record 2026-11-09), from one declared mapping.
FEATURE_TYPES = ROOT / 'feature_types.yml'
TYPE_TOKENS = {
    'pd': ('sampleForm', 'powder'),
    'sc': ('sampleForm', 'single crystal'),
    'neut': ('probe', 'neutron'),
    'xray': ('probe', 'xray'),
    'cwl': ('beamMode', 'constant wavelength'),
    'tof': ('beamMode', 'time-of-flight'),
}
ALL_TYPES = (
    '<span class="ed-tag ed-tag--neutral" data-ed-tag="all" '
    'title="Applies to every experiment type">All types</span>'
)
FEATURE_ROW = re.compile(
    r'^\| \[([^\]\n]+)\]\(([^)\n]+)\)((?: *<(?:a|span) class="ed-tag[^>]*>.*?</(?:a|span)>)*)'
)


def feature_types() -> dict[str, list]:
    """Each row text's declared types, one per row in page order: 'all' or a list of tokens."""
    rows = yaml.safe_load(FEATURE_TYPES.read_text(encoding='utf-8'))['rows']
    out = {}
    for text, value in rows.items():
        occurrences = (
            value['occurrences'] if isinstance(value, dict) and 'occurrences' in value else None
        )
        entries = occurrences if occurrences is not None else [value]
        out[text] = [entry['types'] if isinstance(entry, dict) else entry for entry in entries]
    return out


def feature_code(text: str) -> dict:
    """The experiment setting the code accepts only for some types, for a row that names one."""
    value = yaml.safe_load(FEATURE_TYPES.read_text(encoding='utf-8'))['rows'].get(text)
    return value.get('code', {}) if isinstance(value, dict) else {}


def _tag_features(source: str, relative: str) -> str:
    """Give every Features row its declared experiment-type tags, replacing any earlier ones."""
    declared = feature_types()
    seen: dict[str, int] = {}
    lines = source.splitlines()
    for index, line in enumerate(lines):
        match = FEATURE_ROW.match(line)
        if not match:
            continue
        entries = declared.get(match[1])
        if entries is None:
            raise SystemExit(f'Features row has no declared experiment types: {match[1]}')
        position = seen.get(match[1], 0)
        seen[match[1]] = position + 1
        if position >= len(entries):
            raise SystemExit(
                f'Features row {match[1]!r} occurs more often than its declared types'
            )
        types = entries[position]
        if types == 'all':
            tags = ALL_TYPES
        else:
            tags = ' '.join(badge(*TYPE_TOKENS[token], prefix=relative) for token in types)
        lines[index] = f'| [{match[1]}]({match[2]}) {tags}' + line[match.end() :]
    for text, entries in declared.items():
        if seen.get(text, 0) != len(entries):
            raise SystemExit(f'Features mapping row {text!r} matches {seen.get(text, 0)} rows')
    return '\n'.join(lines) + '\n'


def _features_filter(registry: dict) -> list[str]:
    """The tutorials catalogue's filter bar for Features: three types, search and reset."""
    selects = []
    for family, title in [
        ('sampleForm', 'Sample form'),
        ('probe', 'Probe'),
        ('beamMode', 'Beam mode'),
    ]:
        tokens = sorted({TYPE_TOKENS[t][1] for t in TYPE_TOKENS if TYPE_TOKENS[t][0] == family})
        labels = [(token, registry['tags'][family][token]['meaning']) for token in tokens]
        selects.append((family, title, labels))
    controls = _filter_bar(selects, 'feature', 'Search features', 'Search features')
    controls[0] = '<div class="ed-example-filters" data-feature-bar>'
    return [*controls, '</div>']


def _write_page_labels(registry: dict) -> None:
    tokens = {
        item['label']: (family, token)
        for family, values in registry['tags'].items()
        for token, item in values.items()
        if family in {'sampleForm', 'probe', 'beamMode'}
    }
    for path in DOCS.rglob('*.md'):
        source = path.read_text()
        relative = '../' * len(path.relative_to(DOCS).parent.parts)
        source = re.sub(
            r'<a class="ed-tag[^"\n]*" data-ed-tag="([^"\n]+)" '
            r'data-ed-token="([^"\n]+)"[^>]*>.*?</a>',
            lambda match, relative=relative: badge(
                match[1], html.unescape(match[2]), prefix=relative
            ),
            source,
        )
        if path.relative_to(DOCS).as_posix() == 'physics/models.md':
            source = _badge_models_table(source, relative)
        if path.relative_to(DOCS).as_posix() == 'user-guide/features.md':
            source = _tag_features(source, relative)
        blocks = re.split(r'(^```[^\n]*\n.*?^```[^\n]*$)', source, flags=re.MULTILINE | re.DOTALL)
        for index in range(0, len(blocks), 2):
            for label, (family, token) in tokens.items():
                blocks[index] = blocks[index].replace(
                    '`' + label + '`', badge(family, token, prefix=relative)
                )
        path.write_text(''.join(blocks))


def _filter_bar(selects: list, kind: str, label: str, placeholder: str) -> list[str]:
    """One filter bar, the tutorials catalogue's and the Features page's alike.

    Its selectors two to a line, then the search field and a square reset (the owner, 2026-11-08),
    sized by the same styles. `kind` names the data attributes the page's script reads
    (`data-<kind>-filter`, `-search`, `-reset`). The caller closes the returned `<div>`.
    """
    controls = ['<div class="ed-example-filters">']
    for family, title, labels in selects:
        options = ['<option value="">All ' + title.lower() + 's</option>']
        options.extend(
            f'<option value="{html.escape(token, quote=True)}">{html.escape(text)}</option>'
            for token, text in labels
        )
        controls.append(
            f'<select data-{kind}-filter="{family}" aria-label="{title}">'
            + ''.join(options)
            + '</select>'
        )
    reset = (ROOT / 'surfaces/overrides/.icons/fa5/eraser.svg').read_text(encoding='utf-8')
    reset = re.sub(r'<!--.*?-->', '', reset).strip()
    controls.append(
        f'<div class="ed-example-search"><input type="search" data-{kind}-search '
        f'aria-label="{label}" placeholder="{placeholder}">'
        f'<button type="button" data-{kind}-reset title="Clear all filters" '
        f'aria-label="Clear all filters">{reset}</button></div>'
    )
    return controls


def _catalogue_controls(registry: dict, metadata: dict) -> list[str]:
    # Five selectors, then the search field and a square reset; rows stay readable without JS.
    selects = []
    for family, title in [
        ('purpose', 'Purpose'),
        ('fittingMode', 'Fitting mode'),
        ('sampleForm', 'Sample form'),
        ('probe', 'Probe'),
        ('beamMode', 'Beam mode'),
    ]:
        values = sorted({
            v for entry in metadata.values() for v in entry['values'].get(family, [])
        })
        labels = [
            (token, registry['tags'].get(family, {}).get(token, {}).get('meaning', token))
            for token in values
        ]
        selects.append((family, title, labels))
    controls = _filter_bar(
        selects, 'example', 'Search tutorials', 'Search sample, instrument or label'
    )
    controls.extend(('</div><p data-example-count aria-live="polite"></p>',))
    return controls


# The interfaces' link columns (the owner, 2026-11-08): each header an icon and the full name,
# each cell an icon-only link named for its tutorial.
INTERFACES = {
    'application': ('Application', 'fa5/desktop'),
    'python': ('Python', 'simple/python'),
    'cli': ('Command line', 'fa5/terminal'),
}


def _icon(name: str) -> str:
    """An icon as inline SVG: the site's own set, else Zensical's."""
    import zensical  # noqa: PLC0415 - only the site build has it

    for folder in (
        ROOT / 'surfaces/overrides/.icons',
        Path(zensical.__file__).parent / 'templates/.icons',
    ):
        path = folder / f'{name}.svg'
        if path.is_file():
            svg = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8')).strip()
            return f'<span class="twemoji">{svg}</span>'
    raise SystemExit(f'render_experiments: no icon {name}')


# The record's names for the interfaces (projects.yml `interfaces:`), by this table's columns.
RECORD_INTERFACES = {'app': 'application', 'python': 'python', 'cli': 'cli'}

# Tutorials that are no project case, listed under Getting started after the cases. The built-in
# assistant is the app's alone; one's own assistant is driven from Python or the command line
# (owner record 2026-11-09).
ASSISTANT_ROWS = (
    {
        'id': 'assistant-built-in',
        'title': 'Built-in assistant: La₀.₅Ba₀.₅CoO₃ on HRPT',
        'pages': {'application': 'application/tutorials/assistant.md'},
    },
    {
        'id': 'assistant-own',
        'title': 'Your own assistant: La₀.₅Ba₀.₅CoO₃ on HRPT',
        'pages': {'python': 'python/tutorials/assistant.md', 'cli': 'cli/tutorials/assistant.md'},
    },
)


# The case both assistant tutorials fit: their tags and filter values are its own, plus the AI
# assistant tag (owner record 2026-11-09).
ASSISTANT_CASE = 'pd-neut-cwl_lbco-hrpt'
ASSISTANT_TAG = {'facet': 'interface', 'value': 'assistant', 'label': 'AI assistant'}


def _assistant_records(records: list[dict]) -> list[dict]:
    section = 'Getting started'
    case = next(record for record in records if record['id'] == ASSISTANT_CASE)
    return [
        {
            **row,
            'case': ASSISTANT_CASE,
            'tags': [*case['tags'], ASSISTANT_TAG],
            'section': section,
            'section_icon': SECTIONS[section],
        }
        for row in ASSISTANT_ROWS
        if all((DOCS / page).is_file() for page in row['pages'].values())
    ]


def _tutorial_links(record: dict, python_pages: set[str]) -> dict[str, str | None]:
    """Each interface's tutorial of a case, as a link from a Tutorials page, or None.

    An interface the case record does not declare has none, by design (owner record 2026-11-09).
    """
    if 'pages' in record:
        return {
            key: f'../../{record["pages"][key]}' if key in record['pages'] else None
            for key in INTERFACES
        }
    declared = {RECORD_INTERFACES[name] for name in record.get('interfaces', RECORD_INTERFACES)}
    links = _case_links(record, python_pages)
    return {key: link if key in declared else None for key, link in links.items()}


def _case_links(record: dict, python_pages: set[str]) -> dict[str, str | None]:
    case = record['id']
    page = f'python/tutorials/cases/{case}.md'
    # The case's own Application tutorial (render_app_tutorials.py); a dash until it has one.
    application = f'application/tutorials/cases/{case}.md'
    if not (DOCS / application).is_file():
        application = None
    cli = f'cli/tutorials/cases/{case}.md'
    return {
        'application': f'../../{application}' if application else None,
        'python': f'../../{page}' if page in python_pages else None,
        # The command line's own tutorial pages (render_cli_tutorials.py), never the developer
        # docs (the owner, 2026-11-09); a dash until a case has one.
        'cli': f'../../{cli}' if (DOCS / cli).is_file() else None,
    }


def _tutorial_rows(
    metadata: dict,
    records: list[dict],
    columns: list[str],
    python_pages: set[str],
    own_interface: str | None = None,
) -> list[str]:
    """The table's rows, with a link column for each of ``columns``.

    On an interface's own page (``own_interface``) there is no link column; each title links to
    that interface's tutorial.
    """
    # Every page starts at its first section heading, with no header row (the owner, 2026-11-09);
    # an interface column is its linked icon alone, named by its tooltip.
    rows = ['<table><tbody>']
    # The sections in the navigation's order (case_records.SECTIONS), each with its cases.
    sections: dict[str, list[dict]] = {name: [] for name in SECTIONS}
    for record in records:
        sections.setdefault(record['section'], []).append(record)
    for section, members in sections.items():
        if not members:
            continue
        icon = members[0]['section_icon']
        rows.append(
            f'<tr class="ed-tutorial-section" data-tutorial-section="{html.escape(section)}">'
            f'<th colspan="{1 + len(columns)}">{_icon("fa5/" + icon)} '
            f'{html.escape(section)}</th></tr>'
        )
        for record in members:
            entry = metadata.get(
                record.get('case', record['id']),
                {'samples': [record['id']], 'origin': '', 'detail': '', 'values': {}},
            )
            values = entry['values']
            attrs = ' '.join(
                f'data-{key.lower()}="{html.escape(json.dumps(tokens), quote=True)}"'
                for key, tokens in values.items()
            )
            # The case record's title, as the tutorials and the navigation name the case.
            title = record['title'] or ' / '.join(entry['samples'])
            labels = ' '.join(
                badge(tag['facet'], tag['value'], prefix='../../') for tag in record['tags'] or []
            )
            links = _tutorial_links(record, python_pages)
            own = links.get(own_interface) if own_interface else None
            if own_interface and not own:
                continue  # an interface's own page lists only its tutorials
            name = f'<a href="{own}">{html.escape(title)}</a>' if own else html.escape(title)
            search = html.escape(
                (
                    record['id'] + ' ' + title + ' ' + entry['detail'] + ' ' + json.dumps(values)
                ).lower(),
                quote=True,
            )
            cells = ''.join(
                '<td class="ed-tutorial-link">'
                + (
                    f'<a href="{links[key]}" title="{INTERFACES[key][0]}" '
                    f'aria-label="{INTERFACES[key][0]}">'
                    f'{_icon(INTERFACES[key][1])}</a>'
                    if links[key]
                    else '—'
                )
                + '</td>'
                for key in INTERFACES
                if key in columns
            )
            rows.append(
                f'<tr data-example-row data-search="{search}" {attrs}>'
                f'<td><span class="ed-example-name">{name}</span>'
                f'{html.escape(entry["detail"])}<span class="ed-example-tags">{labels}</span></td>'
                f'{cells}</tr>'
            )
    rows.append('</tbody></table>')
    return rows


def write_tutorial_tables(records: list[dict], python_pages: set[str]) -> list[Path]:
    """Write the one tutorial table into the Tutorials pages, and return those pages.

    The user guide's page has every interface's link column; each interface's overview has none,
    its titles linking to its own tutorials (the owner, 2026-11-08 and 2026-11-09).
    """
    registry = json.loads((ASSETS / 'experiment-tags.json').read_text())
    metadata = json.loads((ASSETS / 'examples.json').read_text())['examples']
    controls = _catalogue_controls(registry, metadata)
    written = []
    for page, interface in (
        ('user-guide/tutorials/index.md', None),
        ('application/tutorials/index.md', 'application'),
        ('python/tutorials/index.md', 'python'),
        ('cli/tutorials/index.md', 'cli'),
    ):
        # The all-tutorials page has a link column per interface; an interface's own page none.
        columns = [] if interface else list(INTERFACES)
        rows = _tutorial_rows(
            metadata, [*records, *_assistant_records(records)], columns, python_pages, interface
        )
        content = '<div data-example-catalogue>\n' + '\n'.join(controls + rows) + '\n</div>'
        replace(DOCS / page, 'tutorial-table', content)
        written.append(DOCS / page)
    return written


def render() -> None:
    if not (ASSETS / 'experiment-tags.json').exists():
        return
    registry = json.loads((ASSETS / 'experiment-tags.json').read_text())
    _write_tag_css(registry)
    _write_experiment_types(registry)
    _write_page_labels(registry)
    replace(
        DOCS / 'user-guide/features.md', 'features-filter', '\n'.join(_features_filter(registry))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-native', type=Path)
    args = parser.parse_args()
    if args.import_native:
        ASSETS.mkdir(parents=True, exist_ok=True)
        source = args.import_native.resolve()
        provenance = {
            'edi_commit': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=source, text=True
            ).strip(),
            'files': {},
        }
        for name, filename in [('tags', 'tags.json'), ('examples', 'metadata.json')]:
            path = source / 'app/examples' / filename
            data = path.read_bytes()
            provenance['files'][filename] = hashlib.sha256(data).hexdigest()
            shutil.copyfile(
                path, ASSETS / ('experiment-tags.json' if name == 'tags' else 'examples.json')
            )
        (ASSETS / 'experiment-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    render()


if __name__ == '__main__':
    main()
