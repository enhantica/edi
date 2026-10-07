"""Structural wiring checks; model state is exercised separately in the
core tier."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / 'app'


def source(path):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', (APP / path).read_text(), flags=re.DOTALL)


def spans(text):
    stack, found = [], []
    quote = ''
    escaped = False
    for position, character in enumerate(text):
        if quote:
            if character == quote and not escaped:
                quote = ''
            escaped = character == '\\' and not escaped
        elif character in '"\'`':
            quote = character
            escaped = False
        elif character == '{':
            stack.append(position)
        elif character == '}':
            assert stack, 'Scan wiring: source blocks must balance before inspection'
            found.append((stack.pop(), position + 1))
    assert not stack, 'Scan wiring: source blocks must close before inspection'
    return found


def block(text, marker):
    assert marker in text, (
        'Scan wiring: the claimed operation must exist in its effective component: ' + marker
    )
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 0
    quote = ''
    escaped = False
    for position in range(opening, len(text)):
        character = text[position]
        if quote:
            if character == quote and not escaped:
                quote = ''
            escaped = character == '\\' and not escaped
        elif character in '"\'`':
            quote = character
            escaped = False
        elif character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
            if depth == 0:
                return text[start : position + 1]
    pytest.fail('Scan wiring: the observed block must close before inspection')


def item(text, object_name):
    match = re.search(r'objectName:\s*["\'`]' + re.escape(object_name) + r'["\'`]', text)
    assert match, 'Scan wiring: the claimed control must exist in the shipped component'
    begin, end = min(
        ((a, b) for a, b in spans(text) if a < match.start() < b), key=lambda x: x[1] - x[0]
    )
    return text[begin:end]


def require(text, pattern, message):
    assert re.search(pattern, text, re.DOTALL), (
        'Scan wiring: the claimed control must preserve its actual binding: ' + message
    )


def property_value(text, name):
    opening = text.find('{')
    nested = [(a, b) for a, b in spans(text) if a > opening]
    pattern = r'(?m)^\s*(?:(?:readonly\s+)?property\s+\w+\s+)?' + re.escape(name) + r':\s*'
    for match in re.finditer(pattern, text):
        if any(a < match.start() < b for a, b in nested):
            continue
        start = match.end()
        if text[start] == '{':
            return block(text[start:], '{')
        if text[start] == '[':
            depth, quote = 0, ''
            for end in range(start, len(text)):
                c = text[end]
                if quote:
                    if c == quote and text[end - 1] != '\\':
                        quote = ''
                elif c in '"\'`':
                    quote = c
                elif c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        return text[start : end + 1]
        line = text[start : text.index('\n', start)].strip()
        if line.endswith('{'):
            opening = text.index('{', start)
            return text[start:opening] + block(text[opening:], '{')
        return line
    pytest.fail('Scan wiring: the claimed property must bind on its own control: ' + name)


def control_type(text, name):
    owned = item(text, name)
    start = text.index(owned)
    match = re.search(r'([\w.]+)\s*$', text[:start])
    assert match, 'Scan wiring: the actual control must resolve its base type'
    return match.group(1)


def javascript(program):
    node = Path(sys.prefix) / 'bin/node'
    assert node.is_file(), 'Scan wiring: the declared Python environment supplies Node'
    result = subprocess.run(
        [node], input=program, text=True, capture_output=True, check=False, timeout=5
    )
    assert result.returncode == 0, (
        'Scan wiring: the actual expression must execute: ' + result.stderr
    )
    return json.loads(result.stdout)


def evaluate(expression, context=''):
    value = (
        '(function()' + expression + ')()'
        if expression.startswith('{')
        else '(' + expression + ')'
    )
    return javascript(context + '\nconsole.log(JSON.stringify(' + value + '));')


def require_availability(text):
    control = item(text, 'experiments.loadData.${row.index}')
    visible = property_value(control, 'visible')
    enabled = property_value(control, 'enabled')
    contexts = [
        (False, {'canLoadData': True, 'calculationOnly': True}, True),
        (False, {'canLoadData': True, 'calculationOnly': False}, True),
        (False, {'canLoadData': False, 'calculationOnly': True}, False),
        (False, {'canLoadData': False, 'calculationOnly': False}, False),
        (False, None, False),
        (True, {'canLoadData': True, 'calculationOnly': True}, False),
        (True, {'canLoadData': True, 'calculationOnly': False}, False),
    ]
    program = 'let observed=[];'
    for scan, experiment, _ in contexts:
        program += (
            '{const group={scan:' + json.dumps(scan) + '};'
            'const row={experiment:' + json.dumps(experiment) + '};'
            'observed.push(Boolean((' + visible + ') && (' + enabled + ')));}'
        )
    program += 'console.log(JSON.stringify(observed));'
    assert javascript(program) == [expected for _, _, expected in contexts], (
        'Load data availability: created unloaded and loaded rows admit the action; '
        'imported, absent and scan rows cannot invoke it'
    )


def assert_search(shared, delegate=None):
    field = item(shared, 'comboBox.search')
    delegate = delegate or block(shared, 'delegate:')
    matcher = block(shared, 'function matches(')
    # Both a direct input binding and state updated by the input are valid compositions.
    program = """const control = {count: 11, searchText: ""}; const searchField = {text:
""};
const selector = control; const EaStyle = {Sizes: {comboBoxHeight:
24}};
Object.defineProperty(control, 'searchThreshold', {get: () => THRESHOLD}

);
Object.defineProperty(control, 'searchable', {get: () => {let {count,

searchThreshold} = control; return SEARCHABLE}});
Object.defineProperty(control, 'filter', {get: () => {let {searchable,

searchText} = control; return FILTER}});
control.matches = function(text) {let filter = control.filter; MATCH_BODY}

