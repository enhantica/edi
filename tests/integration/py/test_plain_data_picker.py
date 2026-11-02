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
const ExperimentViewModel={SingleCrystal:'single crystal'};
const initiator={id:'initiator',canLoadData:true,calculationOnly:true,sampleForm:SAMPLE_FORM};
const other={id:'other',canLoadData:true,calculationOnly:true};
const original={currentExperimentIndex:4,
    loadDataInto:(experiment,file)=>calls.push(['loaded','original',experiment.id,file]),
    loadExperiments:files=>calls.push(['wrong-action',files])};
const foreign={currentExperimentIndex:7,
    loadDataInto:(experiment,file)=>calls.push(['loaded','foreign',experiment.id,file])};
const group={project:original,webRequest:0,webRequestProject:null,webDataExperiment:null,
    pickerLife:{alive:true}};
const row={index:2,experiment:initiator};
const Session={get project(){return group.project}};
const qsTr=text=>text;
const WebFiles={available:BROWSER,
    openFiles:(filter,multiple)=>{calls.push(['web',filter,multiple]);return 41;}};
const dataDialog={intent:null,experiment:null,project:null,selectedFile:'chosen.dat',
    open:()=>calls.push(['desktop',dataDialog.experiment.id])};
group.dataFilter=DATA_FILTER;
group.chooseData=function(experiment) CHOOSE;
function click() { ACTION }
function accept() { ACCEPTED }
RECEIVED
FAILED
CANCELLED
click();
let desktopFilters=FILTERS;
original.currentExperimentIndex=8;
SCENARIO
console.log(JSON.stringify({calls,desktopFilters}));
"""
    route = (
        'onFilesOpened(41,["chosen.dat"]); onFilesOpened(41,["duplicate.dat"]);'
        if browser
        else 'accept.call(dataDialog); accept.call(dataDialog);'
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
        'reindexed': 'row.index=9;',
        'retargeted-row': 'row.experiment=other;',
    }[scenario]
    substitutions = {
        'BROWSER': json.dumps(browser),
        'SAMPLE_FORM': json.dumps(sample_form),
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
    if browser:
        assert observed['calls'] and observed['calls'][0][0] == 'web', (
            'The real browser click must open its file chooser before routing a result'
        )
        assert (
            {'.xye', '.xy', '.dat', '.txt', '.csv', '.int'}
            | ({'.hkl'} if sample_form == 'single crystal' else set())
        ).issubset(set(observed['calls'][0][1].split(','))), (
            'The browser picker must admit every supported reflection extension, including hkl'
        )
        expected = [['web', observed['calls'][0][1], False]]
    else:
        expected = [['desktop', 'initiator']]
    if scenario not in {'foreign-project', 'closed-project', 'cancelled', 'failed'}:
        expected.append(['loaded', 'original', 'initiator', 'chosen.dat'])
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
    control = item(text, 'experiments.loadData.${row.index}')
    property_name = 'visible'  # The actual ownership/availability guard moved onto visibility.
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
        ('onClicked: group.chooseData(row.experiment)', 'onClicked: {}', True, 'accepted'),
        ('group.chooseData(row.experiment)', 'group.chooseData(other)', False, 'accepted'),
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
    old, new, browser, scenario
):
    text = source(PATH)
    require_picker(text, browser, 'accepted')
    if old == 'project-identity':
        # A caller that bypasses the native guard must still red the same
        # foreign-project vector. Do not replace ApplicationInfo with a stub.
        callback = block(text, 'function onFilesOpened(')
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
