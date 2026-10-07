"""Runnable source contracts while the Qt interaction tiers are switched off."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def code(path):
    text = (ROOT / path).read_text()
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)


def test_shared_block_selector_has_bounded_square_icon_steps_and_file_labels():
    selector = code('app/qml/Components/BlockSelector.qml')
    model = code('app/src/project_view_model.cpp')
    assert 'arrow-circle-up' in selector and 'arrow-circle-down' in selector, (
        'The shared selector must use the circled arrow style of Continue'
    )
    buttons = re.findall(r'EaElements.SideBarButton\s*\{(.*?)\n    \}', selector, re.DOTALL)
    assert len(buttons) == 2, 'Both steps must use the regular sidebar button component'
    assert all(
        'width: EaStyle.Sizes.comboBoxHeight' in button
        and 'height: EaStyle.Sizes.comboBoxHeight' in button
        for button in buttons
    ), 'Both selector buttons must be square at the regular combobox height'
    assert 'spacing: AppSizes.toolbarSpacing' in selector, (
        'The compact main-area selector must use the shared toolbar-group spacing'
    )
    assert all(
        label in selector
        for label in (
            'Previous experiment',
            'Previous structure',
            'Next experiment',
            'Next structure',
        )
    ), 'Both stepping controls must retain tooltips for each browsed block kind'
    assert len(re.findall(r'enabled\s*:', selector)) >= 2, (
        'Both stepping controls must bind their enabled state'
    )
    assert re.search(r'blockIndex\s*>\s*0|blockIndex\s*>=\s*1', selector), (
        'The previous step must be disabled at the first block'
    )
    assert re.search(r'blockIndex\s*<[^;\n]*(?:count|length|rowCount)', selector), (
        'The next step must be disabled at the last block'
    )
    assert 'blockActivated' in selector, (
        'Arrows and combobox picks must use the same selection signal'
    )
    assert '·' in selector + model and (
        'fileName' in selector + model
        or 'filename' in selector + model
        or 'key + QStringLiteral(".edi")' in model
    ), 'Selector labels must combine datablock and file names'
    placement = code('app/qml/Components/MainAreaBlockSelector.qml')
    assert 'BlockSelector {' in placement and (
        'onBlockActivated: index => placement.blockActivated(index)' in placement
    ), 'The main-area selector must forward choices from the shared block control'
    workflow = code('app/qml/Components/WorkflowPage.qml')
    assert (
        'MainAreaBlockSelector {' in workflow and 'visible: page.blockSelectorShown' in workflow
    ), 'The shared workflow main area must host the enabled block selector'
    assert all(
        binding in workflow
        for binding in (
            'blocks: page.blocks',
            'blockKind: page.blockKind',
            'blockIndex: page.blockIndex',
            'onBlockActivated: index => page.blockActivated(index)',
        )
    ), 'The shared selector must forward the page collection, selection and activation'
    for name, kind, collection in (
        ('Experiment', 'Experiment', 'experiments'),
        ('Structure', 'Structure', 'structures'),
        ('Analysis', 'Experiment', 'experiments'),
    ):
        page = code(f'app/qml/Pages/{name}/{name}Page.qml')
        assert 'WorkflowPage {' in page and 'blockSelectorShown: true' in page, (
            'All three browsing pages must enable the shared workflow selector'
        )
        assert f'blocks: project ? project.{collection} : null' in page, (
            'Each browsing page must supply its own complete block collection'
        )
        assert f'onBlockActivated: index => page.project.current{kind}Index = index' in page, (
            'Each browsing page must apply shared selector activation to its own selection'
        )


def test_linked_structure_rows_use_available_names_and_add_remove_disable_actions():
    text = code('app/qml/Pages/Experiment/LinkedStructureGroup.qml')
    assert 'ComboBox' in text or 'ComboBoxCell' in text, (
        'A linked phase name must be picked from available structure names'
    )
    assert not re.search(r'model\s*:\s*experiment\s*\?\s*1\s*:\s*0', text), (
        'The linked-phase table must bind the complete collection'
    )
    assert re.search(
        r'onClicked[^\n]*(?:add|create|append)|onTriggered[^\n]*(?:add|create|append)',
        text,
        re.IGNORECASE,
    ), 'Linked phases need a live add action'
    assert re.search(r'onClicked[^\n]*remove|onTriggered[^\n]*remove', text, re.IGNORECASE), (
        'Linked phases need a live remove action'
    )
    assert re.search(
        r'(?:disable|enabled|isEnabled).*?(?:onClicked|onToggled)|(?:onClicked|onToggled).*?(?:disable|enabled|isEnabled)',
        text,
        re.DOTALL,
    ), 'Disabling a linked phase must be an actionable persisted model edit'


def test_structure_loading_is_not_capped_at_one_and_chart_retains_phase_identity():
    header = code('app/src/project_view_model.hpp')
    assert not re.search(r'canLoadStructure\([^)]*\)[^{]*\{[^}]*structures\.empty\(\)', header), (
        'The app must allow adding a second structure to an open project'
    )
    table = code('app/qml/Pages/Structure/StructuresGroup.qml')
    assert 'project.structures' in table and 'currentStructureIndex' in table, (
        'The Structure page must show all structures and select the viewed one'
    )
    source = code('core/src/presentation.cpp')
    assert 'refln.structure_id' in source and 'source.phases.push_back' in source, (
        'Bragg capture must retain each calculated phase identity'
    )
    assert 'for (const PatternSource::Phase& phase : source.phases)' in source, (
        'Both Bragg rows must flow through the existing phase renderer'
    )
    assert 'phase.label' in source and 'phase.place' in source, (
        'Each phase needs its own hover label and stable colour place'
    )
