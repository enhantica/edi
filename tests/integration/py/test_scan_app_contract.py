"""Structural wiring checks; model state is exercised separately in the core tier."""

from __future__ import annotations

import re
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
    match = re.search(r'(?m)^\s*' + re.escape(name) + r':\s*([^\n]+)', text)
    assert match, 'Scan wiring: the claimed property must bind on its own control'
    return match.group(1).strip()


def assert_follow(text):
    follow = item(text, 'fitting.follow')
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
        ('enabled: group.fit !== null && group.fit.scanning', 'enabled: false'),
        (
            'checked: group.fit !== null && group.fit.scanning && group.fit.following',
            'checked: true',
        ),
        ('onToggled: group.fit.following = checked', 'onToggled: {}'),
    ]:
        changed = (
            text.replace(old, new)
            + '\nButton { enabled: group.fit.scanning; onToggled: group.fit.following = checked }'
        )
        assert changed != text, (
            'Follow wiring: each escape must actually alter the production control'
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


def switch_value(text, function, key):
    body = block(text, 'function ' + function + '(')
    cases = list(re.finditer(r'case\s+"([^\"]+)":', body))
    selected = next((m for m in cases if m.group(1) == key), None)
    if selected:
        returned = re.search(r'\breturn\s+([^;]+);', body[selected.end() :])
    else:
        last_switch = max(end for begin, end in spans(body) if begin > body.index('{'))
        returned = re.search(r'\breturn\s+([^;]+);', body[last_switch:])
    assert returned, (
        'Outcomes wiring: each outcome must resolve through the called presentation function'
    )
    return returned.group(1).strip()


@pytest.mark.parametrize(('key', 'word', 'icon', 'color'), OUTCOMES)
def test_view_model_names_each_outcome_from_owner_table(key, word, icon, color):
    text = source('qml/Globals/FitOutcomes.qml')
    assert switch_value(text, 'word', key) == f'qsTr("{word}")', (
        'Outcomes: the called word function follows the owner table'
    )
    assert switch_value(text, 'icon', key) == f'"{icon}"', (
        'Outcomes: the called icon function follows the owner table'
    )
    assert switch_value(text, 'color', key) == 'EaStyle.Colors.' + color, (
        'Outcomes: the called colour function follows the owner table'
    )


def assert_outcome_consumers(bar, label, dialog):
    summary = item(bar, 'statusBar.fit.outcome')
    require(
        summary,
        r'outcome:\s*bar\.fit\s*\?\s*bar\.fit\.outcome\s*:\s*""',
        'Outcomes wiring: status summary reads the actual fit outcome',
    )
    for function in ('icon', 'word', 'color'):
        require(
            label,
            r'FitOutcomes\.' + function + r'\(label\.outcome\)',
            'Outcomes wiring: status label uses the shared tuple',
        )
        require(
            dialog,
            r'FitOutcomes\.' + function + r'\(row\.outcome\)',
            'Outcomes wiring: results row uses the shared tuple',
        )
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


def test_status_fit_area_binds_live_progress_and_terminal_summary():
    text = source('qml/Components/StatusBar.qml')
    progress = item(text, 'statusBar.fit.progress')
    outcome = item(text, 'statusBar.fit.outcome')
    assert property_value(progress, 'visible') == 'fitArea.running', (
        'Status bar wiring: running details disappear after fitting'
    )
    require(
        outcome,
        r'visible:\s*!fitArea\.running',
        'Status bar wiring: only the terminal outcome remains after fitting',
    )
    # The scan branch must carry actual live values, in the required order, in this area.
    area = item(text, 'statusBar.fit')
    require(
        area,
        r'\[[^]]*\.ok[^]]*\.fail[^]]*\.elapsed[^]]*\.eta[^]]*\.chi',
        'Status bar wiring: scan facts are bound in ok, fail, time, ETA, chi order',
    )
    require(
        progress,
        r'indeterminate:\s*[^\n]*scann',
        'Status bar wiring: stripe mode distinguishes single from scan progress',
    )
    require(
        progress,
        r'(?:value|fraction):\s*[^\n]*\.(?:percent|fraction|completed)',
        'Status bar wiring: scan fill is bound to completion',
    )
    assert not re.search(r'\.(?:cancel|stop)\s*\(', text), (
        'Status bar wiring: no handler in the bar stops a fit'
    )


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
        body, r'setCurrentExperimentIndex\(', 'Create wiring: creation selects the newly added row'
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
    require(
        block(text, 'function choose('),
        r'row\.project\.setExperimentType\(row\.experimentIndex,\s*axis,\s*token\)',
        'Type wiring: the helper sends the actual selected index and token',
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
    require(
        item(types, 'experimentType.polarization'),
        r'visible:.*radiationProbe === ExperimentViewModel\.Neutron',
        'Type wiring: polarization is visible only for a neutron probe',
    )
    control = item(
        source('qml/Pages/Experiment/ExperimentsGroup.qml'), 'experiments.loadData.${row.index}'
    )
    assert property_value(control, 'enabled') == 'false', (
        'Load data wiring: the actual row action remains disabled'
    )
    require(
        control,
        r'visible:.*row\.experiment\.calculationOnly',
        'Load data wiring: the action belongs only to simulations',
    )


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
    require(
        control,
        r'onCommitted:\s*text => group\.experiment\.setRange\(',
        'Range wiring: range edits use the supported setRange method',
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


def test_explorer_fit_column_has_outcome_model_roles():
    qml = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    control = item(qml, 'experiments.fit.${row.index}')
    for function, prop in [('icon', 'icon'), ('color', 'iconColor'), ('word', 'toolTip')]:
        require(
            property_value(control, prop),
            r'FitOutcomes\.' + function + r'\(row\.fitOutcome\)',
            'Fit lists wiring: the actual cell uses its row outcome tuple',
        )


@pytest.mark.parametrize('component', ['AliasesGroup', 'ConstraintsGroup'])
def test_long_parameter_pickers_use_shared_search_component(component):
    text = source(f'qml/Pages/Analysis/{component}.qml')
    pickers = re.findall(r'\b(?:EaElements\.)?(\w*ComboBox)\s*\{', text)
    assert pickers and all(name == 'SearchableComboBox' for name in pickers), (
        'Search wiring: every project-item picker uses the shared search component'
    )
    shared = source('qml/Components/SearchableComboBox.qml')
    require(
        shared,
        r'property int searchThreshold:\s*10',
        'Search wiring: the shared threshold is ten entries',
    )
    require(
        shared,
        r'property bool searchable:\s*count > searchThreshold',
        'Search wiring: strictly more than ten shows search',
    )
    require(
        item(shared, 'comboBox.search'),
        r'visible:\s*control\.searchable',
        'Search wiring: the actual input follows that threshold',
    )
    require(
        shared,
        r'property string filter:\s*searchable\s*\?\s*searchField\.text',
        'Search wiring: matches read the actual search input',
    )
    require(
        block(shared, 'function matches('),
        r'String\(text\)\.toLowerCase\(\)\.includes\(filter\)',
        'Search wiring: any substring is matched',
    )
    require(
        block(shared, 'delegate:'),
        r'visible:\s*control\.matches\(text\)',
        'Search wiring: actual delegate visibility uses the match result',
    )
