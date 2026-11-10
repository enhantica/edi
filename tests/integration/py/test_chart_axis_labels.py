"""Pattern names are the axis-title names in the tooltip and legend too."""

from pathlib import Path

from tests.integration.py.test_scan_app_contract import block, javascript, property_value, source

ROOT = Path(__file__).resolve().parents[3]


def test_tooltip_and_legend_names_follow_the_axis_vocabulary():
    source = (ROOT / 'core/src/presentation.cpp').read_text()
    for old in ('Imeas', 'Icalc', 'Ibkg'):
        present = '"' + old in source or '(' + old in source
        assert not present, 'Chart labels must use meas, calc and bkg without the I prefix'
    for label in (
        'Measured (meas)',
        'Total calculated (calc)',
        'Background (bkg)',
        'Residual (meas \u2212 calc)',
    ):
        assert '"' + label + '"' in source, 'The legend uses the stated axis-title name: ' + label


def test_data_table_declares_named_component_columns():
    model = (ROOT / 'app/src/pattern_model.cpp').read_text()
    assert 'component_intensities_net' in model and '"componentIntensities"' in model, (
        'The data model exposes every structure contribution as a live point role'
    )
    qml = source('qml/Pages/Experiment/MeasuredRangeGroup.qml')
    header = block(qml, 'header:')
    repeater = block(header, 'Repeater {')
    label = block(repeater, 'EaComponents.ListViewLabel {')
    assert property_value(repeater, 'model') == 'table.componentNames', (
        'The data header iterates the ordered live structure names'
    )
    assert property_value(label, 'text') == 'modelData', (
        'Each component column is headed by its structure name'
    )
    rows = block(qml, 'delegate: TableRow {')
    repeater = block(rows, 'Repeater {')
    label = block(repeater, 'EaComponents.ListViewLabel {')
    expression = property_value(repeater, 'model')
    observed = javascript(
        'const table={componentNames:["alpha","beta","gamma"]};'
        'const row={};row.model={componentIntensities:[1.25,9.5,16.75]};'
        'const full=(' + expression + ');'
        'row.model.componentIntensities=[1.25,9.5];const partial=(' + expression + ');'
        'delete row.model.componentIntensities;const empty=(' + expression + ');'
        'console.log(JSON.stringify([full,partial,empty]));'
    )
    assert observed == [[1.25, 9.5, 16.75], [1.25, 9.5, None], [None, None, None]], (
        'Each point supplies its ordered structure intensities and retains empty cells '
        'for unavailable curves so rows stay aligned with every header'
    )
    assert (
        property_value(label, 'text')
        == 'group.shown("pd_calc.component_intensities_net", modelData)'
    ), 'Structure contributions use the same plain numeric display as other calculated columns'
    shown = block(qml, 'function shown(')
    observed = javascript(
        'let calls=[];const Session={display:(...args)=>{calls.push(args);return "sentinel"}};'
        + shown
        + ';console.log(JSON.stringify([shown("pd_calc.component_intensities_net",1.375),'
        'calls]));'
    )
    assert observed == ['sentinel', [['pd_calc.component_intensities_net', 1.375]]], (
        'Calculated cells must pass the exact dictionary uid and nontrivial value through '
        'the actual shared numeric display bridge'
    )
