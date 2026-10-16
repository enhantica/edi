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
    AssistantMessage {
        id: row
        objectName: "markdown.row"
        width: 640
        height: implicitHeight
        kind: "assistant"
        text: "Initial original row"
    }
    function setRow(kind, original, dark) {
        EaStyle.Colors.theme = dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        row.kind = kind;
        row.text = original;
    }
}
