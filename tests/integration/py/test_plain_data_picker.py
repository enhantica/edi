"""Execute shipped data-picker handlers and their actual availability bindings."""

from __future__ import annotations

import json
import re

import pytest

from tests.integration.py.test_scan_app_contract import (
    block,
    item,
    javascript,
    property_value,
    require_availability,
    source,
    spans,
)

PATH = 'qml/Pages/Experiment/ExperimentsGroup.qml'


def by_id(text, name):
    match = re.search(r'\bid:\s*' + re.escape(name) + r'\b', text)
    assert match, 'Load data wiring: the actual chooser must exist in its owning component'
    begin, end = min(
        ((a, b) for a, b in spans(text) if a < match.start() < b),
        key=lambda pair: pair[1] - pair[0],
    )
    return text[begin:end]


def require_picker(text, browser, scenario='accepted'):
    control = item(text, 'experiments.loadData.${row.index}')
    chooser = block(text, 'function chooseData(')
    received = block(text, 'function onFilesOpened(')
    failed = block(text, 'function onFailed(')
    cancelled = block(text, 'function onCancelled(')
    dialog = by_id(text, 'dataDialog')
    accepted = property_value(dialog, 'onAccepted')
    filters = property_value(dialog, 'nameFilters')
    data_filter = property_value(text, 'dataFilter')
    program = """
let calls=[];
const original={currentExperimentIndex:4,
    loadData:(index,file)=>calls.push(['loaded','original',index,file]),
    loadExperiments:files=>calls.push(['wrong-action',files])};
const foreign={currentExperimentIndex:7,
    loadData:(index,file)=>calls.push(['loaded','foreign',index,file])};
const group={project:original,webRequest:0,webRequestProject:null,webDataIndex:-1};
const row={index:2,experiment:{canLoadData:true,calculationOnly:true}};
const qsTr=text=>text;
const WebFiles={available:BROWSER,
    openFiles:(filter,multiple)=>{calls.push(['web',filter,multiple]);return 41;}};
const dataDialog={experimentIndex:-1,selectedFile:'chosen.dat',
    open:()=>calls.push(['desktop',dataDialog.experimentIndex])};
group.dataFilter=DATA_FILTER;
group.chooseData=function(index) CHOOSE;
function click() { ACTION }
function accept() { ACCEPTED }
RECEIVED
FAILED
CANCELLED
let desktopFilters=FILTERS;
click();
original.currentExperimentIndex=8;
SCENARIO
console.log(JSON.stringify({calls,desktopFilters}));
"""
    route = (
        'onFilesOpened(41,["chosen.dat"]); onFilesOpened(41,["duplicate.dat"]);'
        if browser
        else 'accept();'
    )
    prefix = {
        'accepted': '',
        'foreign-request': 'onFilesOpened(42,["foreign.dat"]);',
        'foreign-project': 'group.project=foreign;',
        'closed-project': 'group.project=null;',
        'cancelled': 'onCancelled(41);',
        'failed': 'onFailed(41);',
        'foreign-cancel': 'onCancelled(42);',
        'foreign-failure': 'onFailed(42);',
    }[scenario]
    substitutions = {
        'BROWSER': json.dumps(browser),
        'DATA_FILTER': data_filter,
        'CHOOSE': chooser[chooser.index('{') :],
        'ACTION': property_value(control, 'onClicked'),
        'ACCEPTED': accepted,
        'RECEIVED': received,
        'FAILED': failed,
        'CANCELLED': cancelled,
        'FILTERS': filters,
        'SCENARIO': prefix + 'try {' + route + '} catch(error) {calls.push(["error"]);}',
    }
    for token, value in substitutions.items():
        program = program.replace(token, value)
    observed = javascript(program)
    expected = [['web', '.xye,.xy,.dat,.txt,.csv', False]] if browser else [['desktop', 2]]
    if scenario not in {'foreign-project', 'closed-project', 'cancelled', 'failed'}:
        expected.append(['loaded', 'original', 2, 'chosen.dat'])
    assert observed['calls'] == expected, (
        'Load data routing: the real click opens its chooser, targets its initiating row '
        'and project, and rejects stale, foreign, failed, cancelled or duplicate results'
    )
    assert (
        len(observed['desktopFilters']) == 2
        and all(
            extension in observed['desktopFilters'][0]
            for extension in ['*.xye', '*.xy', '*.dat', '*.txt', '*.csv']
        )
        and '(*)' in observed['desktopFilters'][1]
    ), 'Load data filters: the actual data dialog admits every declared extension and all files'


