# SPDX-License-Identifier: BSD-3-Clause
"""Author a tiny reference Features page and one-fault variants without reading the product."""

from html import escape

STATUSES = {
    'available': '#008000',
    'partial': '#0000ff',
    'planned': '#777777',
    'proposed': '#ff7700',
    'unavailable': '#ff0000',
}
INTERFACES = ('Application', 'Python library', 'Command Line')
WAYS = {
    'crystal': [
        'From a CIF file',
        'From COD',
        'From EasyDiffraction collection',
        'Created by hand',
        'From a saved project',
    ],
    'magnetic': ['From a file on disk', 'Created by hand', 'From a saved project'],
    'experiments': [
        'A full experiment from a file',
        'A full experiment from the web',
        'Measured data from a file',
        'Measured data from the web',
        'Several datasets',
        'Created by hand',
        'From a saved project',
    ],
}


def icon(status):
    return f'<svg viewBox="0 0 10 10"><path d="M0 0h10v10H0z" fill="{STATUSES[status]}"/></svg>'


def cell(status, label=None):
    label = escape(label or status.capitalize(), quote=True)
    return f'<td><span role="img" aria-label="{label}" title="{label}">{icon(status)}</span></td>'


def build(fault=None):
    legend = ''.join(f'<li>{icon(status)}{status.capitalize()}</li>' for status in STATUSES)
    if fault == 'legend-prepared':
        legend = legend.replace('Partial</li>', 'Partial, or runs from a prepared project</li>')
    content = [
        '<main><article><h1>Features</h1><h2>How to read this page</h2><ul>',
        legend,
        '</ul>',
        '<h2>Defining structures and experiments</h2>',
    ]
    for group, ways in WAYS.items():
        if fault == 'missing-' + group:
            continue
        title = {
            'crystal': 'Crystal structures',
            'magnetic': 'Magnetic structures',
            'experiments': 'Experiments',
        }[group]
        columns = list(INTERFACES)
        if fault == 'duplicate-interface' and group == 'crystal':
            columns[2] = columns[1]
        content.append(f'<h3>{title}</h3><table><tr><th>Way</th>')
        content.extend(f'<th>{column}</th>' for column in columns)
        content.append('</tr>')
        selected = list(ways)
        if fault in {'magnetic-cod', 'magnetic-cod-long'} and group == 'magnetic':
            selected.append(
                'From COD' if fault == 'magnetic-cod' else 'From the Crystallography Open Database'
            )
        for way in selected:
            content.append(f'<tr><td>{way}</td>')
            for index in range(len(columns)):
                manual = way == 'Created by hand' and group == 'magnetic'
                status = 'planned' if manual else 'available'
                if index == 2 and 'project' not in way:
                    status = 'planned' if manual else 'unavailable'
                if manual and fault == f'manual-{index}':
                    status = 'available'
                if (
                    fault == 'cli-file-available'
                    and group == 'crystal'
                    and index == 2
                    and 'CIF' in way
                ):
                    status = 'available'
                prefix = f'definition-partial-{index}-'
                if group == 'crystal' and 'CIF' in way and (fault or '').startswith(prefix):
                    explanation = fault.removeprefix(prefix)
                    label = {
                        'absent': 'Partial',
                        'generic': 'Partial: missing work',
                        'specific': 'Partial: missing magnetic moment import',
                        'specific-drops': 'Partial: file import drops magnetic moments',
                    }[explanation]
                    content.append(cell('partial', label))
                else:
                    content.append(cell(status))
            content.append('</tr>')
        content.append('</table>')
    labels = {
        'partial-no-reason': 'Partial',
        'partial-renamed-available': 'Available: run a prepared project',
        'partial-generic-reason': 'Partial: missing work',
    }
    label = labels.get(fault, 'Partial: missing background editing')
    content.extend([
        '<h2>Pattern capabilities</h2><table><tr><th>Feature</th><th>Python library</th></tr>',
        '<tr><td>Background editing</td>',
        cell('partial', label),
        '</tr></table></article></main>',
    ])
    return ''.join(content)