;
let output=[];
for (const size of [10,11]) {
 control.count=size;
 for (const term of ["SiO", "absent"]) {
  const text=term; searchField.text=term; ASSIGN;
  const shown=evaluateRow("CoSiO cooling.dat");
  output.push([control.searchable, shown]);
 }
}
function evaluateRow(text) {
 const matching = MATCHING;
 return !!(VISIBLE) && (HEIGHT)>0 && (OPACITY)>0;
}
console.log(JSON.stringify(output));"""
    replacements = {
        'THRESHOLD': property_value(shared, 'searchThreshold'),
        'SEARCHABLE': property_value(shared, 'searchable'),
        'FILTER': property_value(shared, 'filter'),
        'MATCH_BODY': matcher[matcher.index('{') + 1 : -1],
        'ASSIGN': property_value(field, 'onTextChanged'),
        'MATCHING': property_value(delegate, 'matching') if 'matching:' in delegate else 'true',
        'VISIBLE': property_value(delegate, 'visible')
        if re.search(r'(?m)^\s*visible:', delegate)
        else 'true',
        'HEIGHT': property_value(delegate, 'height')
        if re.search(r'(?m)^\s*height:', delegate)
        else '24',
        'OPACITY': property_value(delegate, 'opacity')
        if re.search(r'(?m)^\s*opacity:', delegate)
        else '1',
    }
    for token, value in replacements.items():
        program = program.replace(token, value)
    assert javascript(program) == [[False, True], [False, True], [True, True], [True, False]], (
        'Search wiring: actual field, matcher and delegate implement '
        'case-insensitive substring filtering above ten'
    )
    assert property_value(field, 'visible') == 'control.searchable', (
        'Search wiring: threshold controls the attached field'
    )
    completed = block(shared, 'Component.onCompleted:')
    require(
        completed,
        r'control\.popup\.contentItem\.header\s*=\s*searchHeader\s*;',
        'Search wiring: input is the popup list header',
    )
    accepted = property_value(field, 'onAccepted')
    result = javascript(
        """let picked=[],closed=0; const control={count:3,currentIndex:2,
textAt:i=>["other","CoSiO cooling.dat","last"][i],matches:t=>t.includes("SiO"),


activated:i=>picked.push(i),popup:{close:()=>closed++}};
(function()BODY)();console.log(JSON.stringify([control.currentIndex,

picked,closed]));""".replace('BODY', accepted)
    )
    assert result == [1, [1], 1], (
        'Search wiring: Enter selects and activates the first matching original index'
    )


def assert_follow(text):
    follow = item(text, 'fitting.follow')
    assert property_value(follow, 'checkable') == 'true', (
        'Follow wiring: the actual button must toggle'
    )
    assert property_value(follow, 'enabled') == 'group.fit !== null && group.fit.scanning', (
        'Follow wiring: its own enabled binding must require a running scan'
    )
    assert (
        property_value(follow, 'checked')
        == 'group.fit !== null && group.fit.scanning && group.fit.following'
    ), 'Follow wiring: its own checked binding must read live follow state'
    assert property_value(follow, 'onToggled') == 'group.fit.following = checked', (
        'Follow wiring: toggling must update that fit model'
    )


def test_messages_is_first_in_both_layout_and_width_inventory():
    text = source('qml/Components/StatusBar.qml')
    children = [
        block(text[match.start() :], 'StatusBarItem')
        for match in re.finditer(r'\bStatusBarItem\s*\{', text)
    ]
    assert children and 'objectName: "statusBar.warnings"' in children[0], (
        'Status bar wiring: Messages is the first actual StatusBarItem child'
    )
    require(
        text,
        r'items:\s*\[\s*warningsItem\s*,',
        'Status bar wiring: width inventory starts with Messages',
    )


def test_button_names_and_follow_have_live_model_bindings():
    text = source('qml/Pages/Analysis/FittingGroup.qml')
    start = item(text, 'fitting.start')
    assert (
        property_value(start, 'enabled')
        == 'group.fit !== null && (group.fit.running || group.fit.available)'
    ), 'Buttons wiring: availability must guard the actual fit button'
    assert (
        property_value(start, 'onClicked')
        == 'group.fit.running ? group.fit.cancel() : group.fit.start()'
    ), 'Buttons wiring: the actual fit button dispatches stop or start from live running state'
    require(
        property_value(start, 'text'),
        r'group\.fit\.running\s*\?\s*qsTr\("Stop fitting"\).*'
        r'group\.fit\.continuable\s*\?\s*qsTr\("Continue fitting"\).*'
        r'qsTr\("Start fitting"\)',
        'Buttons wiring: the actual button label follows running and resumable state',
    )
    assert_follow(text)
    follow = item(text, 'fitting.follow')
    assert control_type(text, 'fitting.start') == control_type(text, 'fitting.follow'), (
        'Buttons wiring: Start and Follow inherit the same button base'
    )
    # Both controls inherit the same base width unless they override it.
    for name in ('width', 'implicitWidth', 'wide'):
        a = re.search(r'(?m)^\s*' + name + r':([^\n]+)', start)
        b = re.search(r'(?m)^\s*' + name + r':([^\n]+)', follow)
        assert (a.group(1).strip() if a else None) == (b.group(1).strip() if b else None), (
            'Buttons wiring: Start and Follow share the same base and width override'
        )


def test_follow_observer_rejects_disconnected_controls_and_unrelated_handlers():
    text = source('qml/Pages/Analysis/FittingGroup.qml')
    assert_follow(text)
    for old, new in [
        ('checkable: true', 'checkable: false'),
        ('enabled: group.fit !== null && group.fit.scanning', 'enabled: false'),
        (
            'checked: group.fit !== null && group.fit.scanning && group.fit.following',
            'checked: true',
        ),
        ('onToggled: group.fit.following = checked', 'onToggled: {}'),
    ]:
        changed = text.replace(old, new)
        assert changed != text, (
            'Follow wiring: each escape must actually alter the production control'
        )
        changed += (
            '\nButton { enabled: group.fit.scanning; onToggled: group.fit.following = checked }'
        )
        with pytest.raises(AssertionError):
            assert_follow(changed)


OUTCOMES = [
    ('success', 'Success', 'check-circle', 'green'),
    ('maxIterations', 'Max iterations', 'exclamation-circle', 'orange'),
    ('noStep', 'No step', 'exclamation-circle', 'orange'),
    ('stopped', 'Stopped', 'stop-circle', 'themeForegroundMinor'),
    ('superseded', 'Superseded', 'minus-circle', 'themeForegroundMinor'),
    ('failed', 'Failed', 'times-circle', 'red'),
]


def outcome_functions(text):
    colors = {color: color for _key, _word, _icon, color in OUTCOMES}
    context = 'const qsTr=x=>x; const EaStyle={Colors:' + json.dumps(colors) + '};'
    return (
        context
        + '\n'
        + '\n'.join(block(text, 'function ' + name + '(') for name in ('word', 'icon', 'color'))
    )


@pytest.mark.parametrize(
    ('key', 'word', 'icon', 'color'), OUTCOMES, ids=[row[0] for row in OUTCOMES]
)
def test_view_model_names_each_outcome_from_owner_table(key, word, icon, color):
    result = evaluate(
        '[word(KEY),icon(KEY),color(KEY)]'.replace('KEY', json.dumps(key)),
        outcome_functions(source('qml/Globals/FitOutcomes.qml')),
    )
    assert result == [word, icon, color], (
        'Outcomes: effective return branches follow the owner tuple'
    )


def assert_outcome_consumers(bar, label, dialog):
    summary = item(bar, 'statusBar.fit.outcome')
    require(
        summary,
        r'outcome:\s*bar\.fit\s*\?\s*bar\.fit\.outcome\s*:\s*""',
        'Outcomes wiring: status summary reads the actual fit outcome',
    )
    context = (
        outcome_functions(source('qml/Globals/FitOutcomes.qml'))
        + '\nconst FitOutcomes={word,icon,color};'
    )
    line = block(label, 'IconLine {')
    icon_cell = block(dialog, 'IconCell {')
    value_cell = item(dialog, 'fit.results.value.${row.index}')
    expressions = [
        property_value(icon_cell, 'icon'),
        property_value(icon_cell, 'iconColor'),
        property_value(value_cell, 'text'),
        property_value(value_cell, 'color'),
    ]
    context += '\nconst keys=' + json.dumps([key for key, *_ in OUTCOMES]) + ';'
    rows = evaluate(
        'keys.map(outcome=>{const label={outcome}; '
        'const row={outcome,icon:"fallback",value:"17"}; return ['
        + property_value(line, 'segments')
        + ',['
        + ','.join(expressions)
        + ']];})',
        context,
    )
    for (_key, word, icon, color), (segments, overall) in zip(OUTCOMES, rows, strict=True):
        assert [
            segments[0]['icon'],
            segments[1]['text'],
            segments[0]['color'],
            segments[1]['color'],
        ] == [icon, word, color, color], (
            'Outcomes: displayed status segments use the effective tuple'
        )
        assert overall == [
            icon,
            color,
            word,
            color,
        ], 'Outcomes: Overall status takes the outcome branch for icon, word and both colours'
    assert not re.search(r'font\.underline:\s*true', bar + label + dialog), (
        'Outcomes: clickable summaries do not underline'
    )


def test_result_row_and_status_summary_share_outcome_presentation():
    assert_outcome_consumers(
        source('qml/Components/StatusBar.qml'),
        source('qml/Components/FitOutcomeLabel.qml'),
        source('qml/Components/FitResultsDialog.qml'),
    )
    rows = block(source('src/fit_view_model.cpp'), 'void FitResultListModel::setRecord(')
    require(
        rows,
        r'row\(QString\(\),\s*tr\("Overall status"\),'
        r'\s*status_text\(status\),\s*outcome_key\(status\)\)',
        'Outcomes wiring: Overall status carries the same typed outcome key',
    )


def test_outcome_gate_rejects_a_different_results_word():
    bar, label, dialog = (
        source('qml/Components/' + name)
        for name in ('StatusBar.qml', 'FitOutcomeLabel.qml', 'FitResultsDialog.qml')
    )
    changed = dialog.replace('FitOutcomes.word(row.outcome)', 'qsTr("Different")')
    assert changed != dialog, (
        'Outcomes: the different-word escape must reach the actual results consumer'
    )
    with pytest.raises(AssertionError):
        assert_outcome_consumers(bar, label, changed)


def assert_scan_status(text):
    area = item(text, 'statusBar.fit')
    progress = item(text, 'statusBar.fit.progress')
    outcome = item(text, 'statusBar.fit.outcome')
    values = item(text, 'statusBar.fit.values')
    context = """String.prototype.arg=function(value){return this.replace(/%[1-9]/,String(value));

};const qsTr=x=>x;
const FitOutcomes={separator:' | '};
const bar={fit:{running:true,scanning:true,ok:7,fail:2,scanOk:7,scanFailed:2,elapsed:'TIME',

eta:'ETA',chi:'CHI',goodnessOfFit:'CHI',completed:9,total:24,fraction:0.375,

percent:37.5,scanFitted:9,scanTotal:24,iterations:'13',outcome:'success'}};
const fitArea={};const EaStyle={Colors:{red:'red'}};"""
    running = property_value(area, 'running')
    states = [(True, True), (True, False), (False, True)]
    prop = 'fraction' if re.search(r'(?m)^\s*fraction:', progress) else 'value'
    maximum = property_value(progress, 'to') if re.search(r'(?m)^\s*to:', progress) else '1'
    expressions = [
        property_value(progress, 'visible'),
        property_value(outcome, 'visible'),
        'run ? (' + property_value(progress, 'indeterminate') + ') : null',
        'run && scan ? (' + property_value(progress, prop) + ') : null',
        'run && scan ? (' + maximum + ') : null',
    ]
    context += '\nconst states=' + json.dumps(states) + ';'
    actual = evaluate(
        'states.map(([run,scan])=>{ bar.fit.running=run; bar.fit.scanning=scan; '
        'fitArea.running=(' + running + '); return [' + ','.join(expressions) + '];})',
        context,
    )
    for (run, scan), (visible, terminal, striped, fill, maximum) in zip(
        states, actual, strict=True
    ):
        assert visible == run, (
            'Status bar wiring: progress visibility follows the actual running producer'
        )
        assert terminal == (not run), (
            'Status bar wiring: outcome visibility follows the terminal producer'
        )
        if run:
            assert striped == (not scan), (
                'Status bar wiring: single fits stripe and scans have determinate fill'
            )
            if scan:
                assert fill / maximum == 3 / 8, (
                    'Status bar wiring: the displayed fill is completed datasets '
                    'divided by their total'
                )
    # Execute the text that is actually displayed, not an unused facts array.
    state = (
        context
        + 'bar.fit.scanning=true;bar.fit.running=true;fitArea.running=true;'
        + 'fitArea.scanning=('
        + property_value(area, 'scanning')
        + ');'
        + block(area, 'function joined(').replace('function joined', 'fitArea.joined = function')
        + ';'
    )
    if 'function counts(' in area:
        state += (
            block(area, 'function counts(').replace('function counts', 'fitArea.counts = function')
            + ';'
        )
    for name in ('chi', 'iterations'):
        state += 'fitArea.' + name + '=(' + property_value(area, name) + ');'
    shown = evaluate(property_value(values, 'text'), state)
    assert re.search(r'7.*2.*TIME.*ETA.*CHI', shown), (
        'Status bar wiring: the live-value consumer displays ok, fail, time, ETA and chi in order'
    )
    assert not re.search(r'\.(?:cancel|stop)\s*\(', text), (
        'Status bar wiring: no handler in the bar stops a fit'
    )


def test_status_fit_area_binds_live_progress_and_terminal_summary():
    assert_scan_status(source('qml/Components/StatusBar.qml'))


def test_create_experiment_is_enabled_and_routes_to_view_model():
    text = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    create = item(text, 'experiments.create')
    require(
        create,
        r'enabled:\s*group\.project !== null && group\.project\.canCreateExperiment',
        'Create wiring: the actual button admits valid simulation creation',
    )
    require(
        create,
        r'onClicked:\s*group\.project\.createExperiment\(\)',
        'Create wiring: the actual button enters the supported method',
    )
    body = block(source('src/project_view_model.cpp'), 'bool ProjectViewModel::createExperiment(')
    require(
        body,
        r'apply\(edi::Edit::create_experiment\(',
        'Create wiring: the supported method applies the closed core edit',
    )
    require(
        body,
        r'setCurrentExperimentIndex\(static_cast<int>\(experiment_models_\.size\(\)\) - 1\);',
        'Create wiring: creation selects the newly added row',
    )
    require(
        item(text, 'experiments.load'),
        r'loadDialog\.open\(\)|WebFiles\.openFiles\(',
        'Load wiring: the actual action opens the multi-file loader',
    )
    require(
        block(text, 'FileDialog {'),
        r'onAccepted:\s*group\.project\.loadExperiments\(selectedFiles\)',
        'Load wiring: accepted files reach the supported edit boundary',
    )

    assert property_value(block(text, 'FileDialog {'), 'fileMode') == 'FileDialog.OpenFiles', (
        'Load wiring: desktop chooses multiple files'
    )
    action = property_value(item(text, 'experiments.load'), 'onClicked')
    received = block(text, 'function onFilesOpened(')
    for available in (False, True):
        program = (
            """let calls=[]; const files=['a.edi','b.edi'];
