"""A control has one help owner; refusal takes priority over ordinary help."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from tests.fixtures.shared_ui.generate_tooltip_matrix import qt_control_reference
from tests.integration.app.test_shared_ui_census import ROOT, sources
from tests.integration.py.test_table_and_about_contract import TOKEN, properties

QT_CONTROLS_REFERENCE = json.loads(
    (ROOT / 'tests/fixtures/shared_ui/qt_controls.json').read_text()
)
QT_MODULE_TYPES = {
    uri: frozenset(names) for uri, names in QT_CONTROLS_REFERENCE['modules'].items()
}

# The shared-control contract assigns these entrances to their base element.
# Removing a base popup must not promote its derived wrapper to the accepted owner.
ELEMENT_HELP_OWNERS = frozenset({
    'Button',
    'CheckBox',
    'ComboBox',
    'Pill',
    'SideBarButton',
    'Slider',
    'SpinBox',
    'StatusBarItem',
    'TabButton',
    'TextField',
    'ToolButton',
})
HELP_OWNERS = frozenset('EasyApplication.Gui.Elements.' + name for name in ELEMENT_HELP_OWNERS) | {
    'EasyApplication.Gui.Components.ListViewLabel',
    'EasyApplication.Gui.Components.ListViewTextInput',
    'edi.app.ChartToolButton',
    'edi.app.StatusBarItem',
}


def expression(body, name):
    depth = ternary_depth = 0
    for i, word in enumerate(body[:-1]):
        if depth == 0 and ternary_depth == 0 and word == name and body[i + 1] == ':':
            result, level, ternary = [], 0, 0
            for j in range(i + 2, len(body)):
                value = body[j]
                new_property = (
                    j + 1 < len(body)
                    and body[j + 1] == ':'
                    and re.fullmatch(r'[A-Za-z_][\w.]*', value)
                )
                child = body[j + 1 : j + 2] == ['{'] and re.fullmatch(r'(?:\w+\.)*[A-Z]\w*', value)
                if (
                    level == 0
                    and ternary == 0
                    and (
                        value in {'property', 'readonly', 'function', 'signal', ';'}
                        or new_property
                        or child
                    )
                ):
                    break
                result.append(value)
                if level == 0:
                    if value == '?' and body[j + 1 : j + 2] != ['?'] and body[j - 1] != '?':
                        ternary += 1
                    elif value == ':' and ternary:
                        ternary -= 1
                level += value in {'(', '[', '{'}
                level -= value in {')', ']', '}'}
            return result
        if depth == 0:
            if word == '?':
                ternary_depth += 1
            elif word == ':' and ternary_depth:
                ternary_depth -= 1
        depth += word in {'(', '[', '{'}
        depth -= word in {')', ']', '}'}
    return []


@dataclass(eq=False)
class Node:
    kind: str
    start: int
    parent: object
    words: list = field(default_factory=list)
    props: dict = field(default_factory=dict)
    component: object = None


@dataclass(eq=False)
class Component:
    path: str
    name: str
    root: Node
    nodes: list
    imports: dict


def imported_modules(words):
    imports = {'': []}
    for i, word in enumerate(words[:-1]):
        if word != 'import' or not re.fullmatch(r'[A-Za-z_]\w*(?:\.\w+)*', words[i + 1]):
            continue
        uri, j = words[i + 1], i + 2
        while j < len(words) and re.fullmatch(r'[0-9.]+', words[j]):
            j += 1
        if words[j : j + 1] == ['as'] and j + 1 < len(words):
            imports[words[j + 1]] = uri
        else:
            imports[''].append(uri)
    return imports


def parse(path, source):
    lex = [m for m in TOKEN.finditer(source) if not m.group().startswith(('//', '/*'))]
    words = [m.group() for m in lex]
    stack, nodes = [], []
    for i, word in enumerate(words):
        if word == '{':
            node = None
            if i and re.fullmatch(r'(?:\w+\.)*[A-Z]\w*', words[i - 1]):
                parent = next((n for _, n in reversed(stack) if n), None)
                node = Node(words[i - 1], lex[i - 1].start(), parent)
                node.body_start = i + 1
                node.inline = words[i - 4] == 'component' if i >= 4 else False
                node.inline_name = words[i - 3] if node.inline else ''
                nodes.append(node)
            stack.append((i, node))
        elif word == '}' and stack:
            _, node = stack.pop()
            if node:
                node.words = words[node.body_start : i]
                node.props = {
                    name: expression(node.words, name)
                    for name, _ in properties(node.words)
                    if re.fullmatch(r'[A-Za-z_][\w.]*', name)
                }
    if not nodes:
        return []
    roots = [n for n in nodes if n.parent is None or n.inline]
    imports = imported_modules(words)
    result = []
    for root in roots:
        name = root.inline_name or Path(path).stem
        members = []
        for node in nodes:
            ancestor = node
            while ancestor and ancestor not in roots:
                ancestor = ancestor.parent
            if ancestor is root:
                members.append(node)
        component = Component(path, name, root, members, imports)
        component.source = source
        for node in members:
            node.component = component
        result.append(component)
    return result


def split_top(words, op):
    level = 0
    for i, word in enumerate(words):
        if level == 0 and words[i : i + len(op)] == op:
            return words[:i], words[i + len(op) :]
        level += word in {'(', '[', '{'}
        level -= word in {')', ']', '}'}
    return None


def unwrap(words):
    while words[:1] == ['('] and words[-1:] == [')']:
        level = 0
        consumed = 0
        for word in words:
            consumed += 1
            level += word == '('
            level -= word == ')'
            if level == 0:
                break
        if consumed != len(words):
            break
        words = words[1:-1]
    return words


def truth(words, refusal):
    words = unwrap(words)
    for op in (['|', '|'], ['&', '&']):
        parts = split_top(words, op)
        if parts:
            a, b = (truth(part, refusal) for part in parts)
            return {x or y if op[0] == '|' else x and y for x in a for y in b}
    if words[:1] == ['!']:
        return {not value for value in truth(words[1:], refusal)}
    if len(words) == 1 and words[0] in refusal | {'true', 'false'}:
        return {words != ['false']}
    for op in (['=', '=', '='], ['!', '=', '='], ['=', '='], ['!', '=']):
        parts = split_top(words, op)
        if parts:
            a, b = parts
            if a in (["''"], ['""']):
                a, b = b, a
            if b in (["''"], ['""']):
                states = text_states(a, refusal)
                if states <= {'refusal', 'empty'}:
                    return {((state != 'empty') == (op[0] == '!')) for state in states}
    return {False, True}


def text_states(words, refusal):
    words = unwrap(words)
    if words in (["''"], ['""']):
        return {'empty'}
    if len(words) == 1 and words[0] in refusal:
        return {'refusal'}
    level = ternary = 0
    question = None
    for i, word in enumerate(words):
        if level == 0 and word == '?':
            if question is None:
                question = i
            ternary += 1
        elif level == 0 and word == ':' and question is not None:
            ternary -= 1
            if ternary == 0:
                condition = truth(words[:question], refusal)
                result = set()
                if True in condition:
                    result |= text_states(words[question + 1 : i], refusal)
                if False in condition:
                    result |= text_states(words[i + 1 :], refusal)
                return result
        level += word in {'(', '[', '{'}
        level -= word in {')', ']', '}'}
    return {'help'}


class Census:
    def __init__(self, inventory):
        self.components = [c for path, source in inventory.items() for c in parse(path, source)]
        self.by_name = {}
        for component in sorted(self.components, key=lambda c: c.path.startswith('app/')):
            self.by_name[component.name] = component
        self.qualified = {}
        for c in sorted(self.components, key=lambda c: c.path.startswith('app/')):
            self.qualified[self.module(c) + '.' + c.name] = c
        self.local = {(c.path, c.name): c for c in self.components}
        self.issues = set()

    @staticmethod
    def module(component):
        for prefix in ('base/', 'app/qml/Base/'):
            if component.path.startswith(prefix):
                return 'EasyApplication.' + str(
                    Path(component.path[len(prefix) :]).parent
                ).replace('/', '.')
        return 'edi.app'

    def failure(self, node, message):
        component = node.component
        line = component.source.count('\n', 0, node.start) + 1
        self.issues.add(f'{component.path}:{line}: {message}')

    def resolve(self, node):
        component = node.component
        kind = node.kind
        short = kind.rsplit('.', 1)[-1]
        if '.' in kind:
            alias = kind.split('.')[0]
            uri = component.imports.get(alias)
            if uri:
                return self.qualified.get(uri + '.' + short)
            return self.local.get((component.path, short))
        local = self.local.get((component.path, short))
        if local and local is not component:
            return local
        return self._unqualified(component, short)

    def _unqualified(self, component, short):
        for uri in reversed(component.imports.get('', [])):
            if short in QT_MODULE_TYPES.get(uri, ()):
                return None
            target = self.qualified.get(uri + '.' + short)
            if target:
                return target
        target = self.qualified.get(self.module(component) + '.' + short)
        if target:
            return target
        if not component.imports.get('') and len(component.imports) == 1:
            return self.by_name.get(short)
        return None

    def chain(self, node):
        seen = set()
        while node:
            yield node
            parent = self.resolve(node)
            if not parent or parent in seen:
                break
            seen.add(parent)
            node = parent.root

    def tip(self, node):
        return any(
            n.kind.rsplit('.', 1)[-1] in {'ToolTip', 'WarningToolTip'} for n in self.chain(node)
        )

    def warning(self, node):
        return node.kind.rsplit('.', 1)[-1] == 'WarningToolTip' or any(
            n.component.name == 'WarningToolTip' for n in self.chain(node)
        )

    @staticmethod
    def ids(component):
        return {n.props['id'][0]: n for n in component.nodes if n.props.get('id')}

    def subject(self, tip):
        ids = self.ids(tip.component)
        if tip.parent:
            inherited = self.resolve(tip.parent)
            if inherited and self.owner(inherited.root):
                return tip.parent
        candidates = []
        for prop in ('parent', 'text', 'requested', 'visible'):
            for word in tip.props.get(prop, []):
                identifier = word.split('.')[0]
                if identifier in ids and ids[identifier] is not tip:
                    target = ids[identifier]
                    if prop == 'parent' or any(self.local_help(n) for n in self.chain(target)):
                        candidates.append(target)
            if candidates:
                return candidates[0]
        parent = tip.parent
        while parent and parent.kind.rsplit('.', 1)[-1] in {'Component', 'Loader'}:
            parent = parent.parent
        parent = parent or tip.component.root
        candidates = [
            n
            for n in tip.component.nodes
            if n.parent is parent
            and n is not tip
            and self.owner(n)
            and self.owner(n) is not tip.component
            and self.effective(n, 'ToolTip.text')[0] not in ([], ['""'], ["''"])
        ]
        return candidates[0] if len(candidates) == 1 else parent

    def local_help(self, node):
        component = node.component
        return [
            t
            for t in component.nodes
            if t is not component.root
            and self.tip_shallow(t)
            and not self.warning_shallow(t)
            and self.root_target(t, node)
        ]

    @staticmethod
    def tip_shallow(node):
        return node.kind.rsplit('.', 1)[-1] in {'ToolTip', 'WarningToolTip'}

    @staticmethod
    def warning_shallow(node):
        return node.kind.rsplit('.', 1)[-1] == 'WarningToolTip'

    @staticmethod
    def root_target(tip, target):
        identifier = target.props.get('id', [''])[0]
        parent = tip.props.get('parent', [])
        if parent:
            return parent == [identifier]
        text = tip.props.get('text', [])
        if identifier and any(word.startswith(identifier + '.') for word in text):
            return True
        return tip.parent is target

    def owner(self, node):
        # The oldest element in the inheritance chain owns the help entrance.
        roots = list(self.chain(node))
        for ancestor in reversed(roots):
            if self.module(ancestor.component) + '.' + ancestor.component.name in HELP_OWNERS:
                return ancestor.component
        for ancestor in reversed(roots):
            for tip in ancestor.component.nodes:
                if (
                    tip is not ancestor.component.root
                    and self.tip(tip)
                    and not self.warning(tip)
                    and self.root_target(tip, ancestor)
                ):
                    return ancestor.component
        return None

    def effective(self, node, prop):
        for ancestor in self.chain(node):
            if prop in ancestor.props:
                return ancestor.props[prop], ancestor
        return [], node

    def expand_refusal(self, words, node, names, seen=frozenset()):
        """Follow computed warning guards, keeping caller-supplied help unknown."""
        result = []
        root_ids = {n.props['id'][0] for n in self.chain(node) if n.props.get('id')}
        for word in words:
            parts = word.split('.')
            local = len(parts) == 1 or parts[0] in root_ids
            prop = parts[-1] if local else ''
            if word.endswith('.ToolTip.text') and parts[0] in root_ids:
                prop = 'ToolTip.text'
            replacement, _ = self.effective(node, prop)
            if (
                any(prop == name.rsplit('.', 1)[-1] for name in names)
                or not replacement
                or prop in seen
            ):
                result.append(word)
                continue
            expanded = self.expand_refusal(replacement, node, names, seen | {prop})
            if prop == 'ToolTip.text' or any(t in names for t in expanded):
                result.extend(['(', *expanded, ')'])
            else:
                result.append(word)
        return result

    def check_tips(self, component):
        for tip in component.nodes:
            if tip is component.root or not self.tip(tip) or self.warning(tip):
                continue
            subject = self.subject(tip)
            owner = self.owner(subject)
            if owner and owner is not component:
                identifier = subject.props.get('id', [subject.kind])[0]
                self.failure(tip, f'help for {identifier} belongs to {owner.path}; second popup')

    def check_refusal(self, node, owner):
        if not any('refusal' in n.props for n in self.chain(node)):
            return
        names = {'refusal', 'this.refusal'} | {
            n.props['id'][0] + '.refusal' for n in self.chain(node) if n.props.get('id')
        }
        for tip in owner.nodes:
            if not self.tip(tip) or self.warning(tip) or not self.root_target(tip, owner.root):
                continue
            words = self.expand_refusal(tip.props.get('text', []), node, names)
            requests = [tip.props.get('requested', tip.props.get('visible', []))]
            ancestor = tip.parent
            while ancestor:
                if ancestor.kind.rsplit('.', 1)[-1] == 'Loader':
                    requests.append(ancestor.props.get('active', []))
                ancestor = ancestor.parent
            blocked = any(
                truth(self.expand_refusal(r, node, names), names) == {False} for r in requests
            )
            states = text_states(words, names)
            warning = any(
                self.warning(t) and self.root_target(t, node)
                for t in node.component.nodes
                if t is not node.component.root
            )
            competes = 'help' in states or (warning and states != {'empty'})
            if competes and not blocked:
                origin = next(n for n in self.chain(node) if 'refusal' in n.props)
                if any(w.endswith('.ToolTip.text') for w in tip.props.get('text', [])):
                    _, origin = self.effective(node, 'ToolTip.text')
                self.failure(origin, f"help owned by {owner.path} survives this control's refusal")

    def check_attached(self, component):
        ids = self.ids(component)
        for node in component.nodes:
            owner = self.owner(node)
            if not owner:
                continue
            self.check_refusal(node, owner)
            for prop, value in node.props.items():
                if prop.endswith('ToolTip.visible') and value != ['false']:
                    self.failure(node, f'{prop} opens beside the help owner {owner.path}')
        words = [
            m for m in TOKEN.finditer(component.source) if not m.group().startswith(('//', '/*'))
        ]
        aliases = {
            name: value[0]
            for name, value in component.root.props.items()
            if len(value) == 1 and value[0].endswith('.ToolTip')
        }
        for i, match in enumerate(words):
            word = match.group()
            if (
                word in {'const', 'let', 'var'}
                and i + 3 < len(words)
                and words[i + 2].group() == '='
            ):
                aliases[words[i + 1].group()] = words[i + 3].group()
            target_word = word
            for alias, target in aliases.items():
                if word.startswith(alias + '.'):
                    target_word = target + word[len(alias) :]
            call = i + 1 < len(words) and words[i + 1].group() == '('
            assignment = (
                target_word.endswith('.ToolTip.visible')
                and i + 2 < len(words)
                and words[i + 1].group() == '='
                and words[i + 2].group() != 'false'
            )
            if (re.search(r'\.ToolTip\.(?:show|open)$', target_word) and call) or assignment:
                target = ids.get(target_word.split('.')[0], component.root)
                owner = self.owner(target)
                if owner:
                    self._at_match(component, match, f'attached popup bypasses {owner.path}')
            self._check_popup_call(component, match, target_word, call, words[i : i + 3])

    def _check_popup_call(self, component, match, target_word, call, words):
        if call and target_word.endswith(('.open', '.show')):
            owner = self._call_owner(component, target_word.rsplit('.', 1)[0])
            if owner and owner is not component:
                self._at_match(component, match, f'wrapper opens help belonging to {owner.path}')
        if match.group() in {'Qt.createQmlObject', 'Qt.createComponent'} and len(words) == 3:
            argument = words[2].group()
            if re.search(r'(?:ToolTip|WarningToolTip)\s*(?:\{|\.qml)', argument):
                self._at_match(component, match, 'dynamic tooltip has no declared help owner')

    def _call_owner(self, component, reference):
        ids = self.ids(component)
        if reference in ids and self.tip(ids[reference]):
            return self.owner(self.subject(ids[reference]))
        parts = reference.split('.')
        node = ids.get(parts[0], component.root)
        prop = parts[-1]
        for ancestor in self.chain(node):
            target = ancestor.props.get(prop, [])
            target_ids = self.ids(ancestor.component)
            if len(target) == 1 and target[0] in target_ids and self.tip(target_ids[target[0]]):
                return self.owner(node)
        return None

    def _at_match(self, component, match, message):
        line = component.source.count('\n', 0, match.start()) + 1
        self.issues.add(f'{component.path}:{line}: {message}')

    def run(self):
        for component in self.components:
            self.check_tips(component)
            self.check_attached(component)
        return sorted(self.issues)


CONTRACT_OWNERS = {
    'EasyApplication.Gui.Elements.Button': {'toolTipSelfExplanatory'},
    'EasyApplication.Gui.Components.ListViewLabel': {
        'fullText',
        'shortened',
        'toolTipSelfExplanatory',
    },
    'EasyApplication.Gui.Components.ListViewTextInput': {
        'fullText',
        'shortened',
        'warned',
        'toolTipSelfExplanatory',
    },
    'EasyApplication.Gui.Elements.TextField': {
        'fullText',
        'shortened',
        'warned',
        'toolTipSelfExplanatory',
    },
    'EasyApplication.Gui.Elements.ComboBox': {'warned', 'toolTipSelfExplanatory'},
    'EasyApplication.Gui.Elements.Slider': {'toolTipText', 'toolTipSelfExplanatory'},
}


def contract_owner_issues(inventory):
    # These are the declared base entrances, not a second whole-application census.
    # The separate ancestry and ownership gates retain all wrappers and prior sites.
    owner_names = {name.rsplit('.', 1)[-1] for name in CONTRACT_OWNERS} | {'TextInput'}
    census = Census({
        path: source for path, source in inventory.items() if Path(path).stem in owner_names
    })
    for name, inputs in CONTRACT_OWNERS.items():
        component = census.qualified.get(name)
        if component is None:
            census.issues.add(name + ': ADR-0076 base owner is missing')
            continue
        for prop in inputs:
            if not any(prop in node.props for node in census.chain(component.root)):
                census.failure(component.root, 'ADR-0076 caller input is missing: ' + prop)
        ordinary = [
            tip
            for tip in component.nodes
            if tip is not component.root
            and census.tip(tip)
            and not census.warning(tip)
            and census.root_target(tip, component.root)
        ]
        if len(ordinary) != 1:
            census.failure(component.root, 'ADR-0076 base declares exactly one ordinary popup')
        if 'warned' not in inputs:
            continue
        names = {'warned'} | {
            node.props['id'][0] + '.warned'
            for node in census.chain(component.root)
            if node.props.get('id')
        }
        for tip in ordinary:
            requests = [tip.props.get('requested', tip.props.get('visible', []))]
            ancestor = tip.parent
            while ancestor:
                if ancestor.kind.rsplit('.', 1)[-1] == 'Loader':
                    requests.append(ancestor.props.get('active', []))
                ancestor = ancestor.parent
            if not any(
                truth(census.expand_refusal(request, component.root, names), names) == {False}
                for request in requests
            ):
                census.failure(
                    tip, 'ADR-0076 ordinary request must yield while its own warned input is true'
                )
    return sorted(census.issues)


def test_contract_bases_declare_inputs_and_yield_to_the_warning_owner():
    failures = contract_owner_issues(sources())
    assert not failures, (
        'ADR-0076 bases retain one owner, all caller inputs and a warning suppression boundary:\n'
        + '\n'.join(failures)
    )


def test_contract_input_and_warning_boundary_controls():
    clean = {}
    for name, inputs in CONTRACT_OWNERS.items():
        path = 'base/' + name.removeprefix('EasyApplication.').replace('.', '/') + '.qml'
        declarations = ''.join(
            'property '
            + ('string ' if prop in {'fullText', 'toolTipText'} else 'bool ')
            + prop
            + ': '
            + ('"";' if prop in {'fullText', 'toolTipText'} else 'false;')
            for prop in sorted(inputs)
        )
        request = 'control.hovered && !control.warned' if 'warned' in inputs else 'control.hovered'
        clean[path] = (
            'import QtQuick.Templates as T; T.Control { id: control; '
            + declarations
            + 'ToolTip { text: control.ToolTip.text; requested: '
            + request
            + '; selfExplanatory: control.toolTipSelfExplanatory } }'
        )
    assert not contract_owner_issues(clean), (
        'ADR-0076 complete base inputs and a request guarded by the same control are admitted'
    )
    for name, inputs in CONTRACT_OWNERS.items():
        path = 'base/' + name.removeprefix('EasyApplication.').replace('.', '/') + '.qml'
        for prop in inputs:
            damaged = dict(clean)
            damaged[path] = re.sub(
                r'property (?:bool|string) ' + prop + r': [^;]+;', '', clean[path]
            )
            assert any(
                'input is missing: ' + prop in issue for issue in contract_owner_issues(damaged)
            ), 'ADR-0076 a missing caller input is rejected at every assigned base owner: ' + name
        if 'warned' not in inputs:
            continue
        for wrong in (
            'control.hovered',
            'control.hovered && !other.warned',
            'control.hovered || !control.warned',
        ):
            damaged = dict(clean)
            damaged[path] = clean[path].replace('control.hovered && !control.warned', wrong)
            assert any(
                'yield while its own warned' in issue for issue in contract_owner_issues(damaged)
            ), 'ADR-0076 missing, foreign or disjunctive warning guards cannot reopen help'
        loader = (
            clean[path]
            .replace('ToolTip {', 'Loader { active: !control.warned; sourceComponent: ToolTip {')
            .replace('requested: control.hovered && !control.warned', 'requested: true')
            + ' }'
        )
        assert not contract_owner_issues({**clean, path: loader}), (
            'ADR-0076 warning suppression may guard the actual owner loader instead of its popup'
        )
    for name in CONTRACT_OWNERS:
        path = 'base/' + name.removeprefix('EasyApplication.').replace('.', '/') + '.qml'
        removed = clean[path].replace('ToolTip {', 'Item {')
        assert any(
            'exactly one ordinary popup' in issue
            for issue in contract_owner_issues({**clean, path: removed})
        ), 'ADR-0076 declaring inputs without the assigned renderer cannot satisfy ownership'
        duplicated = clean[path][:-1] + 'ToolTip { text: control.ToolTip.text; requested: true } }'
        assert any(
            'exactly one ordinary popup' in issue
            for issue in contract_owner_issues({**clean, path: duplicated})
        ), 'ADR-0076 the base itself cannot declare competing ordinary renderers'
        assert contract_owner_issues({
            key: value for key, value in clean.items() if key != path
        }), 'ADR-0076 removing an assigned base cannot silently shrink the owner inventory'


def test_help_has_one_element_owner_and_refusal_priority():
    inventory = sources()
    failures = Census(inventory).run()
    assert not failures, (
        'Every control has one element-owned help route and refusal priority:\n'
        + '\n'.join(failures)
    )


def test_ownership_census_rejects_inheritance_wrapper_and_open_escapes():
    base = (
        'import QtQuick.Templates as T; T.Button { id: control;'
        ' ToolTip { text: control.ToolTip.text; requested: control.hovered } }'
    )
    clean = {'base/Gui/Elements/Button.qml': base}
    assert not Census(clean).run(), 'The base element may own its one help popup'
    for body in (
        (
            'Button { id: control; ToolTip { text: control.ToolTip.text; '
            'requested: control.hovered } }'
        ),
        (
            'Item { Button { id: child; ToolTip.text: "Help" } ToolTip { '
            'text: child.ToolTip.text; requested: child.hovered } }'
        ),
        'Item { Button { id: child } ToolTip { parent: child; text: "Help"; requested: true } }',
        (
            'Item { Button { ToolTip.text: "Base help" } '
            'ToolTip { text: "Wrapper help"; requested: true } }'
        ),
        'Button { ToolTip.visible: true }',
        'Button { id: child; onClicked: child.ToolTip.visible = true }',
        'Button { id: child; property alias tip: child.ToolTip; onClicked: tip.open() }',
        'Button { id: child; onClicked: child.ToolTip.show("Help") }',
        'Button { id: child; onClicked: { const t = child.ToolTip; t.show("Help") } }',
        'Button { Loader { sourceComponent: Component { ToolTip { text: "Help" } } } }',
        'Button { onClicked: Qt.createQmlObject("ToolTip { visible: true }", this) }',
    ):
        result = Census({**clean, 'app/qml/Derived.qml': body}).run()
        assert result and any('app/qml/Derived.qml:' in failure for failure in result), (
            'Inherited, wrapper, attached, loader and imperative escapes name their source line: '
            + body
        )
    for expr in ('refusal !== "" ? "" : helpText', 'refusal === "" ? helpText : ""'):
        source = 'Button { property string refusal: ""; ToolTip.text: ' + expr + ' }'
        assert not Census({**clean, 'app/qml/Field.qml': source}).run(), (
            'A derived control may supply help while preserving refusal priority'
        )
    for owner in HELP_OWNERS:
        uri, name = owner.rsplit('.', 1)
        root = 'base/' + uri.removeprefix('EasyApplication.').replace('.', '/')
        if uri == 'edi.app':
            root = 'app/qml/Components'
        removed = 'import QtQuick.Templates as T; T.Control {}'
        duplicate = (
            'import ' + uri + ' as E; E.' + name + ' { ToolTip { text: "Help"; requested: true } }'
        )
        assert Census({
            root + '/' + name + '.qml': removed,
            'app/qml/Derived.qml': duplicate,
        }).run(), (
            'Deleting a contracted base popup cannot transfer ownership to a derived component: '
            + owner
        )
    for expr in (
        'helpText',
        'other.refusal !== "" ? "" : helpText',
        'refusal !== "" ? helpText : ""',
    ):
        source = 'Button { property string refusal: ""; ToolTip.text: ' + expr + ' }'
        assert Census({**clean, 'app/qml/Field.qml': source}).run(), (
            'Ordinary help cannot survive a refusal or use a different control as its guard'
        )


def test_refusal_guards_follow_bindings_and_preserve_newline_boundaries():
    base = (
        'import QtQuick.Templates as T\nT.Button { id: control\n'
        'ToolTip { text: control.ToolTip.text; requested: control.hovered } }'
    )
    derived = (
        'Button { id: field\nproperty string refusal: ""\n'
        'property string helpText: ""\n'
        'readonly property string warning: refusal !== "" ? refusal : ""\n'
        'ToolTip.text: warning !== "" ? "" : helpText\n'
        'WarningToolTip { text: field.refusal; requested: true } }'
    )
    inventory = {'base/Gui/Elements/Button.qml': base, 'app/qml/Field.qml': derived}
    assert not Census(inventory).run(), (
        'Computed refusal priority remains valid across newline bindings and a warning child'
    )
    inventory['app/qml/Field.qml'] = derived.replace(
        'warning !== "" ? ""', 'warning !== "" ? helpText'
    )
    assert Census(inventory).run(), 'A computed refusal guard cannot leave help alive'
    guarded_base = (
        'import QtQuick.Templates as T; T.TextField { id: control; property bool warned: false; '
        'ToolTip { text: control.ToolTip.text; requested: control.hovered && !control.warned } }'
    )
    input_driven = (
        'TextField { id: field; property string refusal: ""; property string helpText: "Help"; '
        'warned: refusal !== ""; ToolTip.text: helpText; '
        'WarningToolTip { text: field.refusal; requested: field.warned && field.hovered } }'
    )
    composed = {'base/Gui/Elements/TextField.qml': guarded_base, 'app/qml/Value.qml': input_driven}
    assert not Census(composed).run(), (
        'ADR-0076 a warning suppresses the base request while semantic help remains populated'
    )
    for guard in ('false', 'other.refusal !== ""'):
        damaged = {
            **composed,
            'app/qml/Value.qml': input_driven.replace('refusal !== "";', guard + ';'),
        }
        assert Census(damaged).run(), (
            'ADR-0076 a missing or foreign caller warning input cannot leave base help alive'
        )


def test_warning_owner_requires_the_help_route_to_yield():
    base = (
        'import QtQuick.Templates as T; T.Button { id: control; '
        'ToolTip { text: control.ToolTip.text; requested: control.hovered } }'
    )
    field = (
        'Button { id: field; property string refusal: ""; '
        'ToolTip.text: refusal; WarningToolTip { text: field.refusal; requested: true } }'
    )
    assert Census({'base/Gui/Elements/Button.qml': base, 'app/qml/Field.qml': field}).run(), (
        'A separate warning popup owns the refusal; the help popup yields even with the same text'
    )


def test_wrapper_cannot_open_an_inherited_popup_alias():
    base = (
        'import QtQuick.Templates as T; T.Button { id: control; '
        'property alias helpPopup: help; '
        'ToolTip { id: help; text: control.ToolTip.text; requested: control.hovered } }'
    )
    wrapper = 'Item { Button { id: child } function showHelp() { child.helpPopup.open() } }'
    assert Census({'base/Gui/Elements/Button.qml': base, 'app/qml/Wrapper.qml': wrapper}).run(), (
        'Opening an inherited popup through its public alias still belongs to the base element'
    )


def test_qt_control_namespace_reference_matches_the_pinned_sdk():
    cache = (ROOT / 'build/app/CMakeCache.txt').read_text()
    qt = re.search(r'^Qt6_DIR:[^=]*=(.+)$', cache, re.MULTILINE)
    assert qt, 'ADR-0076 source ownership uses the Qt SDK selected by the configured native host'
    qml = Path(qt[1]).parents[1] / 'qt6/qml'
    for record in QT_CONTROLS_REFERENCE['files']:
        path = qml / record['name']
        assert path.is_file(), 'ADR-0076 source ownership requires the pinned Qt module metadata'
    imported = {
        uri
        for source in sources().values()
        for value in imported_modules([match.group() for match in TOKEN.finditer(source)]).values()
        for uri in (value if isinstance(value, list) else [value])
        if uri.startswith('QtQuick.Controls')
    }
    assert imported <= QT_MODULE_TYPES.keys(), (
        'ADR-0076 every imported Qt Controls namespace has an independently captured export list'
    )
    assert qt_control_reference(qml)['modules'] == QT_CONTROLS_REFERENCE['modules'], (
        'ADR-0076 source resolution uses the exported type names of the actual pinned Qt SDK'
    )


def test_explicit_qt_imports_do_not_inherit_an_implicit_custom_owner():
    base = 'import QtQuick.Templates as T; T.Button { ToolTip { text: "Base"; requested: true } }'
    clean = {'base/Gui/Elements/Button.qml': base}
    qt = 'import QtQuick.Controls; Button { ToolTip { text: "Standalone"; requested: true } }'
    assert not Census({**clean, 'base/Gui/Elements/GroupButton.qml': qt}).run(), (
        'ADR-0076 an explicit Qt Controls import resolves before an implicit custom-module type'
    )
    private = (
        'import QtQuick.Controls.impl; Button { ToolTip { text: "Duplicate"; requested: true } }'
    )
    assert Census({**clean, 'base/Gui/Elements/PrivateImport.qml': private}).run(), (
        'ADR-0076: private Qt namespaces cannot mask a custom inherited help owner'
    )
    for imported in (
        'import EasyApplication.Gui.Elements;',
        'import EasyApplication.Gui.Elements as E;',
    ):
        name = 'E.Button' if ' as E;' in imported else 'Button'
        child = imported + name + ' { ToolTip { text: "Duplicate"; requested: true } }'
        assert Census({**clean, 'app/qml/Derived.qml': child}).run(), (
            'ADR-0076 explicit custom-module imports retain their actual inherited help owner'
        )


def test_retained_wrappers_inherit_the_declared_popup_owner():
    census = Census(sources())
    owners = {
        'EasyApplication.Gui.Elements.GroupButton': 'EasyApplication.Gui.Elements.Button',
        'edi.app.NumberLabel': 'EasyApplication.Gui.Components.ListViewLabel',
        'edi.app.ValueField': 'EasyApplication.Gui.Elements.TextField',
        'edi.app.SelectorField': 'EasyApplication.Gui.Elements.ComboBox',
    }
    for child, owner in owners.items():
        component = census.qualified.get(child)
        assert component is not None, (
            'ADR-0076 every retained wrapper remains present in the production ownership inventory'
        )
        actual = {
            census.module(node.component) + '.' + node.component.name
            for node in census.chain(component.root)
        }
        assert owner in actual, (
            'ADR-0076 a retained wrapper inherits its assigned base rather than a Qt namesake: '
            + child
            + ' -> '
            + owner
        )