def test_load_data_availability_uses_ownership_after_first_load():
    require_availability(source(PATH))


@pytest.mark.parametrize(
    ('browser', 'scenario'),
    [(False, case) for case in ['accepted', 'foreign-project', 'closed-project']]
    + [
        (True, case)
        for case in [
            'accepted',
            'foreign-request',
            'foreign-project',
            'closed-project',
            'cancelled',
            'failed',
            'foreign-cancel',
            'foreign-failure',
        ]
    ],
)
def test_load_data_click_and_result_reach_the_initiating_row(browser, scenario):
    require_picker(source(PATH), browser, scenario)


@pytest.mark.parametrize('damage', ['always-disabled', 'always-enabled', 'simulation-only'])
def test_availability_observer_rejects_retired_or_overbroad_rules(damage):
    text = source(PATH)
    require_availability(text)
    control = item(text, 'experiments.loadData.${row.index}')
    property_name = 'visible' if damage == 'simulation-only' else 'enabled'
    replacement = (
        'row.experiment !== null && row.experiment.calculationOnly'
        if damage == 'simulation-only'
        else 'false'
        if damage == 'always-disabled'
        else 'true'
    )
    original = property_value(control, property_name)
    changed = text.replace(control, control.replace(original, replacement, 1), 1)
    assert changed != text, 'Load data availability escape: change the effective property'
    with pytest.raises(AssertionError, match='Load data availability'):
        require_availability(changed)


@pytest.mark.parametrize(
    ('old', 'new', 'browser', 'scenario'),
    [
        ('onClicked: group.chooseData(row.index)', 'onClicked: {}', True, 'accepted'),
        ('group.chooseData(row.index)', 'group.chooseData(0)', False, 'accepted'),
        ('dataDialog.open();', 'return;', False, 'accepted'),
        (
            'group.project.loadData(dataDialog.experimentIndex, dataDialog.selectedFile)',
            '{ return; }',
            False,
            'accepted',
        ),
        (
            'group.project.loadData(dataDialog.experimentIndex, dataDialog.selectedFile)',
            'group.project.loadData(0, dataDialog.selectedFile)',
            False,
            'accepted',
        ),
        (
            'group.project.loadData(index, files[0]);',
            'return; group.project.loadData(index, files[0]);',
            True,
            'accepted',
        ),
        (
            'group.project.loadData(index, files[0]);',
            'group.project.loadData(0, files[0]);',
            True,
            'accepted',
        ),
        ('request !== group.webRequest', 'false', True, 'foreign-request'),
        ('project-identity', '', True, 'foreign-project'),
        ('group.dataFilter, false', 'group.dataFilter, true', True, 'accepted'),
    ],
    ids=[
        'disconnected-click',
        'wrong-chosen-row',
        'disconnected-desktop-open',
        'disconnected-desktop-accept',
        'wrong-desktop-row',
        'early-browser-return',
        'wrong-browser-row',
        'foreign-request',
        'foreign-project',
        'wrong-multiplicity',
    ],
)
def test_picker_observer_rejects_disconnected_and_wrong_target_handlers(
    old, new, browser, scenario
):
    text = source(PATH)
    require_picker(text, browser, 'accepted')
    if old == 'project-identity':
        callback = block(text, 'function onFilesOpened(')
        match = re.search(r'group\.project\s*(===|!==)\s*group\.webRequestProject', callback)
        assert match, 'Load data routing escape: the callback owns its project identity guard'
        changed_callback = callback.replace(match[0], 'true' if match[1] == '===' else 'false', 1)
        changed = text.replace(callback, changed_callback, 1)
    else:
        changed = text.replace(old, new, 1)
    assert changed != text, 'Load data routing escape: mutate the actual shipped handler'
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        require_picker(changed, browser, scenario)
