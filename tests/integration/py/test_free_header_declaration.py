"""Declaration supplement; actual filter, click and undo behavior is gated by Qt actors."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_analysis_free_header_declares_the_owner_radio_popup():
    group = (ROOT / 'app/qml/Pages/Analysis/ParametersGroup.qml').read_text()
    popup = ROOT / 'app/qml/Pages/Analysis/FreeHeaderMenu.qml'
    assert popup.is_file(), 'The Analysis free-header popup must be declared in the app module'
    source = popup.read_text()
    assert 'FreeHeaderMenu' in group and 'Qt.RightButton' in group, (
        'The parameter table free-header must route a real right click to its popup'
    )
    for declaration in [
        'Free ·',
        'shown parameter',
        'qsTr("Free")',
        'qsTr("Fixed")',
        'qsTr("Mixed")',
        'checkable: false',
        'Applies to the rows the filters show. Undo with Ctrl+Z.',
    ]:
        assert declaration in source, (
            'The free-header popup must declare each owner-approved state and instruction'
        )
