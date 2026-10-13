"""Declaration supplement; filter, input, geometry and undo use the Qt actor."""

import re
from pathlib import Path

from tests.integration.py.test_scan_app_contract import block, item, property_value

ROOT = Path(__file__).resolve().parents[3]


def test_analysis_free_header_declares_the_owner_radio_popup():
    group = (ROOT / 'app/qml/Pages/Analysis/ParametersGroup.qml').read_text()
    popup = ROOT / 'app/qml/Pages/Analysis/FreeHeaderMenu.qml'
    assert popup.is_file(), 'The Analysis free-header popup must be declared in the app module'
    source = popup.read_text()
    header = item(group, 'parameters.freeHeader')
    assert 'Qt.RightButton' not in header, 'The free header must accept a normal left click'
    marker, signal = (
        ('TapHandler {', 'onTapped') if 'TapHandler {' in header else ('MouseArea {', 'onClicked')
    )
    assert '.popup()' in property_value(block(header, marker), signal), (
        'The free header actual left-click handler must open its radio popup'
    )
    color = property_value(header, 'color')
    if re.fullmatch(r'group\.\w+', color):
        color = property_value(group, color.split('.')[-1])
    assert 'Qt.PointingHandCursor' in header and 'themeAccent' in color, (
        'The free header must declare the hand cursor and accent hover feedback'
    )
    assert 'shown parameter' not in source and 'Applies to the rows' not in source, (
        'The lean free-header menu must omit the retired title and footer'
    )
    assert 'choosable: false' in source or 'checkable: false' in source, (
        'Mixed remains a displayed state that cannot be chosen'
    )
    state_row = block(source, 'component StateRow:')
    layout = block(source, 'Column {')
    assert (
        property_value(block(group, 'delegate: EaElements.MenuItem {'), 'height')
        == 'EaStyle.Sizes.comboBoxHeight'
    ), 'The actual category filter delegate must retain its shared dropdown pitch'
    row_height = property_value(state_row, 'implicitHeight')
    spacing = property_value(layout, 'spacing')
    assert row_height in spacing and 'EaStyle.Sizes.comboBoxHeight' in spacing, (
        'Popup text height and inter-row gap must derive the filter dropdown pitch'
    )
    assert (
        'EaStyle.Sizes.comboBoxHeight'
        in (ROOT / 'app/qml/Components/SearchableComboBox.qml').read_text()
    ), 'The shared combobox renderer must retain the filter dropdown row pitch'
    assert (
        property_value(layout, 'padding') and property_value(source, 'verticalPadding') == '0'
    ), 'The popup must declare one content margin with no extra vertical menu padding'
    for state in ('Free', 'Fixed'):
        assert f'qsTr("{state} · all %1").arg(menu.shown.length)' in source, (
            'Free and Fixed must each render one text with exact counts and single dot spacing'
        )
    assert (
        'qsTr("Mixed · %1 free · %2 fixed").arg(menu.freeCount).arg(menu.fixedCount)' in source
    ), 'Mixed must render one text with exact free/fixed counts and single dot spacing'
    legend = (ROOT / 'app/qml/Components/ChartLegend.qml').read_text()
    assert property_value(block(legend, 'delegate: IconLine {'), 'height') == 'legend.rowHeight', (
        'The actual legend delegate must apply the caller-selected row height'
    )
    assert property_value(legend, 'rowHeight') == 'AppSizes.legendRowHeight', (
        'Pattern legend rows must retain their original shared spacing default'
    )
    structure = (ROOT / 'app/qml/Components/StructureView.qml').read_text()
    assert (
        property_value(item(structure, 'structure.view.legend'), 'rowHeight')
        == 'AppSizes.structureLegendRowHeight'
    ), 'The actual structure legend must select its amended midpoint spacing'
    midpoint = re.sub(
        r'\s+',
        '',
        property_value(
            (ROOT / 'app/qml/Style/AppSizes.qml').read_text(), 'structureLegendRowHeight'
        ),
    )
    assert midpoint == 'Math.round((legendRowHeight+EaStyle.Sizes.comboBoxHeight)/2)', (
        'Structure spacing must derive halfway between pattern and dropdown spacing'
    )
