"""Declaration checks supplement the app runners while those runners are disabled."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'app/qml'


def text(path):
    return (QML / path).read_text()


def test_correlations_follows_the_existing_analysis_tabs():
    source = text('Pages/Analysis/AnalysisPage.qml')
    positions = [
        source.find(f'qsTr("{name}")') for name in ('Pattern', 'Correlations', 'Evolution')
    ]
    assert all(position >= 0 for position in positions), (
        'Analysis must offer Pattern, Evolution and Correlations'
    )
    assert positions == sorted(positions), 'Correlations must sit between Pattern and Evolution'
    assert 'CorrelationChart {' in source, (
        'The Correlations tab must instantiate the production correlation chart'
    )
    assert 'currentExperimentIndex' in source and 'blockSelectorShown: true' in source, (
        'Correlations must share Analysis experiment selection with Pattern and Evolution'
    )


@pytest.mark.parametrize(
    ('property_name', 'needs_experiment'),
    [
        ('experimentPageEnabled', False),
        ('analysisPageEnabled', True),
        ('reportPageEnabled', True),
    ],
)
def test_workflow_pages_follow_structure_and_experiment_presence(property_name, needs_experiment):
    source = text('Globals/AppState.qml')
    match = re.search(r'property bool ' + property_name + r':\s*([^\n]+)', source)
    assert match, 'The app must declare an enabled predicate for each dependent workflow page'
    cases = []
    for structures, experiments in ((0, 0), (0, 1), (1, 0), (1, 1)):
        project = {
            'structures': {'count': structures},
            'experiments': {'count': experiments},
            'structureCount': structures,
            'experimentCount': experiments,
        }
        script = 'const Session=' + json.dumps({'hasProject': True, 'project': project}) + ';'
        script += (
            'const AppState={reached:5,Page:{Home:0,Project:1,Structure:2,'
            'Experiment:3,Analysis:4,Report:5}}; const reached=5;'
        )
        script += 'process.stdout.write(JSON.stringify(Boolean(' + match[1] + ')));'
        outcome = subprocess.run(
            ['node', '-e', script], capture_output=True, text=True, timeout=3, check=False
        )
        assert outcome.returncode == 0, (
            'The production enabled predicate must evaluate with the declared project counts'
        )
        cases.append(json.loads(outcome.stdout))
    expected = [False, False, not needs_experiment, True]
    assert cases == expected, (
        'Removing the final structure or required experiment must disable the workflow page'
    )


def test_create_project_passes_the_chosen_location_to_the_session():
    source = text('Pages/Project/GetStartedGroup.qml')
    accepted = re.search(r'onAccepted:\s*([^\n]+)', source)
    assert accepted and 'projectLocation' in accepted[1], (
        'Create project must use the location chosen in its dialog'
    )


def test_supported_only_selectors_are_disabled_and_explain_the_reason():
    source = text('Pages/Experiment/ExperimentTypeGroup.qml')
    for identity in ('sampleForm', 'scatteringType'):
        marker = source.index('id: ' + identity)
        end = source.find('EaElements.ParamComboBox', marker)
        section = source[marker : end if end >= 0 else len(source)]
        assert re.search(r'enabled:\s*false\b', section), (
            'Sample form and scattering type must be disabled while only one is supported'
        )
        explains = re.search(r'only|support|available', section, re.IGNORECASE)
        assert 'ToolTip' in section and explains, (
            'Each supported-only selector must explain its disabled state in a tooltip'
        )


def test_atom_site_position_column_uses_a_choice_with_coordinates():
    source = text('Pages/Structure/AtomSitesGroup.qml')
    assert 'qsTr("WP")' in source and 'qsTr("WL")' not in source, (
        'The atom position column must be labelled WP'
    )
    assert re.search(r'(?:ComboBox|PositionCell)\s*\{', source), (
        'Wyckoff positions must be chosen through a combobox'
    )
    model = (ROOT / 'app/src/structure_view_model.cpp').read_text()
    coordinates = re.search(r'coordinate|position|xyz', model, re.IGNORECASE)
    assert 'multiplicity' in model and coordinates, (
        'Position choices must include multiplicity, letter and catalogue coordinates'
    )


def test_experiment_data_header_and_button_are_declared():
    source = text('Pages/Experiment/ExperimentsGroup.qml')
    assert 'qsTr("Data file")' in source, (
        'The experiments table must label its data column Data file'
    )
    assert re.search(
        r'(?:Button|DataFileCell)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*qsTr\("Load data…"\)',
        source,
        re.DOTALL,
    ), 'Loading measured data must use a button rather than a clickable text label'


def test_diagnostics_uses_a_button_with_a_declared_combobox_width():
    source = text('Components/AppPreferencesDialog.qml')
    match = re.search(
        r'(?:EaElements\.)?Button\s*\{\s*objectName:\s*"preferences.diagnostics"([^}]+)', source
    )
    assert match and 'qsTr("Show")' in match[1], 'Diagnostics Show must be an actual button'
    assert re.search(r'(?:implicitWidth|width|Layout.preferredWidth):', match[1]), (
        'The diagnostics button must explicitly take the Logging level combobox width'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_each_coefficient_background_has_a_table_layout(kind):
    source = text('Pages/Experiment/BackgroundGroup.qml')
    assert re.search(r'"' + kind + r'"\s*:', source), (
        'Polynomial and Chebyshev backgrounds must each select a coefficient layout'
    )
    assert re.search(r'coef|coefficient', source, re.IGNORECASE), (
        'Coefficient backgrounds must expose their coefficient values'
    )
    assert re.search(r'append\(', source) and re.search(r'remove\(', source), (
        'Coefficient tables must offer the same append and remove actions as line-segment points'
    )


def test_background_type_selector_applies_the_choice():
    source = text('Pages/Experiment/BackgroundGroup.qml')
    selector = source[source.index('objectName: "background.type"') :]
    selector = selector[: selector.index('\n    }')]
    assert re.search(r'on(?:Selected|Activated|Chosen|Committed|TokenChanged):', selector), (
        'The background type selector must apply the chosen value'
    )
    header = (ROOT / 'app/src/experiment_view_model.hpp').read_text()
    declaration = re.search(r'Q_PROPERTY\(QString backgroundType[^\n]+', header)
    assert declaration and 'NOTIFY' in declaration[0] and 'CONSTANT' not in declaration[0], (
        'The selected background type must notify the view when it changes'
    )


def test_background_switch_requires_confirmation_before_discarding_rows():
    source = text('Pages/Experiment/BackgroundGroup.qml')
    match = re.search(
        r'function chooseType\(token(?:: string)?\)\s*\{(.*?)\n    \}', source, re.DOTALL
    )
    assert match, 'Background replacement must distinguish empty models from models holding rows'
    script = (
        'const experiment={backgroundType:"polynomial"};'
        'const points={count:0}; const terms={count:3};'
        'const typeQuestion={opened:false,open(){this.opened=true}};'
        'function chooseType(token){' + match[1] + '}'
        'chooseType("chebyshev");'
        'process.stdout.write(JSON.stringify([experiment.backgroundType,'
        'typeQuestion.opened,typeQuestion.token,typeQuestion.rows]));'
    )
    outcome = subprocess.run(
        ['node', '-e', script], capture_output=True, text=True, timeout=3, check=False
    )
    assert outcome.returncode == 0, 'The production switch must evaluate before any mutation'
    assert json.loads(outcome.stdout) == ['polynomial', True, 'chebyshev', 3], (
        'Choosing another type with rows must leave the old model intact pending confirmation'
    )
    assert 'Dialog.Cancel' in source and 'onAccepted:' in source, (
        'Replacing background rows must permit cancellation and require explicit acceptance'
    )
    assert re.search(r'qsTr\("[^"\n]*(?:empty|removed)', source), (
        'The switch question must tell the user that the old rows are removed'
    )


def test_coefficient_editing_and_constants_have_writable_controls():
    source = text('Pages/Experiment/BackgroundGroup.qml')
    for identity in ('origin', 'xMin', 'xMax', 'order', 'coef'):
        assert re.search(r'background\.' + identity + r'(?:\.\$\{[^}]+\})?["`]', source), (
            'Coefficient backgrounds must expose editable constants, order and coefficients'
        )
    assert 'setOrder(' in source and 'ParameterCell {' in source, (
        'Order must commit to the model and coefficient must retain parameter editing parity'
    )
