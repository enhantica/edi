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
    for state in ('Free', 'Fixed', 'Mixed'):
        assert 'qsTr("' + state + '")' in source, (
            'The lean free-header menu must retain each state label beside its count'
        )
    assert 'choosable: false' in source or 'checkable: false' in source, (
        'Mixed remains a displayed state that cannot be chosen'
    )

    # The dropdown amendment replaces the shared popup/legend height rule.
    state_row = block(source, 'component StateRow:')
    combo = (ROOT / 'app/qml/Components/SearchableComboBox.qml').read_text()
    filter_row = block(group, 'delegate: EaElements.MenuItem {')
    popup_height = property_value(state_row, 'height')
    assert popup_height == property_value(filter_row, 'height'), (
        'Popup radio rows must use the same row height as the category filter list'
    )
    assert 'EaStyle.Sizes.comboBoxHeight' in combo, (
        'The shared combobox list renderer must retain the filter dropdown row height'
    )
    legend = (ROOT / 'app/qml/Components/ChartLegend.qml').read_text()
    legend_height = property_value(block(legend, 'delegate: IconLine {'), 'height')
    assert re.fullmatch(r'AppSizes\.\w+', legend_height), (
        'Both legends must retain one shared app spacing value after the popup amendment'
    )
    sizes = (ROOT / 'app/qml/Style/AppSizes.qml').read_text()
    token = legend_height.split('.')[-1]
    assert re.search(r'property\s+real\s+' + re.escape(token) + r'\s*:', sizes), (
        'Shared structure and pattern legend spacing must remain declared once in AppSizes'
    )
    assert 'qsTr("· all %1").arg(menu.shown.length)' in source, (
        'Free and Fixed must display a middle dot followed by their complete target count'
    )
    assert 'qsTr("· %1 free · %2 fixed").arg(menu.freeCount).arg(menu.fixedCount)' in source, (
        'Mixed must display a middle dot before each exact free and fixed count'
    )
