// Independent literal row data in the actual production presentation component.
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import edi.app

ApplicationWindow {
    id: window
    width: 720
    height: 600
    visible: true
    // Actual AssistantPanel assistantSheet is opaque in this sidebar role.
    color: EaStyle.Colors.appBarBackground
    property var reportEvents: []
    Connections {
        target: row
        ignoreUnknownSignals: true
        function onReportRequested(sourceRowId, link) {
            window.reportEvents = window.reportEvents.concat([{row_id: sourceRowId, href: link}]);
        }
    }
    AssistantMessage {
        id: row
        objectName: "markdown.row"
        width: 640
        height: implicitHeight
        kind: "assistant"
        text: "Initial original row"
    }
    function setReportRow(sourceRowId, original) {
        reportEvents = [];
        row.rowId = sourceRowId;
        row.kind = "assistant";
        row.status = "completed";
        row.text = original;
    }
    function setActivityRow(original) {
        row.rowId = original.id;
        row.kind = original.kind;
        row.status = original.status;
        row.payload = original.payload;
        row.text = original.text;
    }
    function setRow(kind, original, dark) {
        EaStyle.Colors.theme = dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        row.kind = kind;
        row.text = original;
    }
}