const group={project:{loadExperiments:x=>calls.push(['loaded',x])},

webRequest:0,webRequestProject:null};
const WebFiles={available:AVAILABLE,openFiles:(filter,multiple)=>{calls.push(['web',

filter,multiple]);return 41}};
const loadDialog={open:()=>calls.push(['desktop'])};
(function()ACTION)();
RECEIVED
if(WebFiles.available) onFilesOpened(41,files);
console.log(JSON.stringify(calls));"""
            .replace('AVAILABLE', json.dumps(available))
            .replace('ACTION', action)
            .replace('RECEIVED', received)
        )
        expected = (
            [['web', '.edi', True], ['loaded', ['a.edi', 'b.edi']]] if available else [['desktop']]
        )
        assert javascript(program) == expected, (
            'Load wiring: each platform opens its multi-file route and '
            'browser files reach the initiating project'
        )


def test_type_selectors_live_in_explorer_and_follow_selected_row():
    explorer = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    component = block(explorer, 'ExperimentTypeGroup {')
    require(
        component,
        r'experiment:\s*group\.project\s*\?\s*group\.project\.currentExperiment\s*:\s*null',
        'Type wiring: values come from the selected experiment',
    )
    require(
        component,
        r'experimentIndex:\s*group\.project\s*\?\s*group\.project\.currentExperimentIndex\s*:\s*-1',
        'Type wiring: writes target the selected experiment index',
    )
    assert (
        explorer.index('objectName: "experiments.list"')
        < explorer.index('ExperimentTypeGroup {')
        < explorer.index('objectName: "experiments.create"')
    ), 'Type wiring: selectors sit between the explorer and its footer'
    assert 'ExperimentTypeGroup' not in source('qml/Pages/Experiment/ExperimentPage.qml'), (
        'Type wiring: the previous sidebar instance is removed'
    )


@pytest.mark.parametrize('axis', ['sampleForm', 'beamMode', 'radiationProbe', 'scatteringType'])
def test_data_free_experiment_type_has_a_write_boundary(axis):
    text = source('qml/Pages/Experiment/ExperimentTypeGroup.qml')
    control = item(text, 'experimentType.' + axis)
    assert property_value(control, 'enabled') == 'row.editable', (
        'Type wiring: each actual selector follows the data-free guard'
    )
    require(
        text,
        r'property bool editable:\s*experiment !== null && experiment\.calculationOnly',
        'Type wiring: measured data locks every type selector',
    )
    require(
        control,
        r'onActivated:\s*index => row\.choose\(' + axis + r',\s*"' + axis + r'",\s*index\)',
        'Type wiring: each supported axis uses the selected-row edit route',
    )
    chooser = block(text, 'function choose(')
    program = """const Qt={binding:f=>f()}; let calls=[];
