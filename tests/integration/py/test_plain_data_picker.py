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


def require_picker(text, browser, scenario='accepted', *, sample_form='powder'):
    selected = block(text, 'function chooseDataForSelected(')
    dialog = by_id(text, 'dataDialog')
    new_target = scenario in {'create-target', 'empty-cancelled', 'empty-failed'}
    new_picker = 'property int newDataRequest:' in text
    new_scope, _, existing_scope = text.partition('    readonly property string dataFilter:')
    new_scope = new_scope.partition('property int newDataRequest:')[2]
    new_dialog = by_id(text, 'newDataDialog') if new_picker else None
    program = """
let calls=[];
const ExperimentViewModel={SingleCrystal:'single crystal'};
const initiator={id:'initiator',canLoadData:true,calculationOnly:true,sampleForm:SAMPLE_FORM};
const other={id:'other',canLoadData:true,calculationOnly:true};
const original={currentExperimentIndex:4,currentExperiment:initiator,
    createExperiment:()=>{
        calls.push(['created']);
        original.currentExperiment=initiator;
        return true;
    },
    loadDataInto:(experiment,file)=>calls.push(['loaded','original',experiment.id,file]),
    loadDataIntoNewExperiment:file=>calls.push(['loaded-new','original',file]),
    loadExperiments:files=>calls.push(['wrong-action',files])};
const foreign={currentExperimentIndex:7,
    loadDataInto:(experiment,file)=>calls.push(['loaded','foreign',experiment.id,file]),
    loadDataIntoNewExperiment:file=>calls.push(['loaded-new','foreign',file])};
const group={project:original,webRequest:0,webRequestProject:null,webDataExperiment:null,
    newDataRequest:0,newDataProject:null,pickerLife:{alive:true}};
const Session={get project(){return group.project}};
const qsTr=text=>text;
const WebFiles={available:BROWSER,
    openFiles:(filter,multiple)=>{calls.push(['web',filter,multiple]);return 41;}};
const dataDialog={intent:null,experiment:null,project:null,visible:false,selectedFile:'chosen.dat',
    open:()=>calls.push(['desktop',dataDialog.experiment.id])};
const newDataDialog={project:null, selectedFile:'chosen.dat',
    open:()=>calls.push(['desktop-new'])};
group.dataFilter=DATA_FILTER;
group.chooseData=CHOOSE;
group.chooseDataForSelected=function() { with(group) SELECTED }
function click() { ACTION }
function accept() { ACCEPTED }
function acceptNew(selectedFile) { ACCEPTED_NEW }
RECEIVED_NEW
FAILED_NEW
CANCELLED_NEW
RECEIVED
FAILED
CANCELLED
function deliver(request,files) { onFilesOpened(request,files); onNewFilesOpened(request,files); }
function fail(request) { onFailed(request); onNewFailed(request); }
function cancel(request) { onCancelled(request); onNewCancelled(request); }
BEFORE
click();
let desktopFilters=FILTERS;
SCENARIO
console.log(JSON.stringify({calls,desktopFilters}));
"""
    route = (
        'deliver(41,["chosen.dat"]); deliver(41,["duplicate.dat"]);'
        if browser
        else 'acceptNew("chosen.dat"); acceptNew("duplicate.dat");'
        if new_target and new_picker
        else 'accept.call(dataDialog); accept.call(dataDialog);'
    )
    prefix = {
        'accepted': '',
        'foreign-request': 'deliver(42,["foreign.dat"]);',
        'foreign-project': 'group.project=foreign;',
        'closed-project': 'group.project=null;',
        'cancelled': 'cancel(41);',
        'failed': 'fail(41);',
        'foreign-cancel': 'cancel(42);',
        'foreign-failure': 'fail(42);',
        'reindexed': 'original.currentExperimentIndex=9;',
        'retargeted-row': 'original.currentExperiment=other;',
        'create-target': '',
        'empty-cancelled': 'cancel(41);',
        'empty-failed': 'fail(41);',
    }[scenario]

    def new_handler(name, alias):
        if 'function ' + name + '(' not in new_scope:
            return 'function ' + alias + '() {}'
        return block(new_scope, 'function ' + name + '(').replace(name, alias, 1)

    substitutions = {
        'BROWSER': json.dumps(browser),
        'SAMPLE_FORM': json.dumps(sample_form),
        'DATA_FILTER': property_value(text, 'dataFilter'),
        'CHOOSE': block(text, 'function chooseData('),
        'SELECTED': selected[selected.index('{') :],
        'BEFORE': 'original.currentExperiment=null;' if new_target else '',
        'ACTION': property_value(item(text, 'experiments.load.dataFile'), 'onTriggered'),
        'ACCEPTED_NEW': property_value(new_dialog, 'onAccepted') if new_dialog else '',
        'ACCEPTED': property_value(dialog, 'onAccepted'),
        'RECEIVED_NEW': new_handler('onFilesOpened', 'onNewFilesOpened'),
        'FAILED_NEW': new_handler('onFailed', 'onNewFailed'),
        'CANCELLED_NEW': new_handler('onCancelled', 'onNewCancelled'),
        'RECEIVED': block(existing_scope, 'function onFilesOpened('),
        'FAILED': block(existing_scope, 'function onFailed('),
        'CANCELLED': block(existing_scope, 'function onCancelled('),
        'FILTERS': property_value(dialog, 'nameFilters'),
        'SCENARIO': prefix + 'try {' + route + '} catch(error) {calls.push(["error"]);}',
    }
    for token, value in substitutions.items():
        program = program.replace(token, value)
    observed = javascript(program)
    if new_target:
        assert ['created'] not in observed['calls'], (
            'Opening the empty-target chooser must not create the experiment before its answer'
        )
    if browser:
        calls = observed['calls']
        assert calls and calls[0][0] == 'web', (
            'The real browser click must open its file chooser before routing a result'
        )
        assert (
            {'.xye', '.xy', '.dat', '.txt', '.csv', '.int'}
            | ({'.hkl'} if sample_form == 'single crystal' else set())
        ).issubset(set(calls[0][1].split(','))), (
            'The browser picker must admit every supported reflection extension, including hkl'
        )
        expected = [['web', calls[0][1], False]]
    else:
        expected = [['desktop-new']] if new_target else [['desktop', 'initiator']]
    if scenario not in {
        'foreign-project',
        'closed-project',
        'cancelled',
        'failed',
        'empty-cancelled',
        'empty-failed',
    }:
        expected.append(
            ['loaded-new', 'original', 'chosen.dat']
            if new_target
            else ['loaded', 'original', 'initiator', 'chosen.dat']
        )
    assert observed['calls'] == expected, (
        'Load data routing: the real click opens its chooser, targets its initiating row '
        'and project through the retained experiment object after row changes; '
        'foreign, failed, cancelled and duplicate results are refused'
    )
    assert (
        len(observed['desktopFilters']) == 2
        and all(
            extension in observed['desktopFilters'][0]
            for extension in (
                ['*.int', '*.hkl', '*.dat', '*.txt']
                if sample_form == 'single crystal' and not browser
                else ['*.xye', '*.xy', '*.dat', '*.txt', '*.csv']
            )
        )
        and '(*)' in observed['desktopFilters'][1]
    ), 'Load data filters: the actual data dialog admits every declared extension and all files'


