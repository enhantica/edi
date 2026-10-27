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
    assert 'Session.' + entry + '(' in qml, (
        'The route census must follow the actual production loader call'
    )
    if route == 'zip':
        assert 'function onProjectOpened(' in qml and 'group.webRequest' in qml, (
            'The zip-completion path must retain request identity '
            'before loading the extracted project'
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
    wrapper = block(session, 'bool Session::' + entry + '(')
    assert 'emit ' in wrapper and any(
        match.group(1)[2].lower() + match.group(1)[3:] + '(' in wrapper for match in handlers
    ), 'Each public loader must publish its refusal even when the error text did not change'
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
