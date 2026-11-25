"""Read watchdog navigation inputs from the app's declared pages and tab bars."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENARIO = 'e58-tabs'
TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')


def source(path):
    """Remove comments without consuming quoted strings or their delimiters."""
    return TOKENS.sub(lambda m: ' ' if m[0].startswith('/') else m[0], path.read_text())


def balanced(text, start):
    """Return a complete literal array/object, refusing incomplete declarations."""
    opening = text[start]
    closing = {'[': ']', '{': '}'}[opening]
    level, cursor = 0, start
    while cursor < len(text):
        if text[cursor] in {'"', "'"}:
            token = TOKENS.match(text, cursor)
            if token is None:
                raise ValueError('Unterminated quoted QML declaration')
            cursor = token.end()
            continue
        if text[cursor] == opening:
            level += 1
        elif text[cursor] == closing:
            level -= 1
            if not level:
                return text[start : cursor + 1]
        cursor += 1
    raise ValueError('Unterminated QML array or object')


def array(text, name):
    bindings = list(re.finditer(r'\b' + re.escape(name) + r'\s*:', text))
    if not bindings:
        return None
    if len(bindings) != 1:
        raise ValueError('Ambiguous tab declaration: ' + name)
    start = bindings[0].end()
    start += len(text[start:]) - len(text[start:].lstrip())
    if text[start : start + 1] != '[':
        raise ValueError('Tab inventory requires an explicit array: ' + name)
    return balanced(text, start)


def buttons(text, name, prefix):
    literal = array(text, name)
    if literal is None:
        return None
    remaining, result = literal[1:-1].strip(), []
    while remaining:
        component = re.match(r'[\w.]+\s*\{', remaining)
        if component is None:
            raise ValueError('Unrecognized tab component in ' + name)
        body = balanced(remaining, component.end() - 1)
        names = re.findall(r'\bobjectName\s*:\s*"([^"\n]+)"', body)
        if len(names) != 1 or not names[0].startswith(prefix):
            raise ValueError('Each declared tab needs one stable native object name')
        key = names[0].removeprefix(prefix).lower()
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', key):
            raise ValueError('Unrecognized tab identity')
        result.append({'key': key, 'object': names[0]})
        remaining = remaining[component.end() - 1 + len(body) :].strip()
        if remaining:
            if not remaining.startswith(','):
                raise ValueError('Unrecognized tab array separator')
            remaining = remaining[1:].strip()
    if len({r['key'] for r in result}) != len(result):
        raise ValueError('Duplicate native tab identity')
    return result


def page_tabs(qml, component, main, sidebar):
    paths = list((qml / 'Pages').glob('*/' + component + '.qml'))
    if len(paths) != 1:
        raise ValueError('Each mounted page must resolve to one source declaration')
    text = source(paths[0])
    page = component.removesuffix('Page').lower()
    workflow = re.search(r'\bWorkflowPage\s*\{', text) is not None
    if re.search(r'\btabs\s*:', text):
        raise ValueError('A page-local tab bar needs an explicit inventory adapter')
    declared_name = re.findall(r'\bpageName\s*:\s*"([^"\n]+)"', text)
    if workflow and declared_name != [page]:
        raise ValueError('Mounted and native page identities must agree')
    selected = array(text, 'tabKeys')
    own = buttons(text, 'mainTabs', 'mainArea.' + page + '.tab.')
    if selected is not None:
        selected = json.loads(selected)
        if own is not None or not selected or len(set(selected)) != len(selected):
            raise ValueError('A main view needs one unambiguous configured tab set')
        if not set(selected) <= {r['key'] for r in main}:
            raise ValueError('A configured main tab has no native declaration')
        own = [r for r in main if r['key'] in selected]
    if workflow and not own:
        raise ValueError('A workflow page must expose its main-view declarations')
    if not workflow and re.search(r'\b(?:TabBar|\w*TabButton)\s*\{', text):
        raise ValueError('A non-workflow tab bar needs an explicit inventory adapter')
    return page, {'main': own or [], 'sidebar': sidebar if workflow else []}, selected or []


def declared_tabs(root=ROOT):
    """Cover every mounted page and its complete configured tab set, or refuse."""
    qml = root / 'app/qml'
    content = array(source(qml / 'Main.qml'), 'contentArea')
    if content is None:
        raise ValueError('The app must declare its mounted pages')
    types = [
        name
        for name in re.findall(r'\b([\w.]+)\s*\{', content)
        if name not in {'Loader', 'Component'}
    ]
    if not types or len(set(types)) != len(types):
        raise ValueError('Mounted page identities must be nonempty and unique')
    shared = source(qml / 'Components/MainView.qml')
    keys = json.loads(array(shared, 'allKeys'))
    main = buttons(shared, 'tabs', 'mainArea.tab.')
    if keys != [r['key'] for r in main]:
        raise ValueError('Shared main-view keys and native tab objects must agree')
    sidebar = buttons(source(qml / 'Components/WorkflowPage.qml'), 'tabs', 'sideBar.tab.')
    if not sidebar:
        raise ValueError('Workflow sidebar inventory must be nonempty')
    result, used = {}, set()
    for component in types:
        page, areas, selected = page_tabs(qml, component, main, sidebar)
        if page in result or not re.fullmatch(r'[a-z][a-z0-9_]*', page):
            raise ValueError('Mounted types must have distinct canonical page identities')
        used.update(selected)
        result[page] = areas
    if used != set(keys):
        raise ValueError('Every shared tab must belong to a mounted page')
    return result


def tab_targets(inventory):
    """Visit even a tabless page, then each declared main and sidebar tab."""
    result = []
    for page, areas in inventory.items():
        result.append({'name': 'page-' + page, 'page': page, 'area': 'page'})
        for area, tabs in areas.items():
            result.extend(
                {
                    'name': f'tab-{area}-{page}-{tab["key"]}',
                    'page': page,
                    'area': area,
                    **tab,
                }
                for tab in tabs
            )
    if len({target['name'] for target in result}) != len(result):
        raise ValueError('Canonical tab actions must have distinct identities')
    return result


def scenario_steps(root=ROOT):
    contract = json.loads((root / 'tests/fixtures/ui_responsiveness/contract.json').read_text())
    return {
        **contract['scenarios'],
        SCENARIO: [target['name'] for target in tab_targets(declared_tabs(root))],
    }


if __name__ == '__main__':
    print(json.dumps({'pages': declared_tabs(), 'scenarios': scenario_steps()}, indent=2))
