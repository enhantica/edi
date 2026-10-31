// Test-owned readonly signal witness, never a production Timer/clock setter.
import QtQuick
import QtQml
QtObject {
    id: capture
    objectName: "e11.usageClockCapture"
    property var timer: null
    property var dialog: null
    property var panel: null
    property var original: null
    property int count: 0
    property var events: []
    property Connections connection: Connections {
        target: capture.timer
        function onTriggered() { capture.record(); }
    }
    function record() {
        const current = Qt.isQtObject(panel) ? panel.assistant : null;
        const live = Qt.isQtObject(current), shown = Qt.isQtObject(dialog);
        events = events.concat([{at: Date.now(), owner: live && current === original,
            connected: live ? current.connected : null,
            visible: shown ? dialog.visible : null, opened: shown ? dialog.opened : null,
            clock: shown ? dialog.resetClock : null}]);
        ++count;
    }
}
