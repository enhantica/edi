"""Owner-directed reset navigation and the scan-rule required toggle."""

import re

import pytest

from tests.integration.py.test_scan_app_contract import (
    block,
    item,
    javascript,
    property_value,
    source,
)
from tests.integration.py.test_status_columns import children, table_cells


def observe(*expressions):
    return javascript('console.log(JSON.stringify([' + ','.join(expressions) + ']));')


def reset_vector(body):
    return (
        '(()=>{let closed=0,reached=4;const Session={hasProject:true,'
        'closeProject:()=>{closed++;Session.hasProject=false;}};'
        'const AppState={Page:{Home:0,Project:1}};const EaGlobals={Vars:{appBarCurrentIndex:4}};'
        '(' + body + ')();return [Session.hasProject,'
        'EaGlobals.Vars.appBarCurrentIndex,reached,closed];})()'
    )


def reset_handler_vector(handler, guard, *, pending_text=False, settle_text=True):
    return (
        '(()=>{const observations=[];'
        'for(const project of [null,{modified:false},{modified:true}]){'
        'let resets=0;const queued=[],questions=[];'
        'const Session={project,projectGeneration:()=>0};'
        'const Qt={callLater:action=>queued.push(action)};const settlements=[];'
        'let textEdit='
        + ('{settleEdit:action=>settlements.push(action)};' if pending_text else 'null;')
        + 'const AppState={reset:()=>resets++};'
        'const changesQuestion=action=>questions.push(action);'
        + guard
        + ';AppState.afterChanges=afterChanges;(function(){'
        + handler
        + '})();const before=[resets,queued.length,questions.length];'
        + ('for(const action of settlements){textEdit=null;action();}' if settle_text else '')
        + 'for(const action of questions)Qt.callLater(action);'
        'for(const action of queued)action();'
        'observations.push([...before,resets'
        + (',settlements.length' if pending_text else '')
        + ']);}'
        'return observations;})()'
    )


def test_reset_closes_the_project_and_returns_home():
    main = source('qml/Main.qml')
    handler = property_value(item(main, 'appBar.button.reset'), 'onClicked')
    guard = block(source('qml/Globals/AppState.qml'), 'function afterChanges(')
    body = block(source('qml/Globals/AppState.qml'), 'function reset(')
    damaged = (
        'AppState.reset()',
        'AppState.afterChanges(() => {})',
        'AppState.afterChanges(() => {AppState.reset();AppState.reset();})',
    )
    actual, pending, unsettled, reset, *controls = observe(
        reset_handler_vector(handler, guard),
        reset_handler_vector(handler, guard, pending_text=True),
        reset_handler_vector(handler, guard, pending_text=True, settle_text=False),
        reset_vector(body),
        *(reset_handler_vector(control, guard) for control in damaged),
    )
    expected = [[0, 1, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]
    assert actual == expected, (
        'Toolbar reset must wait for the shared unsaved-changes guard, '
        'then invoke the shared reset once after authorization or the queued turn'
    )
    assert all(control != expected for control in controls), (
        'The reset observer must reject guard bypass, a lost reset and duplicate resets'
    )
    assert pending == [[0, 0, 0, 1, 1]] * 3, (
        'Reset waits for each pending Text edit to settle before the project-change guard runs'
    )
    assert unsettled == [[0, 0, 0, 0, 1]] * 3, (
        'An unsettled Text edit prevents every queued or immediate Reset'
    )
    assert reset == [False, 0, 0, 1], (
        'Reset must close the current project once and restore Home as both the current '
        'and furthest reached page'
    )


@pytest.mark.parametrize('damage', ['project-page', 'open-project'])
def test_reset_observer_detects_wrong_destination_and_unclosed_project(damage):
    good = (
        'function reset(){Session.closeProject();reached=AppState.Page.Home;'
        'EaGlobals.Vars.appBarCurrentIndex=AppState.Page.Home;}'
    )
    damaged = (
        good.replace('AppState.Page.Home', 'AppState.Page.Project')
        if damage == 'project-page'
        else good.replace('Session.closeProject();', '')
    )
    clean_observation, damaged_observation = observe(reset_vector(good), reset_vector(damaged))
    assert clean_observation == [False, 0, 0, 1], (
        'The reset control must reach Home with no open project and one close'
    )
    assert damaged_observation != [False, 0, 0, 1], (
        'The reset observer must detect landing on Project or retaining an open project'
    )


def test_scan_rule_required_is_an_unlabelled_editable_icon_toggle():
    qml = source('qml/Pages/Analysis/SequentialExtractGroup.qml')
    header = block(qml, 'header:')
    toggles = [
        (index, body)
        for index, (kind, body) in enumerate(table_cells(qml))
        if kind in {'EaComponents.TableViewButton', 'EaComponents.ListViewButton', 'IconCell'}
        and 'required' in body
    ]
    assert len(toggles) == 1, 'Each scan rule must have exactly one real required icon button'
    index, button = toggles[0]
    headings = children(header, header.index('{') + 1, len(header) - 1)
    assert index < len(headings) and not re.search(r'\b(?:text|uid):', headings[index][1]), (
        'The header cell aligned with the required toggle is unlabelled'
    )
    icon = property_value(button, 'fontIcon')
    tooltip = property_value(button, 'ToolTip.text')
    assert 'text:' not in button.replace('ToolTip.text:', ''), (
        'The required state must use icons without visible yes/no text'
    )
    assert re.search(r'fail|match', tooltip, re.IGNORECASE), (
        'The required toggle tooltip must explain that a file without a match fails'
    )
    handler = property_value(button, 'onClicked')
    target = re.search(r'(\w+)\.(\w+)\.setRequired', handler)
    assert target, 'The required button reaches the editable rule model'
    root, model = target.groups()
    observed = javascript(
        'let calls=[];'
        f'const {root}={{{model}:{{setRequired:(...args)=>calls.push(args)}}}};'
        f'const row={{index:3,model:{{required:false}}}};'
        f'const before=({icon});(function(){{{handler}}})();'
        f'row.model.required=true;const after=({icon});'
        'console.log(JSON.stringify([before,after,calls]));'
    )
    assert observed == ['toggle-off', 'toggle-on', [[3, True]]], (
        'The required icon shows both real rule states and clicking writes its own rule'
    )