const row={experimentIndex:3,project:{setExperimentType:(...args)=>calls.push(args)}

};
const box={value:'old',permittedValues:['old','chosen','other'],currentIndex:0}

;
CHOOSER
choose(box,AXIS,1);
console.log(JSON.stringify([calls,box.currentIndex]));""".replace('CHOOSER', chooser).replace(
        'AXIS', json.dumps(axis)
    )
    assert javascript(program) == [[[3, axis, 'chosen']], 0], (
        'Type wiring: activation forwards the selected experiment, axis '
        'and option token and restores its stored index'
    )
    require(
        block(source('src/project_view_model.cpp'), 'bool ProjectViewModel::setExperimentType('),
        r'apply\(edi::Edit::replace_experiment\(project,\s*experiment,',
        'Type wiring: supported edits reach the core replacement boundary',
    )


def test_disabled_placeholders_and_load_data_are_present():
    types = source('qml/Pages/Experiment/ExperimentTypeGroup.qml')
    for placeholder in ('dimensionality', 'polarization'):
        assert (
            property_value(item(types, 'experimentType.' + placeholder), 'enabled') == 'false'
        ), 'Type wiring: each placeholder is disabled on its own control'
    assert (
        property_value(item(types, 'experimentType.polarization'), 'visible')
        == 'row.experiment !== null && row.experiment.radiationProbe ==='
        ' ExperimentViewModel.Neutron'
    ), 'Type wiring: polarization is restricted to neutron experiments'
    require_availability(source('qml/Pages/Experiment/ExperimentsGroup.qml'))


@pytest.mark.parametrize('field', ['minimum', 'maximum', 'step'])
def test_simulation_range_fields_have_live_write_bindings(field):
    text = source('qml/Pages/Experiment/MeasuredRangeGroup.qml')
    control = item(text, 'range.' + field)
    assert property_value(control, 'editable') == 'group.editable', (
        'Range wiring: each actual field shares the simulation guard'
    )
    require(
        text,
        r'property bool editable:\s*experiment !== null && experiment\.calculationOnly',
        'Range wiring: measured data locks range edits',
    )
    handler = property_value(control, 'onCommitted')
    result = evaluate(
        '(' + handler + ')("13.25")',
        'let calls=[]; const '
        'group={range:{minimum:4,maximum:80,step:0.2},experiment:{setRange'
        ':(...args)=>{calls.push(args);return calls}}};',
    )
    expected = [4, 80, 0.2]
    expected[['minimum', 'maximum', 'step'].index(field)] = 13.25
    assert result == [expected], (
        'Range wiring: the activated field forwards its value and '
        'preserves the other two coordinates'
    )
    require(
        block(source('src/experiment_view_model.cpp'), 'void ExperimentViewModel::setRange('),
        r'editor_\.apply\(edi::Edit::data_range\(experiment,\s*start,\s*end,\s*step\)',
        'Range wiring: the supported method applies the validated core range edit',
    )


def test_sidebar_tabs_have_requested_names():
    text = source('qml/Components/WorkflowPage.qml')
    assert [
        property_value(item(text, 'sideBar.tab.' + key), 'text')
        for key in ('basic', 'extras', 'text')
    ] == ['qsTr("Main")', 'qsTr("Extra")', 'qsTr("Text")'], (
        'Sidebar: actual tabs read Main, Extra, Text'
    )


def assert_explorer_outcomes(qml):
    control = item(qml, 'experiments.fit.${row.index}')
    expressions = [property_value(control, prop) for prop in ('icon', 'iconColor', 'toolTip')]
    expressions = [
        '(function()' + value + ')()' if value.startswith('{') else '(' + value + ')'
        for value in expressions
    ]
    context = outcome_functions(source('qml/Globals/FitOutcomes.qml'))
    context += (
        '\nconst FitOutcomes={word,icon,color}; const keys='
        + json.dumps([key for key, _word, _icon, _color in OUTCOMES])
        + ';'
    )
    actual = evaluate(
        'keys.map(fitOutcome=>{ const row={fitOutcome}; return ['
        + ','.join(expressions)
        + ']; })',
        context,
    )
    assert actual == [[icon, color, word] for _key, word, icon, color in OUTCOMES], (
        'Fit lists wiring: the displayed explorer tuple equals its row outcome'
    )


def test_explorer_fit_column_has_outcome_model_roles():
    assert_explorer_outcomes(source('qml/Pages/Experiment/ExperimentsGroup.qml'))


@pytest.mark.parametrize(
    ('prop', 'fallback'),
    [
        ('icon', '"times-circle"'),
        ('iconColor', '"red"'),
        ('toolTip', '"Failed"'),
    ],
)
def test_explorer_observer_rejects_untaken_mapping_branches(prop, fallback):
    qml = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert_explorer_outcomes(qml)
    control = item(qml, 'experiments.fit.${row.index}')
    expression = property_value(control, prop)
    changed = control.replace(expression, 'false ? (' + expression + ') : ' + fallback, 1)
    assert changed != control, 'Fit lists wiring: the escape alters the actual cell expression'
    with pytest.raises(AssertionError, match='displayed explorer tuple'):
        assert_explorer_outcomes(qml.replace(control, changed, 1))


def test_javascript_uses_declared_runtime_with_empty_path(monkeypatch):
    monkeypatch.setenv('PATH', '')
    assert evaluate('3 * 7') == 21, (
        'Scan wiring: expression execution uses the declared runtime without ambient PATH'
    )


@pytest.mark.parametrize('component', ['AliasesGroup', 'ConstraintsGroup'])
def test_long_parameter_pickers_use_shared_search_component(component):
    text = source(f'qml/Pages/Analysis/{component}.qml')
    pickers = re.findall(r'\b(?:EaElements\.)?(\w*ComboBox)\s*\{', text)
    assert all(name == 'SearchableComboBox' for name in pickers), (
        'Search wiring: every project-item picker uses the shared search component'
    )
    shared = source('qml/Components/SearchableComboBox.qml')
    assert_search(shared)
    assert_search(shared, block(source('qml/Components/BlockSelector.qml'), 'delegate:'))


def status_mapping(text, tmp_path):
    declarations = """#include <iostream>
