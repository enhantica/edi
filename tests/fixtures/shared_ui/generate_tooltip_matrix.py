"""Emit input cases from ADR-0076 point 6; expected outcomes stay in the hidden gates."""

import argparse
import hashlib
import json
import re
from pathlib import Path

LEVELS = ['Off', 'Important', 'All']
BOOLS = [False, True]


def tag(*parts):
    return '-'.join(str(part).lower() if isinstance(part, bool) else str(part) for part in parts)


def cases():
    groups = {}
    groups['composition'] = [
        {'tag': tag(spec, level, enabled), 'spec': spec, 'level': level, 'enabled': enabled}
        for spec in [
            'button',
            'group-button',
            'fitting-label-help',
            'fitting-label-no-help',
            'elided-label-help',
            'elided-label-deduplicated',
            'elided-label-no-help',
            'fitting-table-help',
            'overflow-table-help',
            'overflow-table-no-help',
            'fitting-table-no-help',
            'field-help',
            'field-no-help',
            'combo-help',
            'combo-no-help',
        ]
        for level in LEVELS
        for enabled in BOOLS
    ]
    groups['explicit_full_text'] = [
        {
            'tag': tag(kind, shortened, with_help, full_case),
            'kind': kind,
            'shortened': shortened,
            'withHelp': with_help,
            'fullText': full_text,
        }
        for kind in ['C.ListViewLabel', 'C.ListViewTextInput', 'E.TextField']
        for shortened in BOOLS
        for with_help in BOOLS
        for full_case, full_text in [('empty', ''), ('precise', '1.234567890123')]
    ]
    groups['number_label'] = [
        {'tag': tag(width, level, enabled), 'width': width, 'level': level, 'enabled': enabled}
        for width in [18, 80, 600]
        for level in LEVELS
        for enabled in BOOLS
    ]
    groups['classification'] = [
        {
            'tag': tag(kind, self_explanatory, enabled, level),
            'kind': kind,
            'self': self_explanatory,
            'enabled': enabled,
            'level': level,
        }
        for kind in [
            'E.Button',
            'E.GroupButton',
            'C.ListViewLabel',
            'C.ListViewTextInput',
            'E.TextField',
            'E.ComboBox',
            'E.Slider',
        ]
        for self_explanatory in BOOLS
        for enabled in BOOLS
        for level in LEVELS
    ]
    groups['fixed_and_standalone'] = [
        {'tag': tag(kind, enabled, level), 'kind': kind, 'enabled': enabled, 'level': level}
        for kind in ['E.TabButton', 'ChartToolButton', 'StatusBarItem']
        for enabled in BOOLS
        for level in LEVELS
    ]
    groups['focus_and_warning_input'] = [
        {
            'tag': tag(kind, focus, hovering, warned),
            'kind': kind,
            'focus': focus,
            'hovering': hovering,
            'warned': warned,
        }
        for kind in ['C.ListViewTextInput', 'E.TextField']
        for focus in BOOLS
        for hovering in BOOLS
        for warned in BOOLS
    ]
    groups['base_warning_clearance'] = [
        {'tag': tag(kind, focus, hovering), 'kind': kind, 'focus': focus, 'hovering': hovering}
        for kind in ['C.ListViewTextInput', 'E.TextField', 'E.ComboBox']
        for focus in BOOLS
        for hovering in BOOLS
    ]
    groups['combo_open'] = [{'tag': tag(warned), 'warned': warned} for warned in BOOLS]
    groups['slider_value'] = [
        {'tag': tag(alias, enabled, level), 'alias': alias, 'enabled': enabled, 'level': level}
        for alias in ['untouched', 'empty', 'caller']
        for enabled in BOOLS
        for level in LEVELS
    ]
    groups['value_field'] = [
        {'tag': tag(state, level), 'state': state, 'level': level}
        for state in [
            'refusal',
            'typed-rule',
            'refusal-and-rule',
            'disabled',
            'disabled-refusal',
            'clean-focused',
            'focus-only',
        ]
        for level in LEVELS
    ]
    groups['value_field_clearance'] = [
        {'tag': tag(state, mode, level), 'state': state, 'mode': mode, 'level': level}
        for state, modes in [
            ('refusal', ['hover', 'focus-only', 'focus-and-hover', 'disabled-hover']),
            ('typed-rule', ['focus-only', 'focus-and-hover']),
        ]
        for mode in modes
        for level in LEVELS
    ]
    groups['selector_warning'] = [
        {'tag': tag(state, level), 'state': state, 'level': level}
        for state in [
            'caller-help',
            'option-help',
            'disabled',
            'refusal',
            'open-refusal',
            'clear-token',
            'clear-token-caller',
            'disabled-clear-token',
        ]
        for level in LEVELS
    ]
    groups['project_name'] = [
        {'tag': tag(mode, level), 'mode': mode, 'level': level}
        for mode in ['hover', 'focus-only', 'focus-and-hover']
        for level in LEVELS
    ]
    groups['standard_footer_icons'] = [{'tag': 'all-standard-roles'}]
    return groups


def render():
    return '.pragma library\nvar cases = ' + json.dumps(cases(), indent=2) + ';\n'


def qt_control_reference(qml_root):
    files = []
    modules = {}
    for suffix in ['', '/Basic', '/Material', '/impl', '/Material/impl']:
        folder = 'QtQuick/Controls' + suffix
        uri = folder.replace('/', '.')
        names = set()
        for basename in ['qmldir', 'plugins.qmltypes']:
            relative = folder + '/' + basename
            path = qml_root / relative
            if not path.is_file():
                continue
            data = path.read_bytes()
            source = data.decode()
            files.append({'name': relative, 'sha256': hashlib.sha256(data).hexdigest()})
            if basename == 'qmldir':
                names.update(
                    re.findall(r'^(?:singleton )?([A-Z]\w*) [0-9]+\.[0-9]+ ', source, re.MULTILINE)
                )
            names.update(re.findall(r'"' + re.escape(uri) + r'/([^/" ]+) [^"\n]+"', source))
        modules[uri] = sorted(names)
    modules['QtQuick.Controls'] = sorted(
        set(modules['QtQuick.Controls']) | set(modules['QtQuick.Controls.Basic'])
    )
    if not {'Button', 'ToolTip', 'Slider', 'TextField'} <= set(modules['QtQuick.Controls']):
        raise ValueError('Qt Controls metadata must enumerate its standard exported controls')
    return {
        'source': 'pinned Qt 6.11.2 module metadata',
        'files': files,
        'types': modules['QtQuick.Controls'],
        'modules': modules,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qt-qml', type=Path)
    args = parser.parse_args()
    Path(__file__).with_name('TooltipContractCases.js').write_text(render())
    if args.qt_qml:
        Path(__file__).with_name('qt_controls.json').write_text(
            json.dumps(qt_control_reference(args.qt_qml), indent=2) + '\n'
        )
