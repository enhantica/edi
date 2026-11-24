"""Independent content expectations for the measured two-phase scan scenario."""

import re

from tests.fixtures.ui_responsiveness.tab_inventory import ROOT, source

MAIN = {
    'description': ('DescriptionTab', 'characters', 'model', 'project'),
    'report': ('ReportPreview', 'sections', 'model', 'project'),
    'structure': ('StructureView', 'atoms', 'model', 'structure'),
    'pattern': ('PatternChart', 'points', 'calculated', 'calculated'),
    'meascalc': ('MeasCalcChart', 'points', 'calculated', 'calculated'),
    'correlations': ('CorrelationChart', 'matrix-cells', 'fitted', 'fitted'),
    'stacked': ('ScanViewChart', 'datasets', 'model', 'scan'),
    'map': ('ScanViewChart', 'datasets', 'model', 'scan'),
    'evolution': ('EvolutionChart', 'points', 'fitted', 'scan-fitted'),
}
SIDEBAR = {
    'basic': 'basicItem',
    'extras': 'extrasItem',
    'text': 'textItem',
    'settings': 'settingsItem',
}


def content_expectations(inventory, root=ROOT):
    """Require populated prepared views, retaining declaration-defined empty areas."""
    result = {}
    for page, areas in inventory.items():
        result[page] = {'main': {}, 'sidebar': {}}
        for tab in areas['main']:
            if tab['key'] not in MAIN:
                raise ValueError('A new main tab needs an independent content expectation')
            kind, unit, stage, binding = MAIN[tab['key']]
            result[page]['main'][tab['key']] = {
                'kind': kind,
                'mode': 'data',
                'unit': unit,
                'stage': stage,
                'binding': binding,
            }
        if not areas['main'] and not areas['sidebar']:
            if page != 'home':
                raise ValueError('A new tabless page needs an independent content expectation')
            result[page]['page'] = {
                page: {
                    'kind': 'HomePage',
                    'mode': 'static',
                    'unit': 'items',
                    'stage': 'model',
                    'binding': 'project',
                }
            }
        paths = [
            p
            for p in (root / 'app/qml/Pages').glob('*/*.qml')
            if p.stem.removesuffix('Page').lower() == page
        ]
        if len(paths) != 1:
            raise ValueError('Content expectations require one unambiguous page declaration')
        text = source(paths[0])
        for tab in areas['sidebar']:
            if tab['key'] not in SIDEBAR:
                raise ValueError('A new sidebar tab needs an independent content expectation')
            prop = SIDEBAR[tab['key']]
            present = re.search(r'\b' + prop + r'\s*:', text)
            component = re.search(r'\b' + prop + r'\s*:\s*Component\s*\{', text)
            if present and not component:
                raise ValueError('A custom sidebar binding needs a content expectation adapter')
            if component:
                expectation = {
                    'kind': 'TextTab' if tab['key'] == 'text' else 'SideBarColumn',
                    'mode': 'data',
                    'unit': 'characters' if tab['key'] == 'text' else 'controls',
                    'stage': 'model',
                    'binding': 'block' if tab['key'] == 'text' else 'page',
                }
            else:
                expectation = {
                    'kind': 'TabNote',
                    'mode': 'empty',
                    'unit': 'items',
                    'stage': 'model',
                    'reason': 'no-groups',
                    'object': 'sideBar.note.invite',
                    'binding': 'page',
                }
            result[page]['sidebar'][tab['key']] = expectation
    return result


def required_content(target, state):
    """A page visit includes both shown areas; a tab visit includes its own area."""
    if target['area'] != 'page':
        return [(target['area'], target['key'])]
    result = [
        (area, state[field])
        for area, field in [('main', 'tab'), ('sidebar', 'sidebar_tab')]
        if state.get(field)
    ]
    return result or [('page', target['page'])]