#include <string>
using QString=std::string;
#define QStringLiteral(value) std::string(value)
namespace edi { enum class FitStatus {DONE,MAX_ITER,NO_STEP,CANCELLED,

SUPERSEDED,UNAVAILABLE,ERROR}; }
struct FitViewModel {static std::string tr(const char* value) {return value;

}};"""
    declarations += (
        block(text, 'QString outcome_key(') + '\n' + block(text, 'QString status_text(')
    )
    declarations += """
int main() {for(int i=0;i<7;++i) {auto status=static_cast<edi::FitStatus>(i);

 std::cout<<outcome_key(status)<<"|"<<status_text(status)<<"\\n";}}"""
    file = tmp_path / 'mapping.cpp'
    file.write_text(declarations)
    executable = tmp_path / 'mapping'
    result = subprocess.run(
        ['c++', '-std=c++20', str(file), '-o', str(executable)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'Outcomes: the actual typed producer mapping must compile: ' + result.stderr
    )
    return subprocess.run(
        [str(executable)], capture_output=True, text=True, check=True, timeout=5
    ).stdout.splitlines()


@pytest.fixture(scope='module')
def status_receipts(tmp_path_factory, status_control):
    tmp_path = tmp_path_factory.mktemp('outcomes')
    expected = [key + '|' + word for key, word, _icon, _color in OUTCOMES[:5]] + [
        'failed|Failed',
        'failed|Failed',
    ]
    text = source('src/fit_view_model.cpp')
    good = status_mapping(text, tmp_path)
    changed = text.replace(
        'case edi::FitStatus::MAX_ITER: return QStringLiteral("maxIterations");',
        'case edi::FitStatus::MAX_ITER: return QStringLiteral("failed");',
    )
    assert changed != text, (
        'Outcomes: the producer escape must alter MAX_ITER at its actual branch'
    )
    return good, status_mapping(changed, tmp_path), expected, status_control


@pytest.mark.parametrize('variant', ['actual', 'wrongMAX'])
def test_typed_status_producer_matches_the_shared_outcome_keys(status_receipts, variant):
    good, bad, expected, _control = status_receipts
    assert (good == expected) if variant == 'actual' else (bad != expected), (
        'Outcomes: the typed map follows the owner table and rejects a wrong MAX_ITER key'
    )


@pytest.mark.parametrize(
    'channel',
    [
        'outcome-icon',
        'outcome-color',
        'outcome-word',
        'search-input',
        'search-height',
        'search-opacity',
        'search-header',
        'search-index',
        'block-delegate',
    ],
)
def test_effective_consumers_reject_wrong_branches_and_disconnected_search(channel):
    bar, label, dialog = (
        source('qml/Components/' + name)
        for name in ('StatusBar.qml', 'FitOutcomeLabel.qml', 'FitResultsDialog.qml')
    )
    if channel.startswith('outcome-'):
        assert_outcome_consumers(bar, label, dialog)
        for old, new in [
            ('row.outcome !== "" ? FitOutcomes.icon', 'row.outcome === "" ? FitOutcomes.icon'),
            ('row.outcome !== "" ? FitOutcomes.color', 'row.outcome === "" ? FitOutcomes.color'),
            ('row.outcome !== "" ? FitOutcomes.word', 'row.outcome === "" ? FitOutcomes.word'),
        ]:
            if not old.endswith(channel.removeprefix('outcome-')):
                continue
            mutated = dialog.replace(old, new)
            assert mutated != dialog, (
                'Outcomes: each wrong-branch escape reaches the effective results expression'
            )
            with pytest.raises(AssertionError):
                assert_outcome_consumers(bar, label, mutated)
    shared = source('qml/Components/SearchableComboBox.qml')
    for old, new in [
        ('control.searchText = text', 'control.searchText = ""'),
        (
            'matching ? EaStyle.Sizes.comboBoxHeight : 0',
            'matching ? 0 : EaStyle.Sizes.comboBoxHeight',
        ),
        ('matching ? 1 : 0', 'matching ? 0 : 1'),
        (
            'control.popup.contentItem.header = searchHeader',
            'control.popup.contentItem.header = null',
        ),
        ('control.currentIndex = i', 'control.currentIndex = 0'),
    ]:
        key = {
            'control.searchText = text': 'search-input',
            'matching ? EaStyle.Sizes.comboBoxHeight : 0': 'search-height',
            'matching ? 1 : 0': 'search-opacity',
            'control.popup.contentItem.header = searchHeader': 'search-header',
            'control.currentIndex = i': 'search-index',
        }[old]
        if channel != key:
            continue
        mutated = shared.replace(old, new)
        assert mutated != shared, (
            'Search wiring: each escape must change the connected input or row'
        )
        with pytest.raises(AssertionError):
            assert_search(mutated)
    if channel != 'block-delegate':
        return
    block_delegate = block(source('qml/Components/BlockSelector.qml'), 'delegate:')
    changed = block_delegate.replace('selector.matches(text)', 'true')
    assert changed != block_delegate, 'Search wiring: the escape changes the overridden delegate'
    with pytest.raises(AssertionError):
        assert_search(shared, changed)


def test_search_accepts_direct_field_and_state_compositions():
    shared = source('qml/Components/SearchableComboBox.qml')
    direct = shared.replace(
        'searchable ? searchText.trim().toLowerCase()',
        'searchable ? searchField.text.trim().toLowerCase()',
    )
    assert direct != shared, (
        'Search wiring: the control supplies the alternative field composition'
    )
    delegate = block(shared, 'delegate:')
    visible_delegate = (
        delegate
        .replace(
            'height: matching ? EaStyle.Sizes.comboBoxHeight : 0',
            'height: EaStyle.Sizes.comboBoxHeight',
        )
        .replace('opacity: matching ? 1 : 0', 'opacity: 1')
        .replace(
            'readonly property bool matching: control.matches(text)',
            'readonly property bool matching: control.matches(text)\n        visible: matching',
        )
    )
    assert visible_delegate != delegate, 'Search wiring: the control supplies visibility filtering'
    assert_search(shared)
    assert_search(direct, visible_delegate)


def test_forwarding_controls_reject_wrong_selected_index_token_range_and_visibility(monkeypatch):
    original = source
    # Load-data availability escapes live in test_plain_data_picker, with their
    # own valid controls for unloaded, loaded and imported rows.
    checks = [
        (
            'src/project_view_model.cpp',
            'setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);',
            'setCurrentExperimentIndex(0);',
            test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
        (
            'qml/Pages/Experiment/ExperimentTypeGroup.qml',
            'box.permittedValues[index]',
            'box.permittedValues[0]',
            test_data_free_experiment_type_has_a_write_boundary,
            ('beamMode',),
        ),
        (
            'qml/Pages/Experiment/ExperimentTypeGroup.qml',
            'row.experimentIndex, axis, token',
            '0, axis, token',
            test_data_free_experiment_type_has_a_write_boundary,
            ('beamMode',),
        ),
        (
            'qml/Pages/Experiment/ExperimentTypeGroup.qml',
            'row.experiment.radiationProbe === ExperimentViewModel.Neutron',
            'row.experiment.radiationProbe === ExperimentViewModel.Neutron || true',
            test_disabled_placeholders_and_load_data_are_present,
            (),
        ),
        (
            'qml/Pages/Experiment/MeasuredRangeGroup.qml',
            'setRange(Number(text), group.range.maximum, group.range.step)',
            'setRange(group.range.minimum, Number(text), group.range.step)',
            test_simulation_range_fields_have_live_write_bindings,
            ('minimum',),
        ),
        (
            'qml/Pages/Experiment/ExperimentsGroup.qml',
            'fileMode: FileDialog.OpenFiles',
            'fileMode: FileDialog.OpenFile',
            test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
        (
            'qml/Pages/Experiment/ExperimentsGroup.qml',
            'group.project.loadExperiments(files)',
            'group.project.loadExperiments([])',
            test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
    ]
    for path, old, new, check, args in checks:
        changed = original(path).replace(old, new)
        assert changed != original(path), (
            'Scan wiring: every forwarding escape must reach its actual operation'
        )
        monkeypatch.setattr(
            __import__(__name__, fromlist=['source']),
            'source',
            lambda name, changed=changed, path=path: changed if name == path else original(name),
        )
        with pytest.raises((AssertionError, pytest.fail.Exception)):
            check(*args)
    monkeypatch.setattr(__import__(__name__, fromlist=['source']), 'source', original)


@pytest.fixture(scope='module')
def status_control():
    actual = source('qml/Components/StatusBar.qml')
    # The control supplies the pending scan presentation without counting it as product evidence.
    progress = item(actual, 'statusBar.fit.progress')
    progress_control = progress.replace(
        'indeterminate: true',
        'indeterminate: !bar.fit.scanning\n            value: bar.fit.completed / bar.fit.total',
    )
    values = item(actual, 'statusBar.fit.values')
    body = property_value(values, 'text')
    visible_control = values.replace(
        body, 'fitArea.joined([bar.fit.ok,bar.fit.fail,bar.fit.elapsed,bar.fit.eta,fitArea.chi])'
    )
    good = actual.replace(progress, progress_control).replace(values, visible_control)
    assert_scan_status(good)
    return good


@pytest.mark.parametrize('channel', ['polarity', 'fill', 'producer', 'facts'])
def test_status_observer_rejects_wrong_progress_polarity_fill_producer_and_unused_facts(
    channel, status_control
):
    good = status_control
    for key, (old, new) in zip(
        ['polarity', 'fill', 'producer', 'facts'],
        [
            (
                property_value(item(good, 'statusBar.fit.progress'), 'indeterminate'),
                'bar.fit.scanning',
            ),
            (
                property_value(item(good, 'statusBar.fit.progress'), 'fraction')
                if 'fraction:' in item(good, 'statusBar.fit.progress')
                else property_value(item(good, 'statusBar.fit.progress'), 'value'),
                '1',
            ),
            ('bar.fit !== null && bar.fit.running', 'false'),
            (
                (
                    'text: '
                    'fitArea.joined([bar.fit.ok,bar.fit.fail,bar.fit.elapsed,bar.fit.e'
                    'ta,fitArea.chi])'
                ),
                'text: "wrong"',
            ),
        ],
        strict=True,
    ):
        if key != channel:
            continue
        bad = good.replace(old, new)
        assert bad != good, (
            'Status bar wiring: each wrong effective branch reaches the actual control'
        )
        with pytest.raises(AssertionError):
            assert_scan_status(bad)
