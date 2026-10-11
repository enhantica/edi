"""Declaration supplement; filter, input, geometry and undo use the Qt actor."""

from pathlib import Path

from tests.integration.py.test_scan_app_contract import block, item, property_value

ROOT = Path(__file__).resolve().parents[3]


def test_analysis_free_header_declares_the_owner_radio_popup():
    group = (ROOT / 'app/qml/Pages/Analysis/ParametersGroup.qml').read_text()
    popup = ROOT / 'app/qml/Pages/Analysis/FreeHeaderMenu.qml'
    assert popup.is_file(), 'The Analysis free-header popup must be declared in the app module'
    source = popup.read_text()
    header = item(group, 'parameters.freeHeader')
    assert 'Qt.RightButton' not in header and 'TapHandler {' in header, (
        'The free header must use the normal left-click tap action'
    )
    assert '.popup()' in property_value(block(header, 'TapHandler {'), 'onTapped'), (
        'The free header actual tap must open its radio popup'
    )
    assert 'Qt.PointingHandCursor' in header and 'themeAccent' in property_value(
        header, 'color'
    ), 'The free header must declare the hand cursor and accent hover feedback'
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
