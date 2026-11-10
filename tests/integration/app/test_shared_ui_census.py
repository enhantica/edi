"""Shared control policy and popup icons, from the product's UI rules."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from tests.integration.py.test_table_and_about_contract import properties, qml_objects, tokens

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'app/qml'
DEFERRED = json.loads((ROOT / 'tests/fixtures/shared_ui/deferred.json').read_text())


def pinned_gui():
    cmake = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    cache = (ROOT / 'build/app/CMakeCache.txt').read_text()
    match = re.search(r'^FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS:[^=]*=(.+)$', cache, re.MULTILINE)
    if not match or not match[1].strip():
        match = re.search(r'^gui_components_SOURCE_DIR:[^=]*=(.+)$', cache, re.MULTILINE)
    assert match, 'The crop census requires the GUI source resolved by the configured edi build'
    src = Path(match[1]) / 'src'
    expected = re.search(r'set\(EDI_GUI_COMPONENTS_SRC_SHA256\s+([0-9a-f]{64})\)', cmake)
    assert expected and src.is_dir(), "The configured GUI must carry edi's pinned source tree"
    inventory = ''.join(
        f'{path.relative_to(src).as_posix()} {hashlib.sha256(path.read_bytes()).hexdigest()}\n'
        for path in sorted(src.rglob('*'), key=lambda p: p.relative_to(src).as_posix())
        if path.is_file()
    )
    assert hashlib.sha256(inventory.encode()).hexdigest() == expected[1], (
        'The crop gate must read the current edi pin, never stale or locally edited GUI files'
    )
    return src / 'EasyApplication/Gui'


def sources():
    result = {path.relative_to(ROOT).as_posix(): path.read_text() for path in QML.rglob('*.qml')}
    base = pinned_gui().parent
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

    prefix = 'import EasyApplication.Gui.Globals as Policy; '
    for kind, visible, delay in (
        ('ToolTip', 'visible', ''),
        ('WarningToolTip', 'visible', ''),
        ('Button', 'ToolTip.visible', 'ToolTip.delay: Policy.Vars.toolTipDelay;'),
    ):
        call = 'Policy.Vars.toolTipAllowed(false, false)'
        valid = prefix + kind + ' { ' + delay + visible + ': ' + call + ' }'
        assert not tooltip_violations(valid), (
            'Explicit and attached level decisions remain admissible'
        )
        for plant in (
            valid.replace('toolTipAllowed', 'unrelatedHelper'),
            valid.replace('Policy.Vars.toolTipAllowed(false, false)', 'true'),
            valid.replace(call, 'true || ' + call),
        ):
            assert tooltip_violations(plant), (
                'An unrelated helper or bypass cannot become the expected policy'
            )
    assert tooltip_violations(valid.replace('ToolTip.delay: Policy.Vars.toolTipDelay;', '')), (
        'Attached tooltips must use the shared delay as well as the level decision'
    )


def tooltip_violations(source):
    # ADR-0076 names the entry point; the level actor checks gate 2's truth table.
    aliases = re.findall(r'import\s+EasyApplication.Gui.Globals\s+as\s+(\w+)', source)
    decisions = {alias + '.Vars.toolTipAllowed' for alias in aliases}
    failures = []
    for kind, body in qml_objects(source):
        explicit = kind.rsplit('.', 1)[-1] in {'ToolTip', 'WarningToolTip'}
        visible = 'visible' if explicit else 'ToolTip.visible'
        delay_name = 'delay' if explicit else 'ToolTip.delay'
        if delay_name in dict(properties(body)) and binding(body, delay_name) not in [
            [alias + '.Vars.toolTipDelay'] for alias in aliases
        ]:
            failures.append(delay_name + ' freezes a per-instance delay outside the shared policy')
        if visible not in dict(properties(body)):
            continue
        if not any(requires_decision(binding(body, visible), name) for name in decisions):
            failures.append(visible + ' bypasses the level decision')
        if not explicit and binding(body, 'ToolTip.delay') not in [
            [alias + '.Vars.toolTipDelay'] for alias in aliases
        ]:
            failures.append('attached tooltip bypasses the shared delay')
    return failures


def test_tooltip_uses_share_one_level_decision():
    failures = []
    found = []
    for path, source in sources().items():
        if deferred(path) and path not in {
            'app/qml/Main.qml',
            'app/qml/Components/AppPreferencesDialog.qml',
            'app/qml/Globals/Preferences.qml',
        }:
            continue
        words = tokens(re.sub(r'property\s+bool\s+showToolTips\s*:\s*(?:true|false)', '', source))
        failures.extend(
            path + ': direct legacy showToolTips read'
            for word in words
            if word.endswith('showToolTips')
        )
        for kind, body in qml_objects(source):
            if kind.rsplit('.', 1)[-1] in {
                'ToolTip',
                'WarningToolTip',
            } or 'ToolTip.visible' in dict(properties(body)):
                found.append(path)
        failures.extend(path + ': ' + problem for problem in tooltip_violations(source))
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
                if inherits(button, {'DialogButtonBox'}):
                    continue
                if not inherits(button, {'Button', 'ToolButton', 'MenuItem'}):
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


def test_tooltip_choices_flush_browser_storage():
    source = (QML / 'Globals/Preferences.qml').read_text()
    words = tokens(source)
    for handler in ('onToolTipLevelChanged', 'onToolTipDelayChanged'):
        start = words.index(handler)
        body = binding(words[start:], handler)
        sync = ['settings.sync', '(', ')', ';']
        flush = ['ApplicationInfo.storeSettings', '(', ')']
        sync_at = next((i for i in range(len(body)) if body[i : i + len(sync)] == sync), -1)
        after_sync = body[sync_at + len(sync) : sync_at + len(sync) + len(flush)]
        assert sync_at >= 0 and after_sync == flush, (
            'Every tooltip choice syncs its file then immediately stores browser settings: '
            + handler
        )


def test_popup_census_preserves_custom_footer_buttons(monkeypatch):
    inventory = {
        'base/Button.qml': 'import QtQuick.Templates as T; T.Button {}',
        'base/DialogButtonBox.qml': 'import QtQuick.Templates as T; T.DialogButtonBox {}',
        'app/Dialog.qml': (
            'Dialog { DialogButtonBox { standardButtons: DialogButtonBox.Ok } '
            'Button { text: "Custom"; fontIcon: "plus" } }'
        ),
    }
    monkeypatch.setattr(__name__ + '.sources', lambda: inventory)
    test_every_popup_button_has_an_icon()
    for body in (
        (
            'Dialog { DialogButtonBox { Button { text: "Nested custom" } } '
            'Button { text: "Custom"; fontIcon: "plus" } }'
        ),
        (
            'Dialog { DialogButtonBox { standardButtons: DialogButtonBox.Ok } '
            'Button { text: "Custom" } }'
        ),
    ):
        inventory['app/Dialog.qml'] = body
        with pytest.raises(AssertionError, match='Every popup button has an icon'):
            test_every_popup_button_has_an_icon()


@pytest.mark.parametrize(
    ('kind', 'visible', 'delay'),
    [
        ('ToolTip', 'requested', 'delay'),
        ('WarningToolTip', 'requested', 'delay'),
        ('Button', 'ToolTip.text', 'ToolTip.delay'),
    ],
)
def test_tooltip_delay_census_rejects_instance_overrides(kind, visible, delay):
    prefix = 'import EasyApplication.Gui.Globals as Policy; '
    source = prefix + kind + ' { ' + visible + ': true; ' + delay + ': Policy.Vars.toolTipDelay; }'
    assert not tooltip_violations(source), (
        'ADR-0076: an explicit delay remains bound to the one live shared setting'
    )
    for frozen in [
        '1000',
        '1500',
        'savedDelay',
        'Policy.Vars.toolTipDelay + 1',
        'true ? 1000 : Policy.Vars.toolTipDelay',
    ]:
        assert tooltip_violations(source.replace('Policy.Vars.toolTipDelay;', frozen + ';')), (
            'ADR-0076: explicit and attached tooltips cannot freeze or bypass the live delay'
        )
