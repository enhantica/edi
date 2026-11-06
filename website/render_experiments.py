#!/usr/bin/env python3
"""Render experiment tags and a searchable catalogue from native app metadata."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from itertools import starmap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'
ASSETS = DOCS / 'assets/reference'


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
        '.ed-example-filters {display:flex;flex-wrap:wrap;gap:.5rem;margin-block:.7rem}',
        (
            '.ed-example-filters input,.ed-example-filters select '
            '{font:inherit;max-width:100%;padding:.4em .6em;border:1px solid '
            'var(--md-default-fg-color--lightest);border-radius:5px;'
            'background:var(--md-default-bg-color);color:var(--md-default-fg-color)}'
        ),
        '.ed-example-name {display:block}',
        '.ed-example-tags {display:block;margin-top:.25em}',
        '[data-example-row][hidden] {display:none}',
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
    }
    meanings = {
        'fitting': (
            'Compare a calculated model with measured intensities and refine its parameters.'
        ),
        'simulation': 'Calculate the pattern from the current model without measured intensities.',
        'bragg-diffraction': 'Model the crystalline contribution from lattice reflections.',
        'single-fit': 'Refine one experiment.',
        'joint-fit': 'Refine several experiments together with shared model quantities.',
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
        'time-of-flight': (
            'Neutron wavelengths are separated by arrival time. Calibration relates flight '
            'time to diffraction geometry.'
        ),
    }
    intro = (
        'An experiment combines one label from each family below. For example, the first '
        'refinement is '
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


def _write_glossary_labels() -> None:
    glossary = DOCS / 'user-guide/glossary.md'
    text = glossary.read_text()
    for phrase, family, token in [
        ('**Powder diffraction**', 'sampleForm', 'powder'),
        ('**Single-crystal diffraction**', 'sampleForm', 'single crystal'),
        ('**Constant wavelength (CWL)**', 'beamMode', 'constant wavelength'),
        ('**Time of flight (TOF)**', 'beamMode', 'time-of-flight'),
    ]:
        marker = '<!-- glossary-label:' + token.replace(' ', '-') + ' -->'
        text = re.sub(' ?' + re.escape(marker) + r'.*?<!-- /glossary-label -->', '', text)
        text = text.replace(
            phrase, phrase + ' ' + marker + badge(family, token) + '<!-- /glossary-label -->', 1
        )
    text = re.sub(
        r'\nFor linked definitions of .*?see \[Experiment types and '
        r'labels\]\(experiment-types.md\)\.\n?',
        '\n',
        text,
    )
    glossary.write_text(text.rstrip() + '\n')


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


def _badge_features(source: str, relative: str) -> str:
    """Add measurement labels to scoped feature links."""

    def feature_scope(match, relative=relative):
        title, scope, url = match[1], match[2], match[3]
        values = []
        combined = title + ' ' + scope
        if 'powder' in combined.lower():
            values.append(('sampleForm', 'powder'))
        if 'single crystal' in combined.lower():
            values.append(('sampleForm', 'single crystal'))
        if 'neutron' in title.lower():
            values.append(('probe', 'neutron'))
        if 'x-ray' in title.lower():
            values.append(('probe', 'xray'))
        if 'CW' in scope or 'constant wavelength' in scope:
            values.append(('beamMode', 'constant wavelength'))
        if 'TOF' in scope or 'time of flight' in scope:
            values.append(('beamMode', 'time-of-flight'))
        if not values:
            return match[0]
        if 'ABSCOR1' in scope:
            title += ' (ABSCOR1)'
        return (
            '['
            + title
            + ']('
            + url
            + ') '
            + ' '.join(badge(family, token, prefix=relative) for family, token in values)
        )

    return re.sub(
        r'\[([^]\n]+?) · ((?:CW|TOF|constant wavelength|time of '
        r'flight)[^]\n]*)\]\(([^)]+)\)',
        feature_scope,
        source,
    )


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
            source = _badge_features(source, relative)
        blocks = re.split(r'(^```[^\n]*\n.*?^```[^\n]*$)', source, flags=re.MULTILINE | re.DOTALL)
        for index in range(0, len(blocks), 2):
            for label, (family, token) in tokens.items():
                blocks[index] = blocks[index].replace(
                    '`' + label + '`', badge(family, token, prefix=relative)
                )
        path.write_text(''.join(blocks))


def _catalogue_controls(registry: dict, metadata: dict) -> list[str]:
    # One compact, progressively disclosed catalogue; all entries remain readable without JS.
    controls = [
        (
            '<div class="ed-example-filters"><input type="search" data-example-search '
            'aria-label="Search examples" placeholder="Search sample, instrument or label">'
        )
    ]
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
        if len(values) < 2:
            continue
        options = ['<option value="">All ' + title.lower() + 's</option>']
        for token in values:
            label = registry['tags'].get(family, {}).get(token, {}).get('meaning', token)
            options.append(
                f'<option value="{html.escape(token, quote=True)}">{html.escape(label)}</option>'
            )
        controls.append(
            f'<select data-example-filter="{family}" aria-label="{title}">'
            + ''.join(options)
            + '</select>'
        )
    controls.append('</div><p data-example-count aria-live="polite"></p>')
    return controls


def _catalogue_rows(registry: dict, metadata: dict) -> list[str]:
    rows = [
        '<table><thead><tr><th>Example</th><th>Purpose and experiment</th></tr></thead><tbody>'
    ]
    for identity, entry in metadata.items():
        attrs = ' '.join(
            f'data-{key.lower()}="{html.escape(json.dumps(values), quote=True)}"'
            for key, values in entry['values'].items()
        )
        title = ' / '.join(entry['samples']) + ' · ' + entry['origin']
        labels = []
        for family, values in registry['tags'].items():
            labels.extend(
                badge(family, token)
                for token in entry['values'].get(family, [])
                if token in values
            )
        search = html.escape(
            (
                identity + ' ' + title + ' ' + entry['detail'] + ' ' + json.dumps(entry['values'])
            ).lower(),
            quote=True,
        )
        rows.append(
            (
                f'<tr data-example-row data-search="{search}" {attrs}><td><a '
                'class="ed-example-name" '
                f'href="https://github.com/enhantica/edi/tree/ai-assistant-on-dev/docs/user/cli/{identity}">{html.escape(title)}</a>{html.escape(entry["detail"])}</td><td>'
            )
            + ' '.join(labels)
            + '</td></tr>'
        )
    rows.append('</tbody></table>')
    return rows


def _write_example_catalogue(registry: dict, metadata: dict) -> None:
    controls = _catalogue_controls(registry, metadata)
    rows = _catalogue_rows(registry, metadata)
    content = (
        (
            '<details><summary>Find more examples by measurement type</summary>\n<div '
            'data-example-catalogue>\n'
        )
        + '\n'.join(controls + rows)
        + '\n</div>\n</details>'
    )
    replace(DOCS / 'user-guide/examples.md', 'example-catalogue', content)


def render() -> None:
    if not (ASSETS / 'experiment-tags.json').exists():
        return
    registry = json.loads((ASSETS / 'experiment-tags.json').read_text())
    metadata = json.loads((ASSETS / 'examples.json').read_text())['examples']
    _write_tag_css(registry)
    _write_experiment_types(registry)
    _write_glossary_labels()
    _write_page_labels(registry)
    _write_example_catalogue(registry, metadata)


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
