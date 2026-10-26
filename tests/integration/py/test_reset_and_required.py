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
from tests.integration.py.test_status_columns import table_cells


def reset_observation(body):
    return javascript(
        'let closed=0,reached=4;const Session={hasProject:true,'
        'closeProject:()=>{closed++;Session.hasProject=false;}};'
        'const AppState={Page:{Home:0,Project:1}};const EaGlobals={Vars:{appBarCurrentIndex:4}};'
        '(' + body + ')();console.log(JSON.stringify([Session.hasProject,'
        'EaGlobals.Vars.appBarCurrentIndex,reached,closed]));'
    )


def reset_handler_observation(handler, guard):
    return javascript(
        'const observations=[];for(const project of [null,{modified:false},{modified:true}]){'
        'let resets=0;const queued=[],questions=[];const Session={project};'
        'const Qt={callLater:action=>queued.push(action)};'
        'const AppState={reset:()=>resets++};'
        'const changesQuestion=action=>questions.push(action);'
        + guard
        + ';AppState.afterChanges=afterChanges;(function(){'
        + handler
        + '})();const before=[resets,queued.length,questions.length];'
        'for(const action of questions)Qt.callLater(action);'
        'for(const action of queued)action();'
        'observations.push([...before,resets]);}'
        'console.log(JSON.stringify(observations));'
    )


def test_reset_closes_the_project_and_lands_on_project():
    main = source('qml/Main.qml')
    handler = property_value(item(main, 'appBar.button.reset'), 'onClicked')
    guard = block(source('qml/Globals/AppState.qml'), 'function afterChanges(')
    expected = [[0, 1, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]
    assert reset_handler_observation(handler, guard) == expected, (
        'Toolbar reset must wait for the shared unsaved-changes guard, '
        'then invoke the shared reset once after authorization or the queued turn'
    )
    for damaged in (
        'AppState.reset()',
        'AppState.afterChanges(() => {})',
        'AppState.afterChanges(() => {AppState.reset();AppState.reset();})',
    ):
        assert reset_handler_observation(damaged, guard) != expected, (
            'The reset observer must reject guard bypass, a lost reset and duplicate resets'
        )
    body = block(source('qml/Globals/AppState.qml'), 'function reset(')
    assert reset_observation(body) == [False, 1, 1, 1], (
        'Reset must close the current project once and land on the reached Project page'
    )


@pytest.mark.parametrize('damage', ['home', 'open-project'])
def test_reset_observer_detects_wrong_destination_and_unclosed_project(damage):
    good = (
        'function reset(){Session.closeProject();reached=AppState.Page.Project;'
        'EaGlobals.Vars.appBarCurrentIndex=AppState.Page.Project;}'
    )
    assert reset_observation(good) == [False, 1, 1, 1], (
        'The closed-form reset control must reach the declared Project state'
    )
    damaged = (
        good.replace('AppState.Page.Project', 'AppState.Page.Home')
        if damage == 'home'
        else good.replace('Session.closeProject();', '')
    )
    assert reset_observation(damaged) != [False, 1, 1, 1], (
        'Reset gates must detect both returning Home and retaining an open project'
    )


def test_scan_rule_required_is_an_unlabelled_editable_icon_toggle():
    qml = source('qml/Pages/Analysis/SequentialExtractGroup.qml')
    header = block(qml, 'header:')
    assert 'qsTr("required")' not in header, (
        'The required toggle column must retain an empty header'
    )
    cells = [
        body
        for kind, body in table_cells(qml)
        if kind in {'EaComponents.TableViewButton', 'IconCell'}
    ]
    toggles = [body for body in cells if 'required' in body]
    assert len(toggles) == 1, 'Each scan rule must have exactly one real required icon button'
    button = toggles[0]
    editable = 'onClicked:' in button
    icon = property_value(button, 'fontIcon' if editable else 'icon')
    tooltip = property_value(button, 'ToolTip.text' if editable else 'toolTip')
    assert 'text:' not in button.replace('ToolTip.text:', ''), (
        'The required state must use icons without visible yes/no text'
    )
    assert re.search(r'fail|match', tooltip, re.IGNORECASE), (
        'The required toggle tooltip must explain that a file without a match fails'
    )
    if editable:
        handler = property_value(button, 'onClicked')
        target = re.search(r'(\w+)\.(\w+)\.setRequired', handler)
        assert target, 'An editable required button must reach its rule model write boundary'
        root, model = target.groups()
        context = 'const ' + root + '={' + model + ':{setRequired:(...args)=>calls.push(args)}};'
        invoke = '(function(){' + handler + '})();'
    else:
        # Scan declarations currently have no GUI write route. A read-only icon
        # is permitted only alongside the other read-only declaration cells.
        assert 'onCommitted:' not in qml and 'setRequired' not in source(
            'src/analysis_view_model.hpp'
        ), 'A non-clickable required icon is allowed only while scan rules are read-only'
        context, invoke = '', ''
    observed = javascript(
        'const qsTr=x=>x;let calls=[];'
        + context
        + 'const row={index:3,model:{required:false}};const before=('
        + icon
        + ');'
        + invoke
        + 'row.model.required=true;const after=('
        + icon
        + ');'
        'console.log(JSON.stringify([before,after,calls]));'
    )
    assert observed == ['toggle-off', 'toggle-on', [[3, True]] if editable else []], (
        'The required icon must show both real rule states '
        'and any editable action writes its own rule'
    )