def test_load_data_availability_uses_ownership_after_first_load():
    require_availability(source(PATH))


@pytest.mark.parametrize(
    ('browser', 'scenario'),
    [
        (False, case)
        for case in [
            'accepted',
            'create-target',
            'foreign-project',
            'closed-project',
            'reindexed',
            'retargeted-row',
        ]
    ]
    + [
        (True, case)
        for case in [
            'accepted',
            'create-target',
            'empty-cancelled',
            'empty-failed',
            'foreign-request',
            'foreign-project',
            'closed-project',
            'cancelled',
            'failed',
            'foreign-cancel',
            'foreign-failure',
            'reindexed',
            'retargeted-row',
        ]
    ],
)
def test_load_data_click_and_result_reach_the_initiating_row(browser, scenario):
    require_picker(source(PATH), browser, scenario)


@pytest.mark.parametrize('damage', ['always-disabled', 'always-enabled', 'simulation-only'])
def test_availability_observer_rejects_retired_or_overbroad_rules(damage):
    text = source(PATH)
    require_availability(text)
    control = item(text, 'experiments.load.dataFile')
    property_name = 'enabled'
    replacement = (
        'loadMenu.selected !== null && loadMenu.selected.calculationOnly'
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


@pytest.fixture(scope='module')
def picker_control():
    text = source(PATH)
    for browser in (False, True):
        require_picker(text, browser, 'accepted')
    return text


@pytest.mark.parametrize(
    ('old', 'new', 'browser', 'scenario'),
    [
        ('onTriggered: group.chooseDataForSelected()', 'onTriggered: {}', True, 'accepted'),
        ('chooseData(project.currentExperiment)', 'chooseData(other)', False, 'accepted'),
        ('ApplicationInfo.chooseExperimentData(experiment);', 'return;', False, 'accepted'),
        (
            'ApplicationInfo.acceptExperimentDataFile()',
            '{ return; }',
            False,
            'accepted',
        ),
        (
            'ApplicationInfo.acceptExperimentDataFile()',
            'group.project.loadDataInto(other, dataDialog.selectedFile)',
            False,
            'accepted',
        ),
        (
            'ApplicationInfo.formFilesOpened(request, files, true);',
            'return;',
            True,
            'accepted',
        ),
        (
            'ApplicationInfo.formFilesOpened(request, files, true);',
            'group.project.loadDataInto(other, files[0]);',
            True,
            'accepted',
        ),
        (
            'ApplicationInfo.formFilesOpened(request, files, true);',
            'group.project.loadDataInto(group.webDataExperiment, files[0]);',
            True,
            'foreign-request',
        ),
        ('project-identity', '', True, 'foreign-project'),
        (
            'ApplicationInfo.chooseExperimentData(experiment);',
            (
                'group.webRequestProject=group.project;group.webDataExperiment=experiment;'
                'group.webRequest=WebFiles.openFiles(group.dataFilter,true);'
            ),
            True,
            'accepted',
        ),
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
    picker_control, old, new, browser, scenario
):
    text = picker_control
    if old == 'project-identity':
        # A caller that bypasses the native guard must still red the same
        # foreign-project vector. Do not replace ApplicationInfo with a stub.
        scope = text.partition('    readonly property string dataFilter:')[2]
        callback = block(scope, 'function onFilesOpened(')
        changed_callback = callback.replace(
            'ApplicationInfo.formFilesOpened(request, files, true);',
            'if(request===group.webRequest){group.webRequest=0;'
            'group.project.loadDataInto(group.webDataExperiment,files[0]);}',
        )
        changed = text.replace(callback, changed_callback, 1)
    else:
        changed = text.replace(old, new, 1)
    assert changed != text, 'Load data routing escape: mutate the actual shipped handler'
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        require_picker(changed, browser, scenario)


@pytest.mark.parametrize('browser', [False, True])
def test_single_crystal_picker_retains_int_admission_and_owner_routing(browser):
    require_picker(source(PATH), browser, sample_form='single crystal')
