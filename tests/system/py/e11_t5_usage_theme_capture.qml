// Nonvisual TEST-owned witness, no copied formatter or canonical state.
import QtQuick
import QtQml
QtObject {
    id: capture
    objectName: "e11.usageThemeCapture"
    property var button: null
    property var label: null
    property var original: null
    property var colors: null
    property int originalTheme: -1
    property int changes: 0
    property Connections connection: Connections {
        target: capture.label
        function onColorChanged() { ++capture.changes; }
    }
}
