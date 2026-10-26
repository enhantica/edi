"""Declaration supplement for the actual Qt load-failure actor."""

import re
from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import block, property_value, spans

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('route', 'path', 'entry'),
    [
        ('open', 'GetStartedGroup.qml', 'openProject'),
        ('recent', 'RecentProjectsGroup.qml', 'openProject'),
        ('example', 'ExamplesGroup.qml', 'openExample'),
        ('zip', 'GetStartedGroup.qml', 'openProject'),
    ],
)
def test_every_project_load_route_has_a_per_attempt_visible_failure_channel(route, path, entry):
    qml = (ROOT / 'app/qml/Pages/Project' / path).read_text()
    if route in {'open', 'zip'}:
        selected = 'selectedFolder' if route == 'open' else 'selectedFile'
        assert f'Qt.callLater(Session.openProject, {selected})' in qml, (
            'The selected folder or archive must reach the real loader on the next event-loop turn'
        )
    elif route == 'recent':
        assert 'AppState.afterChanges(() => RecentProjects.open(row.path))' in qml, (
            'Recent activation must defer the selected row through the actual '
            'replacement lifecycle'
        )
        recent = (ROOT / 'app/qml/Globals/RecentProjects.qml').read_text()
        assert 'Session.openProject(Session.projectDirectoryUrl(path))' in recent, (
            'The recent-project adapter must pass its selected disk path to the actual loader'
        )
        state = (ROOT / 'app/qml/Globals/AppState.qml').read_text()
        assert 'Qt.callLater(action)' in block(state, 'function afterChanges('), (
            'The recent-project replacement lifecycle must queue its action after'
            ' the current handler'
        )
    else:
        assert 'Session.' + entry + '(' in qml, (
            'The route census must follow the actual production loader call'
        )
    main = (ROOT / 'app/qml/Main.qml').read_text()
    handlers = []
    for target in re.finditer(r'^\s*target:\s*Session\s*$', main, re.MULTILINE):
        start, end = min(
            ((a, b) for a, b in spans(main) if a < target.start() < b),
            key=lambda span: span[1] - span[0],
        )
        component = main[start:end]
        handlers.extend(re.finditer(r'function\s+(on\w*(?:Failed|Refused))\s*\(', component))
    assert handlers, (
        'Every project-load route must show failure through a Session per-attempt channel, '
        'including repeated identical errors'
    )
    session = (ROOT / 'app/src/session.cpp').read_text()
    wrappers = [block(session, 'bool Session::' + entry + '(')]
    if route == 'zip':
        assert 'pickOpen(kind, root, webOpenAnswer(root))' in block(
            session, 'void Session::openWebProject('
        ), 'Browser ZIP refusal must come from the callback used by the live Open route'
        wrappers.append(block(session, 'WebStorage::Answer Session::webOpenAnswer('))
    if route == 'recent':
        assert 'Session.openStoredProject(webKey(path), path.startsWith("kept:"))' in recent, (
            'Browser recent rows must retain their actual stored-project receiver'
        )
        wrappers.append(block(session, 'void Session::openStoredProject('))
    assert all(
        'emit ' in wrapper
        and any(
            match.group(1)[2].lower() + match.group(1)[3:] + '(' in wrapper for match in handlers
        )
        for wrapper in wrappers
    ), 'Every live desktop and browser loader must publish repeated per-attempt refusals'
    observer = block(main, 'function ' + handlers[0].group(1) + '(')
    opened = re.search(r'(\w+)\.open\(\)', observer)
    assert opened is not None, 'The per-load failure handler must open a visible message dialog'
    location = main.index('id: ' + opened.group(1))
    start, end = min(
        ((a, b) for a, b in spans(main) if a < location < b),
        key=lambda span: span[1] - span[0],
    )
    dialog = main[start:end]
    assert '.message = ' in observer and opened.group(1) + '.message' in dialog, (
        'The load dialog must display the message carried by the actual failure event'
    )
    assert property_value(dialog, 'standardButtons').strip(), (
        'The failure dialog must let the user acknowledge the load refusal'
    )
