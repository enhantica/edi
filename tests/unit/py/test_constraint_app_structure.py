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


def test_cwl_width_row_combines_uvw_xy_and_keeps_tof_lorentzian_separate():
    # Previously U V W and X Y occupied separate rows; TCH now shares one width row.
    # TOF Lorentzian gamma, size and strain still use their separate family row.
    text = source('src/experiment_view_model.cpp')
    match = re.search(r'int peak_family\([^)]*\)\s*\{(.*?)\n\}', text, re.DOTALL)
    assert match, 'the profile row classifier must remain inspectable by the static layout gate'
    body = match.group(1)
    width = re.search(r'if\s*\(([^\n{};]+)\)\s*\{\s*return\s+1\s*;', body)
    assert width and 'starts("broad_gauss_")' in width.group(1), (
        'U, V and W must share the profile width row'
    )
    for name in ('broad_lorentz_x', 'broad_lorentz_y'):
        assert re.search(r'name\s*==\s*"' + name + '"', width.group(1)), (
            'both TCH X and Y must join U V W in the profile width row'
        )
    assert 'starts("broad_lorentz_")' not in width.group(1), (
        'the shared CWL width row must not absorb all TOF Lorentzian fields'
    )
    assert re.search(r'if\s*\([^{};]*"broad_lorentz_"[^{};]*\)\s*\{\s*return\s+2\s*;', body), (
        'TOF Lorentzian gamma, size and strain must retain their separate row'
    )
    grid = source('qml/Components/ParameterGrid.qml')
    columns = re.search(r'property int maxColumns:\s*(\d+)', grid)
    assert columns and int(columns.group(1)) >= 5, (
        'one profile width row must have room for all five U V W X Y fields'
    )
    peak = source('qml/Pages/Experiment/PeakGroup.qml')
    assert 'peakGaussian' in peak and 'peakLorentzian' in peak, (
        'the peak group must consume the shared width row and the TOF Lorentzian row'
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
    # Relation models now delegate through the undo-aware relation entry, which uses the same door.
    relations = text.split('AnalysisViewModel::AnalysisViewModel', 1)[0]
    edits = re.findall(r'edi::Edit::\w+\(', relations)
    routed = re.findall(r'editor_\.apply_relation_edit\(edi::Edit::\w+\(', relations)
    assert edits and len(routed) == len(edits), (
        'every relation edit must enter the typed relation route without a direct-write escape'
    )
    project = source('src/project_view_model.cpp')
    route = re.search(
        r'QString ProjectViewModel::apply_relation_edit\([^)]*\)\s*{(.*?)\n}', project, re.DOTALL
    )
    assert route and 'apply(change, true)' in route.group(1), (
        'the relation route must delegate to the common structural edit door'
    )
    door = re.search(r'QString ProjectViewModel::apply\([^)]*\)\s*{(.*?)\n}', project, re.DOTALL)
    assert door and 'preview_->apply(change)' in door.group(1), (
        'the common edit door must submit the typed change through the preview publisher'
    )


def test_analysis_text_uses_the_saved_core_block_and_invalidates_after_edits():
    analysis = source('src/analysis_view_model.cpp')
    assert re.search(r'BlockText\([^;]*saved\("analysis/analysis\.edi"\)', analysis), (
        'the Analysis Text tab must read the canonical saved analysis block'
    )
    project = source('src/project_view_model.cpp')
    # Saving uses the template when a dataset is shown; ordinary projects save themselves.
    assert 'edi::project_edi_files(scanTemplateOrModel())' in project, (
        'the text provider must use the canonical writer on the same template or model as saving'
    )
    assert (
        'edi::save_project_as(*scan_template_' in project
        and 'edi::save_project_as(*project_' in project
    ), 'project saving must retain both the scan-template and ordinary-model canonical routes'
    assert re.search(r'for \(const auto& \[path, body\] : savedFiles\(\)\)', project), (
        'each text block must come from the shared saved-file snapshot'
    )
    assert 'analysis_->text()->invalidate()' in project, (
        'editing a relation must invalidate shown analysis text instead of displaying stale loops'
    )
