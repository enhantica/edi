#!/usr/bin/env python3
"""Build linked GUI/Edi/Python/CIF tables from the native dictionary and verified bindings."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from operator import itemgetter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'
ASSETS = DOCS / 'assets/reference'
STRUCTURE = {
    'space_group',
    'cell',
    'atom_site',
    'atom_site_aniso',
    'scattering_length',
    'geom',
    'structure_view',
    'space_group_symop',
    'expanded_atom_site',
    'geom_bond',
    'atom_sites_cartn_transform',
}
EXPERIMENT = {
    'experiment_type',
    'scattering_source',
    'data_source',
    'data_range',
    'data',
    'instrument',
    'peak',
    'background',
    'background_estimate',
    'absorption',
    'extinction',
    'reflns',
    'linked_structure',
    'preferred_orientation',
    'excluded_region',
    'refln',
    'data_calc',
    'pd_calc',
    'pd_calc_overall',
}


# Category-specific guides use the native category symbol; broad workflow groups
# retain the existing Material workflow icons (ADR-0002).
CATEGORY_PAGES = {
    'application/symmetry.md': 'cell',
    'application/atoms.md': 'atom_site',
    'application/displacement.md': 'atom_site_aniso',
    'application/instrument.md': 'instrument',
    'application/peak-profiles.md': 'peak',
    'application/background.md': 'background',
    'application/linked-structures.md': 'linked_structure',
    'application/minimizer.md': 'minimizer',
    'application/fitting-modes.md': 'fitting_mode',
}


def anchor(uid: str) -> str:
    if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?', uid):
        raise ValueError('Invalid dictionary identity: ' + uid)
    return uid.replace('_', '-').replace('.', '-')


# The development task labels some dictionary descriptions end with.
TASK_LABEL = re.compile(r'[;,]?\s*\b[A-Z]\d{2}-[T]\d+\b')


def without_task_labels(value: object) -> object:
    """The dictionary export with development task labels left out of its text."""
    if isinstance(value, str):
        return TASK_LABEL.sub('', value)
    if isinstance(value, list):
        return [without_task_labels(item) for item in value]
    if isinstance(value, dict):
        return {key: without_task_labels(item) for key, item in value.items()}
    return value


def plain(text: str) -> str:
    # Dictionary provenance belongs in the retained metadata, rather than user descriptions.
    text = re.sub(r'\s*\(ADR-\d+[^)]*\)', '', text)
    text = TASK_LABEL.sub('', text)
    return html.escape(text).replace('|', '&#124;').replace('\n', ' ')


def code(value: str) -> str:
    return '<code>' + html.escape(value).replace('|', '&#124;') + '</code>'


def icon(name: str, glyphs: dict, *, category: str = '') -> str:
    if not name:
        return ''
    value = glyphs.get(name)
    if value is None:
        raise ValueError('Native icon has no exported Font Awesome glyph: ' + name)
    marker = f' data-reference-category="{anchor(category)}"' if category else ''
    return f'<span class="ed-reference-icon"{marker} aria-hidden="true">&#{value};</span> '


def parameter_icon(name: str, rules: list) -> str:
    return next((value for prefix, value in rules if name.startswith(prefix)), '')


def _special_name(item: dict) -> str | None:
    name = item['name']
    if item['category'] == 'cell':
        if name.startswith('length_'):
            return 'Cell length ' + name.removeprefix('length_')
        if name.startswith('angle_'):
            return 'Cell angle ' + item['label']
    names = {
        'name_h_m': 'Hermann-Mauguin symbol',
        'coord_system_code': 'Space-group setting',
        'it_number': 'Space-group number',
        'intensity_meas': 'Measured intensity',
        'intensity_meas_su': 'Measured intensity uncertainty',
        'intensity_calc': 'Calculated intensity',
        'intensity_bkg': 'Background intensity',
        'adp_iso': 'Isotropic or equivalent displacement',
    }
    if name in names:
        return names[name]
    coordinate = re.fullmatch(r'(fract|cartn)_([xyz])', name)
    if coordinate:
        return (
            ('Fractional ' if coordinate[1] == 'fract' else 'Cartesian ')
            + coordinate[2]
            + '-coordinate'
        )
    return None


def _category_name(item: dict) -> str | None:
    name = item['name']
    # A lookup label names the quantity. Descriptions, equations and cross-program
    # conventions belong in the linked explanation, never in this column or heading.
    labels = {
        'atom_site.id': 'Atom-site identifier',
        'atom_site.type_symbol': 'Chemical element',
        'atom_site.wyckoff_letter': 'Wyckoff position',
        'atom_site.adp_type': 'Displacement parameter type',
        'atom_site_aniso.id': 'Anisotropic atom-site identifier',
        'scattering_length.length_fm': 'Neutron scattering length',
        'geom.min_bond_distance_cutoff': 'Minimum bond distance',
        'geom.bond_distance_inc': 'Bond-distance tolerance',
        'structure_view.atom_view': 'Atom radius model',
        'structure_view.adp_probability': 'Ellipsoid probability',
        'space_group_symop.operation_xyz': 'Symmetry operation',
        'expanded_atom_site.atom_site_id': 'Source atom site',
        'expanded_atom_site.site_symmetry': 'Generating symmetry operation',
        'expanded_atom_site.cluster_id': 'Coincident-atom cluster',
        'background.intensity': 'Background anchor intensity',
        'background.position': 'Background anchor position',
        'background.coef': 'Background coefficient',
        'background.order': 'Background term order',
        'background.origin': 'Polynomial background origin',
        'background.x_min': 'Chebyshev domain minimum',
        'background.x_max': 'Chebyshev domain maximum',
        'background.type': 'Background model',
        'background.id': 'Background row identifier',
        'background_estimate.n_points': 'Number of background anchors',
        'background_estimate.tolerance': 'Background thinning tolerance',
        'background_estimate.in_peaks': 'Anchors within peaks',
        'background_estimate.use_model': 'Calculated-peak treatment',
        'su_format.rule': 'Uncertainty rounding rule',
        'data_source.file_name': 'Measured-data filename',
        'data.calc_status': 'Calculation status',
        'instrument.calib_twotheta_offset': 'Zero-point angular offset',
        'instrument.setup_wavelength_2': 'Secondary wavelength',
        'instrument.setup_wavelength_2_to_1_ratio': 'Secondary-to-primary intensity ratio',
        'peak.mixing_eta_0': 'Pseudo-Voigt mixing intercept',
        'peak.mixing_eta_1': 'Pseudo-Voigt mixing slope',
        'peak.cutoff_fwhm': 'Peak calculation cutoff',
        'linked_structure.weight_fraction': 'Phase mass fraction',
        'preferred_orientation.march_r': 'March-Dollase coefficient',
        'preferred_orientation.march_random_fract': 'Randomly oriented fraction',
        'reflns.threshold_sigma': 'Observed-reflection threshold',
        'refine_ls.threshold_sigma': 'Fitted-reflection threshold',
        'fitting_mode.type': 'Fitting mode',
        'fit_result.n_data_points': 'Number of fitted observations',
        'fit_result_bank.n_data_points': 'Number of fitted observations',
        'sequential_fit_extract.target': 'Extracted value name',
    }
    if item['uid'] in labels:
        return labels[item['uid']]
    if item['category'] == 'atom_sites_cartn_transform' and name.startswith('mat_'):
        return 'Coordinate-transform element ' + name.removeprefix('mat_')
    if item['category'] == 'atom_site_aniso' and name.startswith('adp_'):
        return 'Displacement tensor component ' + name.removeprefix('adp_')
    if item['category'] == 'peak':
        for prefix, title in {
            'rise_alpha_': 'Exponential rise coefficient',
            'decay_beta_': 'Exponential decay coefficient',
            'broad_gauss_': 'Gaussian broadening',
            'broad_lorentz_': 'Lorentzian broadening',
            'asym_fcj_': 'FCJ asymmetry',
            'asym_beba_': 'Bérar-Baldinozzi asymmetry',
        }.items():
            if name.startswith(prefix):
                return title + ' ' + item['label']
    return None


def readable_name(item: dict) -> str:
    name = item['name']
    special = _special_name(item)
    if special is not None:
        return special
    category = _category_name(item)
    if category is not None:
        return category
    common = {
        'occupancy': 'Occupancy',
        'u_iso': 'Isotropic displacement U',
        'd_spacing': 'Interplanar spacing',
        'two_theta': 'Scattering angle',
        'time_of_flight': 'Time of flight',
        'index_h': 'Miller index h',
        'index_k': 'Miller index k',
        'index_l': 'Miller index l',
    }
    if name in common:
        return common[name]
    label = item['label'].strip() or name.replace('_', ' ')
    return label[:1].upper() + label[1:]


def explanation(item: dict) -> str:
    if item['category'] == 'cell' and item['name'].startswith('length_'):
        axis = item['name'].removeprefix('length_')
        return (
            f'Length of the unit-cell edge along the {axis} axis. Cell geometry determines '
            'calculated reflection positions; check the space-group symmetry before freeing '
            'cell dimensions.'
        )
    coordinate = re.fullmatch(r'fract_([xyz])', item['name'])
    if coordinate and item['category'] in {'atom_site', 'expanded_atom_site'}:
        axis = {'x': 'a', 'y': 'b', 'z': 'c'}[coordinate[1]]
        subject = (
            'representative atom site'
            if item['category'] == 'atom_site'
            else 'symmetry-generated atom'
        )
        return (
            f'Position of the {subject} along the {axis} lattice vector, expressed as a '
            'fraction of the unit cell rather than a Cartesian distance.'
        )
    return plain(item['description'])


def _gui_name(item: dict, lookup: dict, glyphs: dict, rules: list) -> str:
    category = item['category']
    label = plain(item['label'])
    if not item['parameter']:
        return label
    block_icon = (
        'layer-group' if category in STRUCTURE else 'microscope' if category in EXPERIMENT else ''
    )
    return (
        '<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">'
        + icon(block_icon, glyphs)
        + icon(lookup[category]['icon'], glyphs)
        + icon(parameter_icon(item['name'], rules), glyphs)
        + '</span><span class="ed-icon-text">'
        + label
        + '</span></span>'
    )


def _cif_names(item: dict) -> str:
    variants = [v for v in item['variants'] if v['cif_names']]
    shown = [v['cif_names'][0] for v in variants] if variants else item['cif_names'][:1]
    value = (
        '<br>'.join(code(v['token']) + ': ' + code(v['cif_names'][0]) for v in variants)
        if variants
        else (code(shown[0]) if shown else '—')
    )
    aliases = list(
        dict.fromkeys(
            name
            for name in item['cif_names'] + [name for v in variants for name in v['cif_names']]
            if name not in shown
        )
    )
    if aliases:
        value += (
            '<details><summary>Accepted aliases</summary>'
            + '<br>'.join(code(name) for name in aliases)
            + '</details>'
        )
    return value


def _table_caption(category: dict, projection: str, glyphs: dict) -> str:
    url = '../physics/parameters.md#' + anchor(category['id'])
    caption = (
        '**['
        + icon(category['icon'], glyphs, category=category['id'])
        + category['title']
        + ']('
        + url
        + ')**'
    )
    if projection == 'GUI':
        caption = (
            '<span class="ed-reference-anchor" id="names-'
            + anchor(category['id'])
            + '">'
            + caption
            + '</span>'
        )
    return caption


def _table_rows(
    projection: str, entries: list, lookup: dict, glyphs: dict, rules: list, paths: dict
) -> list[str]:
    rows = []
    for item in entries:
        url = '../physics/parameters.md#' + anchor(item['uid'])
        name = '[' + plain(readable_name(item)) + '](' + url + ')'
        value = (
            _gui_name(item, lookup, glyphs, rules)
            if projection == 'GUI'
            else code(item['edi_tag'])
            + (
                (
                    '<br><small>Also accepted: '
                    + ', '.join(code(v) for v in item['edi_aliases'])
                    + '</small>'
                )
                if item['edi_aliases']
                else ''
            )
            if projection == 'Edi'
            else '<br>'.join(code(p) for p in paths.get(item['uid'], [])) or '—'
            if projection == 'Python'
            else _cif_names(item)
        )
        rows.append('    | ' + name + ' | ' + value + ' |')
    return rows


def _name_tables(
    categories: list, items: list, lookup: dict, glyphs: dict, rules: list, paths: dict
) -> list[str]:
    tables = [
        '# Parameter names across interfaces',
        '',
        (
            'Compare names used in the app, saved Edi projects, Python and CIF. Select a '
            'parameter to read its meaning, units and model restrictions.'
        ),
        '',
        '??? note "About these names"',
        '',
        (
            '    GUI names use the application icon patterns. Python paths are checked '
            'against the supplied examples; use `.value` or `.free` on a parameter. CIF '
            'mappings can include EasyDiffraction extensions. A dash means no declared '
            'mapping was found; a listed field is not necessarily editable or independently '
            'refinable in every model.'
        ),
        '',
    ]
    for heading, group in [
        ('Structure parameters', STRUCTURE),
        ('Experiment parameters', EXPERIMENT),
        ('Project and analysis settings', set(lookup) - STRUCTURE - EXPERIMENT),
    ]:
        tables += ['## ' + heading, '']
        selected = [c for c in categories if c['id'] in group]
        for projection in ['GUI', 'Edi', 'Python', 'CIF']:
            tables += ['=== "' + projection + '"', '']
            for category in selected:
                entries = [item for item in items if item['category'] == category['id']]
                if not entries:
                    continue
                tables += [
                    '    ' + _table_caption(category, projection, glyphs),
                    '',
                    '    | Parameter or field | ' + projection + ' name |',
                    '    | --- | --- |',
                ]
                tables += _table_rows(projection, entries, lookup, glyphs, rules, paths)
                tables.append('')
    return tables


def _explanation_entry(item: dict, category: dict, scientific: dict) -> list[str]:
    identity = anchor(item['uid'])
    details = [
        '<section class="ed-parameter-entry" markdown="1" aria-labelledby="' + identity + '">',
        '',
        '### ' + plain(readable_name(item)) + ' {#' + identity + '}',
        '',
        explanation(item),
        '',
    ]
    links = []
    units = item['units'] or scientific.get(item['uid'], {}).get('units', '')
    if category['id'] == 'atom_site_aniso' and item['variants']:
        units = 'Å² for B/U; dimensionless for β'
    if units and item['dtype'] in {'float', 'int'}:
        details += ['**Units:** ' + plain(units) + '.', '']
    if item['uid'] in scientific:
        entry = scientific[item['uid']]
        if entry['role'] == 'stored-only':
            details += [
                (
                    '**Stored only.** Retained in project input but not applied in '
                    'this calculation.'
                ),
                '',
            ]
        links.append(
            '[Equation and conventions](' + entry['explanation_url'].replace('/#', '.md#') + ')'
        )
    if item['options']:
        details += ['| Option | Meaning |', '| --- | --- |']
        for option in item['options']:
            details += [
                '| '
                + plain(option['label'] or option['token'])
                + ' | '
                + plain(option['description'])
                + ' |'
            ]
        details += ['']
    if item['variants']:
        details += ['| Form | Units |', '| --- | --- |']
        for variant in item['variants']:
            unit = variant['units'] or item['units']
            if category['id'] == 'atom_site_aniso' and variant['token'] == 'beta':  # noqa: S105 -- scientific CIF displacement type
                unit = 'dimensionless'
            details += ['| ' + code(variant['token']) + ' | ' + (plain(unit) or '—') + ' |']
        details += ['']
    links.append(
        '[Names across interfaces](../user-guide/parameter-reference.md#names-'
        + anchor(category['id'])
        + ')'
    )
    details += [' · '.join(links), '', '</section>', '']
    return details


def _explanations(categories: list, items: list, glyphs: dict, scientific: dict) -> list[str]:
    details = [
        '---',
        'template: physics.html',
        '---',
        '',
        '# Parameter explanations {#parameter-and-category-reference}',
        '',
        (
            'Read what each parameter describes, its units and the models that use it. '
            'Applicability depends on the experiment and selected model. [Compare names '
            'across interfaces](../user-guide/parameter-reference.md).'
        ),
        '',
    ]
    for category in sorted(
        categories,
        key=lambda c: (
            0 if c['id'] in STRUCTURE else 1 if c['id'] in EXPERIMENT else 2,
            c['order'],
        ),
    ):
        entries = [item for item in items if item['category'] == category['id']]
        if not entries:
            continue
        details += [
            '## '
            + icon(category['icon'], glyphs, category=category['id'])
            + category['title']
            + ' {#'
            + anchor(category['id'])
            + '}',
            '',
            plain(category['description']),
            '',
        ]
        for item in entries:
            details += _explanation_entry(item, category, scientific)
    return details


def _decorate_category_pages(lookup: dict, glyphs: dict) -> None:
    for filename, uid in CATEGORY_PAGES.items():
        category = lookup[uid]
        glyph = glyphs[category['icon']]
        path = DOCS / filename
        text = path.read_text()
        # This metadata is generated from the same exported dictionary as headings.
        text = re.sub(r'^category_glyph:.*\n', '', text, flags=re.MULTILINE)
        if not text.startswith('---\n'):
            raise ValueError('Category guide must retain its template front matter: ' + filename)
        text = text.replace('---\n', '---\ncategory_glyph: ' + json.dumps(chr(glyph)) + '\n', 1)
        text = re.sub(
            r'^(# )<span[^>]*data-reference-category="[^"\n]+"[^>]*>.*?</span>\s*',
            r'\1',
            text,
            count=1,
            flags=re.MULTILINE,
        )
        text = re.sub(r'^(# ):material-[a-z-]+:\s*', r'\1', text, count=1, flags=re.MULTILINE)
        text, count = re.subn(
            r'^# ',
            '# ' + icon(category['icon'], glyphs, category=uid),
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError('Category guide must have a title: ' + filename)
        path.write_text(text)


def _decorate_feature_headings(lookup: dict, glyphs: dict) -> None:
    heading_categories = {
        'Symmetry and cell': 'cell',
        'Atom sites': 'atom_site',
        'Linked structures': 'linked_structure',
        'Absorption': 'absorption',
        'Preferred orientation': 'preferred_orientation',
        'Background': 'background',
        'Background models': 'background',
        'Background estimation': 'background_estimate',
        'Observation exclusions': 'excluded_region',
        'Single-crystal extinction': 'extinction',
        'Extinction': 'extinction',
        'Atomic displacement': 'atom_site_aniso',
        'Fitting mode': 'fitting_mode',
        'Fitting modes': 'fitting_mode',
        'Calibration': 'instrument',
    }
    for filename in ['user-guide/features.md', 'physics/models.md']:
        path = DOCS / filename
        text = path.read_text()

        def decorate(match):
            level, title = match[1], match[2]
            title = re.sub(
                r'^<span[^>]*data-reference-category="[^"\n]+"[^>]*>.*?</span>\s*', '', title
            )
            title, marker = re.match(r'^(.*?)( \{#[^}]+\})?$', title).groups()
            uid = heading_categories.get(title)
            if not uid:
                return match[0]
            marker = marker or ' {#' + re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + '}'
            return level + ' ' + icon(lookup[uid]['icon'], glyphs, category=uid) + title + marker

        text = re.sub(r'^(#{2,3}) (.+)$', decorate, text, flags=re.MULTILINE)
        path.write_text(text)


def render() -> None:
    if not (ASSETS / 'dictionary.json').exists():
        return
    dictionary = json.loads((ASSETS / 'dictionary.json').read_text())
    paths = json.loads((ASSETS / 'python-paths.json').read_text())['paths']
    rules = json.loads((ASSETS / 'gui-parameter-icons.json').read_text())
    glyphs = json.loads((DOCS / 'assets/gui-icons/glyphs.json').read_text())
    catalogue = json.loads((DOCS / 'physics/catalogue.json').read_text())
    scientific = {entry['id']: entry for entry in catalogue['parameters']}
    categories = sorted(dictionary['categories'], key=itemgetter('order'))
    items = dictionary['items']
    uids = [item['uid'] for item in items]
    if len(set(uids)) != len(uids) or set(scientific) - set(uids):
        raise ValueError('Native dictionary must cover every existing scientific parameter')
    anchors = [anchor(uid) for uid in uids] + [anchor(c['id']) for c in categories]
    if len(set(anchors)) != len(anchors):
        raise ValueError('Reference anchor collision')
    lookup = {category['id']: category for category in categories}
    tables = _name_tables(categories, items, lookup, glyphs, rules, paths)
    details = _explanations(categories, items, glyphs, scientific)
    (DOCS / 'physics/parameters.md').write_text('\n'.join(details))
    (DOCS / 'user-guide/parameter-reference.md').write_text('\n'.join(tables))
    _decorate_category_pages(lookup, glyphs)
    _decorate_feature_headings(lookup, glyphs)
    # A portable exact lookup also consumed by native help verification and future integrations.
    (ASSETS / 'parameter-links.json').write_text(
        json.dumps(
            {uid: 'physics/parameters/#' + anchor(uid) for uid in [*lookup, *uids]}, indent=2
        )
        + '\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-native', type=Path)
    parser.add_argument('--dictionary', type=Path)
    parser.add_argument('--python-paths', type=Path)
    parser.add_argument('--sdk-library', type=Path)
    args = parser.parse_args()
    if args.import_native:
        if not args.dictionary or not args.python_paths or not args.sdk_library:
            parser.error('Import requires --dictionary, --python-paths and --sdk-library')
        source = args.import_native.resolve()
        ASSETS.mkdir(parents=True, exist_ok=True)
        dictionary = without_task_labels(json.loads(args.dictionary.read_text()))
        (ASSETS / 'dictionary.json').write_text(json.dumps(dictionary, indent=4) + '\n')
        shutil.copyfile(args.python_paths, ASSETS / 'python-paths.json')
        # Reuse the exact prefix rules of the native Analysis name renderer.
        qml = source / 'app/qml/Globals/ParameterNames.qml'
        rules = re.search(r'const icons = (\[.*?\]);', qml.read_text()).group(1)
        (ASSETS / 'gui-parameter-icons.json').write_text(
            json.dumps(json.loads(rules), indent=2) + '\n'
        )
        provenance = {
            'edi_commit': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=source, text=True
            ).strip(),
            'source_sha256': {
                str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in [
                    qml,
                    source / 'tools/docs/reference-metadata.cpp',
                    source / 'tools/docs/python-reference.py',
                    source / 'data/category-census.json',
                ]
            },
            'sdk_library_sha256': hashlib.sha256(args.sdk_library.read_bytes()).hexdigest(),
        }
        (ASSETS / 'parameter-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    render()


if __name__ == '__main__':
    main()
