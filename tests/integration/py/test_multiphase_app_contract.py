"""Runnable source contracts while the Qt interaction tiers are switched off."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def code(path):
    text = (ROOT / path).read_text()
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)


def test_shared_block_selector_has_bounded_plain_arrow_steps_and_file_labels():
    selector = code('app/qml/Components/BlockSelector.qml')
    model = code('app/src/project_view_model.cpp')
    assert '▲' in selector and '▼' in selector, (
        'The shared selector needs the plain up and down arrows'
    )
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
        'fileName' in selector + model or 'filename' in selector + model
    ), 'Selector labels must combine datablock and file names'
    for path in (
        'app/qml/Pages/Analysis/ExperimentSelectorGroup.qml',
        'app/qml/Pages/Experiment/ExperimentPage.qml',
        'app/qml/Pages/Structure/StructurePage.qml',
    ):
        assert 'BlockSelector' in code(path), (
            'All three pages must retain the shared browsing control'
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
        r'onClicked[^\n]*(?:add|create)|onTriggered[^\n]*(?:add|create)', text, re.IGNORECASE
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
