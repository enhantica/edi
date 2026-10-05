"""Static app wiring checks retained while native app tests are disabled."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / 'app'


def source(path):
    text = (APP / path).read_text()
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.DOTALL)


def test_excluded_regions_are_in_the_basic_category_tier():
    text = source('src/category_list_model.cpp')
    assert re.search(r'QStringLiteral\("excluded_region"\)\s*,\s*\{\s*T::Basic\b', text), (
        'excluded regions must remain on the Experiment Basic tab'
    )
    page = source('qml/Pages/Experiment/ExperimentPage.qml')
    assert '"excluded_region": excludedRegionsContent' in page, (
        'the Basic category must retain its live excluded-regions editor'
    )


def test_cwl_gaussian_and_lorentzian_coefficients_have_distinct_rows():
    text = source('src/experiment_view_model.cpp')
    match = re.search(r'int peak_family\([^)]*\)\s*\{(.*?)\n\}', text, re.DOTALL)
    assert match, 'the profile row classifier must remain inspectable by the static layout gate'
    body = match.group(1)
    gaussian = re.search(r'if\s*\((.*?)\)\s*\{\s*return\s+1\s*;', body, re.DOTALL)
    assert gaussian and 'broad_gauss_' in gaussian.group(1), (
        'U, V and W must share their Gaussian row'
    )
    assert 'broad_lorentz_' not in gaussian.group(1), (
        'X and Y must not be folded into the U V W row'
    )
    assert re.search(r'if\s*\([^)]*"broad_lorentz_"[^;]*return\s+2\s*;', body, re.DOTALL), (
        'X and Y must share their separate Lorentzian row'
    )
    grid = source('qml/Components/ParameterGrid.qml')
    assert re.search(r'property int maxColumns:\s*[3-9]', grid), (
        'one row must have room for all three U V W fields'
    )
    peak = source('qml/Pages/Experiment/PeakGroup.qml')
    assert 'peakGaussian' in peak and 'peakLorentzian' in peak, (
        'the peak group must consume both live family rows'
    )


@pytest.mark.parametrize(
    ('category', 'component', 'collection'),
    [('alias', 'AliasesGroup', 'aliases'), ('constraint', 'ConstraintsGroup', 'constraints')],
)
def test_analysis_groups_read_core_rows_without_preview_data(category, component, collection):
    page = source('qml/Pages/Analysis/AnalysisPage.qml')
    assert f'"{category}"' in page and component + ' {' in page, (
        'Analysis must attach each declared relation group to its category'
    )
    group = source(f'qml/Pages/Analysis/{component}.qml')
    assert f'analysis.{collection}' in group, (
        'a relation table must consume the live analysis model'
    )
    assert not re.search(r'\bmodel\s*:\s*\[', group), (
        'preview rows must not replace a shipped table model'
    )
    adapter = source('src/analysis_view_model.cpp')
    assert f'project_.{collection}' in adapter, (
        'the analysis row model must enumerate edi core declarations'
    )
    assert not re.search(r'rows\.append\(\s*\{\s*(?:nullptr|0)\s*,', adapter), (
        'sample rows must never be injected into shipped analysis models'
    )


def test_load_warnings_reach_the_app_message_model():
    session = source('src/session.cpp')
    assert re.search(r'edi::load_project\([^;]*warnings\.append', session, re.DOTALL), (
        'project loading must collect the core warning sink into app messages'
    )
    assert re.search(r'warnings_->setMessages\(warnings\)', session), (
        'the replacement project must publish collected warnings to the Messages model'
    )


def test_preview_projects_cannot_be_bundled_as_application_resources():
    for path in (ROOT / 'app').rglob('*'):
        if path.is_file() and path.suffix in {'.qml', '.qrc', '.cmake'}:
            assert 'constraint_samples' not in path.read_text(), (
                'temporary look-check projects must not enter shipped application resources'
            )
    cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    examples = re.search(r'set\(EDI_APP_OWN_EXAMPLES\s+([^)]*)\)', cmake)
    assert examples, 'the app example packaging list must be inspectable'
    assert not re.search(r'(?i)(?:look|preview|sample|demo)', examples.group(1)), (
        'look-check and preview projects must not enter the shipped example resource list'
    )
    assert 'constraint_samples' not in cmake, (
        'the application packaging list must exclude the temporary relation samples'
    )


@pytest.mark.parametrize('component', ['AliasesGroup', 'ConstraintsGroup'])
def test_relation_tables_expose_live_append_duplicate_and_remove_actions(component):
    group = source(f'qml/Pages/Analysis/{component}.qml')
    for action in ('append', 'duplicate', 'remove'):
        assert re.search(r'onClicked\s*:[^\n]*\.' + action + r'\(', group), (
            'each relation table action must call its live model operation'
        )
    assert 'Append new' in group and 'Duplicate selected' in group, (
        'relation editing must expose both requested footer actions'
    )
    if component == 'AliasesGroup':
        assert 'ComboBox' in group, 'alias rows must provide a suitable-parameter combobox'
    else:
        assert re.search(r'onClicked[^\n]*(?:enable|toggle|Enabled)', group), (
            'constraint rows must expose a live enable action before removal'
        )
        assert re.search(r'(?:enable|toggle|Enabled)[^}]*}.*\.remove\(', group, re.DOTALL), (
            'the enable action must appear before the remove action in each constraint row'
        )


def test_linked_structures_are_explicitly_moved_to_the_end_of_presentation_order():
    text = source('src/category_list_model.cpp')
    body = text.split('presentation_order(', 1)[1].split(
        'CategoryListModel::CategoryListModel', 1
    )[0]
    assert '"linked_structure"' in body, (
        'presentation ordering must explicitly handle Linked structures after all other groups'
    )
    assert re.search(r'\{\s*"excluded_region"\s*,\s*"linked_structure"\s*}', body), (
        'the final ordinary Basic group must precede Linked structures in presentation order'
    )


def test_alias_picker_uses_core_candidates_and_the_closed_edit_door():
    text = source('src/analysis_view_model.cpp')
    assert 'named_parameters(' in text, (
        'the alias picker must enumerate core-owned suitable parameter identities'
    )
    assert 'edi::Edit::' in text and re.search(r'\.apply\(|->apply\(', text), (
        'relation edits must enter the closed core edit door for publication'
    )


def test_analysis_text_uses_the_saved_core_block_and_invalidates_after_edits():
    analysis = source('src/analysis_view_model.cpp')
    assert re.search(r'BlockText\([^;]*saved\("analysis/analysis\.edi"\)', analysis), (
        'the Analysis Text tab must read the canonical saved analysis block'
    )
    project = source('src/project_view_model.cpp')
    assert 'edi::project_edi_files(*project_)' in project, (
        'the text provider must use the same core writer as a project save'
    )
    assert 'analysis_->text()->invalidate()' in project, (
        'editing a relation must invalidate shown analysis text instead of displaying stale loops'
    )
