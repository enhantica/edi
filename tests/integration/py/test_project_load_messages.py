"""Declaration supplement for the actual Qt load-failure actor."""

import re
from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import (
    block,
    item,
    javascript,
    object_id,
    property_value,
    spans,
)

ROOT = Path(__file__).resolve().parents[3]


def deferred_row(qml, route):
    recent = (ROOT / 'app/qml/Globals/RecentProjects.qml').read_text()
    state = (ROOT / 'app/qml/Globals/AppState.qml').read_text()
    recent_route = route == 'recent'
    action = 'ApplicationInfo.openProjectRow(' + str(recent_route).lower() + ', true)'
    assert action in qml, 'Every actual row activation must enter its native replacement route'
    program = (
        'let queued=[],calls=[];const textEdit=null;const Qt={callLater:f=>queued.push(f)};'
        'const row={activated(){},available:true,path:"/chosen/entry",'
        'exampleId:"authored_example"};'
        'const WebFiles={available:false};const Session={project:null,projectGeneration:()=>0,'
        'projectDirectoryUrl:path=>"file://"+path,'
        'openProject:path=>calls.push(["project",path]),'
        'openExample:id=>calls.push(["example",id])};'
        + block(state, 'function afterChanges(')
        + 'const AppState={afterChanges};const RecentProjects={open:function(path)'
        + block(recent, 'function open(').split(')', 1)[1]
        + '};'
        + action
        + ';const before=calls.length;'
        'queued.splice(0).forEach(f=>f());console.log(JSON.stringify([before,calls]));'
    )
    assert javascript(program) == [
        0,
        [
            [
                'project' if recent_route else 'example',
                'file:///chosen/entry' if recent_route else 'authored_example',
            ]
        ],
    ], 'Recent/example activation defers its actual selected row through the replacement lifecycle'


def deferred_chooser(main, chooser_id, selected, purpose):
    accepted = property_value(object_id(main, chooser_id), 'onAccepted')
    assert accepted, 'The actual window chooser must own its acceptance handler'
    choices = {'selectedFolder': 'file:///chosen/project', 'selectedFile': 'file:///chosen/file'}
    expression = (
        '(()=>{let queued=[], loaded=[], remembered=[];'
        'const selectedFolder="file:///chosen/project", selectedFile="file:///chosen/file";'
        'const Qt={callLater:(fn, path)=>queued.push(()=>fn(path))};'
        'const Session={openProject:path=>loaded.push(path)};'
        'const DialogFolders={remember:(purpose,path)=>remembered.push([purpose,path])};'
        + accepted
        + 'const before=loaded.slice();queued.splice(0).forEach(f=>f());'
        'return [before,loaded,remembered];})()'
    )
    return expression, [[], [choices[selected]], [[purpose, choices[selected]]]]


def check_chooser_and_refusal_observations(main, handler, choosers):
    observer = block(main, 'function ' + handler + '(')
    refusal_probe = (
        '(()=>{let shown=[];const qsTr=s=>s;const refusal={message:"",title:"",'
        'file:"",open(){shown.push([this.message,this.file,this.title])}};'
        + observer
        + ';'
        + handler
        + '("same refusal","file:///unreadable.edi");'
        + handler
        + '("same refusal");return shown;})()'
    )
    probes = [expression for expression, _ in choosers] + [refusal_probe]
    observed = javascript('console.log(JSON.stringify([' + ','.join(probes) + ']));')
    assert observed[:-1] == [expected for _, expected in choosers], (
        'The window chooser must remember and defer its actual selected path to the project loader'
    )
    assert observed[-1] == [
        ['same refusal', 'file:///unreadable.edi', 'The project was not opened'],
        ['same refusal', '', 'The project was not opened'],
    ], (
        'Each actual per-attempt event must open the message dialog, including identical '
        'refusals, and replace the unreadable file with the current attempt'
    )


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
    main = (ROOT / 'app/qml/Main.qml').read_text()
    choosers = []
    if route == 'open':
        choosers = [deferred_chooser(main, 'openFolderDialog', 'selectedFolder', 'openProject')]
    elif route == 'zip':
        choosers = [
            deferred_chooser(main, 'openZipDialog', 'selectedFile', 'openProject'),
            deferred_chooser(main, 'importDialog', 'selectedFile', 'importProject'),
        ]
    else:
        deferred_row((ROOT / 'app/qml/Pages/Project' / path).read_text(), route)
    handlers = []
    components = spans(main)
    for target in re.finditer(r'^\s*target:\s*Session\s*$', main, re.MULTILINE):
        start, end = min(
            ((a, b) for a, b in components if a < target.start() < b),
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
        native = (ROOT / 'app/src/app_info.cpp').read_text()
        recent_native = block(native, 'void ApplicationInfo::recentOpen(')
        assert all(
            fragment in recent_native
            for fragment in (
                '"openStoredProject"',
                '"webKey"',
                '"kept:"',
            )
        ), 'Browser recent rows must retain their actual stored-project receiver'
        assert re.search(r'"webKey", \{path\}', recent_native) and re.search(
            r'return QJSValueList\{key, kept\}', recent_native
        ), 'Browser recent completion must pass both its actual selected key and recovery choice'
        wrappers.append(block(session, 'void Session::openStoredProject('))
    assert all(
        'emit ' in wrapper
        and any(
            match.group(1)[2].lower() + match.group(1)[3:] + '(' in wrapper for match in handlers
        )
        for wrapper in wrappers
    ), 'Every live desktop and browser loader must publish repeated per-attempt refusals'
    handler = next(match.group(1) for match in handlers if match.group(1) == 'onLoadFailed')
    check_chooser_and_refusal_observations(main, handler, choosers)
    assert re.search(r'\bErrorDialog\s*\{\s*id:\s*refusal\b', main), (
        'ADR-0062: load refusals must use the shared reportable error dialog'
    )
    assert 'objectName: "refusal.dialog"' in item(main, 'refusal.dialog'), (
        'The actual load refusal must retain its observable dialog identity'
    )
    dialog = (ROOT / 'app/qml/Components/ErrorDialog.qml').read_text()
    assert 'text: dialog.message' in dialog, (
        'The actual failure dialog must render the message published by its native event owner'
    )
    assert property_value(dialog, 'standardButtons').strip(), (
        'The failure dialog must let the user acknowledge the load refusal'
    )
