"""Shared control policy and popup icons, from the product's UI rules."""

import json
import re
from pathlib import Path

from tests.integration.py.test_table_and_about_contract import properties, qml_objects, tokens

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'app/qml'
DEFERRED = json.loads((ROOT / 'tests/fixtures/shared_ui/deferred.json').read_text())


def sources():
    result = {path.relative_to(ROOT).as_posix(): path.read_text() for path in QML.rglob('*.qml')}
    base = ROOT / 'build/app/qml/EasyApplication'
    assert base.is_dir(), (
        'The census requires the configured app and its selected pinned base QML modules'
    )
    result.update({
        'base/' + path.relative_to(base).as_posix(): path.read_text()
        for path in base.rglob('*.qml')
    })
    return result


def deferred(path):
    return path in DEFERRED['files']


def test_overlap_deferrals_are_explicit():
    assert DEFERRED['heads'].keys() == {'magnetic_structures', 'online_data'}, (
        'The census identifies both overlapping branches and the exact heads it measured'
    )
    assert len(DEFERRED['files']) == len(set(DEFERRED['files'])), (
        'Each file deferred to the final shared-control pass has one named entry'
    )
    for path in DEFERRED['files']:
        assert (ROOT / path).is_file(), (
            'A deferred census path must name an actual QML file: ' + path
        )


def binding(body, name):
    depth = 0
    for index, word in enumerate(body[:-1]):
        if depth == 0 and word == name and body[index + 1] == ':':
            result = []
            level = 0
            for offset in range(index + 2, len(body)):
                value = body[offset]
                if level == 0 and (
                    value in {'property', 'readonly', 'function', 'signal', ';'}
                    or (offset + 1 < len(body) and body[offset + 1] == ':')
                ):
                    break
                result.append(value)
                level += value in {'(', '[', '{'}
                level -= value in {')', ']', '}'}
            return result
        depth += word in {'(', '[', '{'}
        depth -= word in {')', ']', '}'}
    return []


def requires_decision(expression, decision):
    def unwrap(words):
        while words and words[0] == '(' and words[-1] == ')':
            depth = 0
            consumed = 0
            for word in words:
                consumed += 1
                depth += word == '('
                depth -= word == ')'
                if depth == 0:
                    break
            if consumed != len(words):
                break
            words = words[1:-1]
        return words

    expression = unwrap(expression)
    factors = []
    start = depth = 0
    for index, word in enumerate(expression):
        if depth == 0 and expression[index : index + 2] == ['|', '|']:
            return False
        if depth == 0 and expression[index : index + 2] == ['&', '&']:
            factors.append(expression[start:index])
            start = index + 2
        depth += word in {'(', '[', '{'}
        depth -= word in {')', ']', '}'}
    factors.append(expression[start:])
    for part in factors:
        factor = unwrap(part)
        if len(factor) < 3 or factor[:2] != [decision, '('] or factor[-1] != ')':
            continue
        depth = 0
        consumed = 1
        for word in factor[1:]:
            consumed += 1
            depth += word == '('
            depth -= word == ')'
            if depth == 0:
                break
        if consumed == len(factor):
            return True
    return False


def test_census_rejects_visibility_bypasses():
    assert requires_decision(tokens('hovered && Policy.allowed(control)'), 'Policy.allowed'), (
        'A genuine required level decision remains admissible'
    )
    for source in (
        'true || Policy.allowed(control)',
        'hovered || (Policy.allowed(control) && text)',
        'hovered && (true || Policy.allowed(control))',
        'hovered; onClicked: Policy.allowed(control)',
        '"Policy.allowed(control)"',
        'hovered /* Policy.allowed(control) */',
    ):
        body = tokens('visible: ' + source)
        assert not requires_decision(binding(body, 'visible'), 'Policy.allowed'), (
            'A named call must be a required visibility conjunct, not a comment or bypass: '
            + source
        )


def test_tooltip_uses_share_one_level_decision():
    failures = []
    found = []
    shared = sources()['app/qml/Base/Gui/Elements/ToolTip.qml']
    root = list(qml_objects(shared))[-1][1]
    visible = binding(root, 'visible')
    decisions = set(re.findall(r'\b([\w.]+)\s*\(', ' '.join(visible)))
    decisions -= {'Boolean', 'qsTr'}
    if len(decisions) != 1:
        failures.append(
            'Base/Gui/Elements/ToolTip.qml: shared visibility must invoke one level decision'
        )
    for path, source in sources().items():
        if deferred(path):
            continue
        words = tokens(re.sub(r'property\s+bool\s+showToolTips\s*:\s*(?:true|false)', '', source))
        failures.extend(
            path + ': direct legacy showToolTips read'
            for word in words
            if word.endswith('showToolTips')
        )
        for kind, body in qml_objects(source):
            if kind.rsplit('.', 1)[-1] not in {'ToolTip', 'WarningToolTip'}:
                continue
            found.append(path)
            bindings = dict(properties(body))
            # The shared tooltip owns the level decision; uses inherit it. A local
            # visible binding is allowed only through the same decision method.
            if 'visible' in bindings:
                expression = binding(body, 'visible')
                if not any(requires_decision(expression, decision) for decision in decisions):
                    failures.append(path + ': tooltip visibility bypasses the shared decision')
    assert found, (
        'The census must reach actual tooltip declarations, including the shared component'
    )
    assert not failures, (
        'Every tooltip use follows one level decision; unit 6 defers '
        + ', '.join(DEFERRED['files'])
        + '; violations: '
        + '; '.join(failures)
    )


def test_every_popup_button_has_an_icon():
    all_sources = sources()
    roots = {}
    for path, source in all_sources.items():
        objects = list(qml_objects(source))
        if objects:
            roots[Path(path).stem] = objects[-1]

    def inherits(kind, targets, seen=()):
        short = kind.rsplit('.', 1)[-1]
        if short in targets:
            return True
        if short in roots and short not in seen:
            return inherits(roots[short][0], targets, (*seen, short))
        return False

    def icon(kind, body, seen=()):
        props = dict(properties(body))
        if any(
            key in props and props[key] not in {'""', "''"}
            for key in ('fontIcon', 'icon.source', 'icon.name')
        ):
            return True
        short = kind.rsplit('.', 1)[-1]
        return short in roots and short not in seen and icon(*roots[short], (*seen, short))

    failures = []
    count = 0
    for path, source in all_sources.items():
        if deferred(path):
            continue
        for kind, body in qml_objects(source):
            if not inherits(kind, {'Popup', 'Dialog', 'Menu', 'AppDialog'}):
                continue
            # Reparse the complete popup body so nested layout containers cannot
            # hide a button. Strings and comments remain lexical tokens.
            for button, contents in qml_objects(' '.join(body)):
                if not inherits(button, {'Button', 'ToolButton', 'MenuItem', 'DialogButtonBox'}):
                    continue
                count += 1
                if not icon(button, contents):
                    label = dict(properties(contents)).get(
                        'objectName', dict(properties(contents)).get('text', button)
                    )
                    failures.append(f'{path}: {button} {label}')
    assert count, 'The popup census must visit actual nested popup buttons'
    assert not failures, (
        'Every popup button has an icon; no unnamed exceptions; unit 6 defers '
        + ', '.join(DEFERRED['files'])
        + '; violations: '
        + '; '.join(sorted(set(failures)))
    )
