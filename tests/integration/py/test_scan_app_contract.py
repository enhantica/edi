"""App binding contracts from the owner's outcome and interaction tables.

These source observers cover the enabled non-GUI tier. Rendered look and event
behavior remain the owner's check while the Qt app tiers are disabled.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / 'app'


def source(path):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', (APP / path).read_text(), flags=re.DOTALL)


def block(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 1
    index = opening + 1
    quote = ''
    while index < len(text) and depth:
        character = text[index]
        if quote:
            if character == quote and text[index - 1] != '\\':
                quote = ''
        elif character in '"\'`':
            quote = character
        elif character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
        index += 1
    assert depth == 0, 'Scan UI: observed component blocks must have balanced braces'
    return text[start:index]


def item(text, object_name):
    match = re.search(r'objectName:\s*[\"\']' + re.escape(object_name) + r'[\"\']', text)
    assert match, 'Scan UI: the requested control must exist in the shipped view'
    opening = text.rfind('{', 0, match.start())
    return block(text[opening:], '{')


def test_messages_is_first_in_both_layout_and_width_inventory():
    text = source('qml/Components/StatusBar.qml')
    controls = re.findall(r'objectName:\s*"(statusBar\.[^"]+)"', text)
    assert controls and controls[0] == 'statusBar.warnings', (
        'Status bar: Messages must be the first displayed item'
    )
    inventory = re.search(r'items:\s*\[([^]]+)\]', text)
    if inventory:
        assert inventory.group(1).strip().split(',')[0].strip() == 'warningsItem', (
            'Status bar: width accounting must use the same Messages-first order'
        )


def test_button_names_and_follow_have_live_model_bindings():
    text = source('qml/Pages/Analysis/FittingGroup.qml')
    assert 'Cancel fitting' not in text and 'Stop fitting' in text, (
        'Buttons: a running fit reads Stop fitting because its partial result is retained'
    )
    combined = text + source('src/fit_view_model.cpp')
    assert 'Continue fitting' in combined and 'Start fitting' in combined, (
        'Buttons: a partial scan offers Continue and a fresh run offers Start'
    )
    assert re.search(r'(?:qsTr|tr)\("Follow"\)', text), (
        'Follow: the Analysis fitting group must expose the requested toggle'
    )
    follow = text
    assert re.search(r'(?:checked|checkable):', follow) and re.search(
        r'on(?:Clicked|Toggled):', follow
    ), 'Follow: the toggle must read and write live state'
    assert re.search(r'width:|Layout\.fillWidth:|wide:', text), (
        'Buttons: Start and Follow must have an explicit layout width contract'
    )


@pytest.mark.parametrize(
    ('status_code', 'word'),
    [
        ('DONE', 'Success'),
        ('MAX_ITER', 'Max iterations'),
        ('NO_STEP', 'No step'),
        ('CANCELLED', 'Stopped'),
        ('SUPERSEDED', 'Superseded'),
        ('ERROR', 'Failed'),
    ],
)
def test_view_model_names_each_outcome_from_owner_table(status_code, word):
    files = list((APP / 'src').glob('*fit*.*'))
    text = '\n'.join(
        re.sub(r'//[^\n]*|/\*.*?\*/', '', path.read_text(), flags=re.DOTALL) for path in files
    )
    if status_code == 'ERROR':
        assert re.search(r'return[^;]*"Failed"', text), (
            'Outcomes: engine errors use the Failed display word'
        )
        return
    assert re.search(
        r'case\s+(?:edi::)?FitStatus::'
        + status_code
        + r'\s*:[^;{}]*[\"\']'
        + re.escape(word)
        + r'[\"\']',
        text,
    ), 'Outcomes: each engine exit reason must map to the owner-approved display word'


def test_result_row_and_status_summary_share_outcome_presentation():
    text = source('src/fit_view_model.cpp')
    assert not re.search(r'result\.success\s*\?\s*(?:QStringLiteral|tr)\(', text), (
        'Outcomes: the results row must use the full outcome rather than a success/failure split'
    )
    dialog = source('qml/Components/FitResultsDialog.qml')
    bar = source('qml/Components/StatusBar.qml')
    assert not re.search(r'row\.icon\s*===\s*"check-circle"\s*\?', dialog), (
        'Outcomes: amber and grey outcomes must retain their own colour in the results row'
    )
    assert not re.search(r'font\.underline:\s*true', dialog + bar), (
        'Outcomes: clickable summaries highlight on hover without an underline'
    )


def test_status_fit_area_binds_live_progress_and_terminal_summary():
    text = source('qml/Components/StatusBar.qml')
    models = source('src/fit_view_model.hpp') + source('src/fit_view_model.cpp')
    assert re.search(r'ProgressBar|FitProgress', text), (
        'Status bar: single and scan runs must share a progress area'
    )
    for fact in ('elapsed', 'eta', 'fail', 'percent'):
        assert re.search(fact, text + models, re.IGNORECASE), (
            'Status bar: live progress must carry time, ETA, failures and completion fraction'
        )
    assert ' · ' in text + models, 'Status bar: facts use the same spaced middle-dot separator'
    assert not re.search(r'onClicked:\s*[^\n]*\.(?:cancel|stop)\(', text), (
        'Status bar: stopping stays in the Analysis group'
    )
    assert re.search(r'(?:summary|running)', text, re.IGNORECASE), (
        'Status bar: running details and retained summary must be distinguished'
    )


def test_create_experiment_is_enabled_and_routes_to_view_model():
    text = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert 'Create experiment' in text and 'Load experiment' in text, (
        'Creating experiments: the two footer actions use the owner-approved names'
    )
    assert re.search(r'onClicked:\s*[^\n]*\.(?:create|append|add)Experiment\(', text), (
        'Creating experiments: the action must call the project view model'
    )
    header = source('src/project_view_model.hpp')
    assert re.search(r'Q_INVOKABLE\s+\w+\s+(?:create|append|add)Experiment\(', header), (
        'Creating experiments: creation must enter the project edit boundary'
    )


def test_type_selectors_live_in_explorer_and_follow_selected_row():
    explorer = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert 'ExperimentTypeGroup' in explorer, (
        'Experiment type: selectors belong below the explorer table and above its buttons'
    )
    assert explorer.index('ExperimentTypeGroup') < explorer.index('Create experiment'), (
        'Experiment type: the explorer must place selectors before its footer actions'
    )
    component = block(explorer, 'ExperimentTypeGroup')
    assert 'currentExperiment' in component, (
        'Experiment type: selectors show the experiment selected in the table'
    )
    page = source('qml/Pages/Experiment/ExperimentPage.qml')
    assert '"experiment_type":' not in page, (
        'Experiment type: moving the group must remove the previous sidebar instance'
    )


@pytest.mark.parametrize('axis', ['sampleForm', 'beamMode', 'radiationProbe', 'scatteringType'])
def test_data_free_experiment_type_has_a_write_boundary(axis):
    header = source('src/experiment_view_model.hpp')
    assert re.search(r'Q_PROPERTY\([^)]*\b' + axis + r'\b[^)]*\bWRITE\b', header), (
        'Experiment type: each supported axis is editable before measured data arrives'
    )
    body = source('src/experiment_view_model.cpp')
    assert re.search(r'calculation_only|hasMeasuredData|hasData|data\.has_value|data->', body), (
        'Experiment type: its write boundary must distinguish simulation and measured data'
    )


def test_disabled_placeholders_and_load_data_are_present():
    types = source('qml/Pages/Experiment/ExperimentTypeGroup.qml')
    assert r'1D' in types and r'None' in types, (
        'Experiment type: dimensionality and polarization have their disabled placeholders'
    )
    assert re.search(r'Neutron|[Nn]eutron', types), (
        'Experiment type: polarization is only shown for neutron experiments'
    )
    explorer = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert 'Load data…' in explorer, (
        'Creating experiments: a data-free row shows the future Load data action'
    )
    assert re.search(r'enabled:\s*false', explorer), (
        'Creating experiments: plain-data loading stays disabled until it is implemented'
    )


@pytest.mark.parametrize('field', ['minimum', 'maximum', 'step'])
def test_simulation_range_fields_have_live_write_bindings(field):
    header = source('src/pattern_model.hpp')
    assert re.search(r'Q_PROPERTY\([^)]*\b' + field + r'\b[^)]*WRITE', header), (
        'Simulation range: start, end and step must have view-model write boundaries'
    )
    qml = source('qml/Pages/Experiment/MeasuredRangeGroup.qml')
    control = item(qml, 'range.' + field)
    assert not re.search(r'editable:\s*false', control), (
        'Simulation range: editing is enabled for simulations and locked for measured data'
    )
    assert re.search(r'onCommitted:|onValueChanged:', control), (
        'Simulation range: entering a value must write the simulation grid'
    )


def test_sidebar_tabs_have_requested_names():
    text = source('qml/Components/WorkflowPage.qml')
    labels = re.findall(r'text:\s*qsTr\("([^\"]+)"\)', text)
    assert labels[:3] == ['Main', 'Extra', 'Text'], (
        'Sidebar: the tab labels must read Main, Extra and Text in that order'
    )


def test_explorer_fit_column_has_outcome_model_roles():
    qml = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert 'qsTr("Fit")' in qml, 'Fit lists: every project type has an explorer Fit column'
    cpp = source('src/project_view_model.cpp')
    assert re.search(r'fit(?:Outcome|Status|Icon)|fit_(?:outcome|status|icon)', cpp), (
        'Fit lists: explorer rows must derive their outcomes from the model'
    )


@pytest.mark.parametrize('component', ['AliasesGroup', 'ConstraintsGroup'])
def test_long_parameter_pickers_use_shared_search_component(component):
    qml = source(f'qml/Pages/Analysis/{component}.qml')
    used = set(re.findall(r'\b(\w*(?:Search|Combo)\w*)\s*\{', qml))
    assert used - {'ComboBox'}, (
        'Search: alias and constraint parameter pickers must use the shared searchable popup'
    )
    matches = [
        path.read_text() for path in (APP / 'qml/Components').glob('*.qml') if path.stem in used
    ]
    assert any(
        re.search(r'>\s*10\b', text)
        and re.search(r'TextField|SearchField', text)
        and re.search(r'indexOf|includes', text)
        for text in matches
    ), 'Search: the shared popup shows search strictly above ten and matches substrings'
