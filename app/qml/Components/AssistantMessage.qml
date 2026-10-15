// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
    id: row
    required property string kind
    required property string text
    property var payload: ({})
    property string status: ""
    color: "transparent"
    implicitHeight: content.implicitHeight + (kind === "user" ? AppSizes.unit * 1.5 : AppSizes.unit * 0.5)
    TextMetrics {
        id: userTextMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: row.kind === "user" ? row.text : ""
    }
    Rectangle {
        id: bubble
        x: row.kind === "user" ? row.width - width : 0
        width: row.kind === "user" ? Math.min(row.width - AppSizes.unit, Math.max(AppSizes.unit * 3, userTextMetrics.advanceWidth + AppSizes.unit * 2)) : row.width
        height: row.implicitHeight
        color: row.kind === "user" ? EaStyle.Colors.contentBackground : "transparent"
        radius: row.kind === "user" ? AppSizes.unit * 0.75 : 0
    }
    Column {
        id: content
        x: bubble.x + (row.kind === "user" ? AppSizes.unit : 0)
        y: row.kind === "user" ? AppSizes.unit * 0.75 : AppSizes.unit * 0.25
        width: bubble.width - (row.kind === "user" ? AppSizes.unit * 2 : 0)
        spacing: AppSizes.unit * 0.4
        EaElements.Label {
            visible: row.kind !== "user" && row.kind !== "assistant"
            text: qsTr("Activity")
            font.bold: true
        }
        EaElements.Label {
            visible: row.kind !== "user" && row.kind !== "assistant" && row.status.length > 0
            text: row.status
            textFormat: Text.PlainText
        }
        TextEdit {
            width: parent.width
            text: row.text
            readOnly: true
            selectByMouse: true
            persistentSelection: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.Wrap
            color: EaStyle.Colors.themeForeground
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }
        EaElements.Button {
            id: disclosure
            visible: row.kind !== "assistant" && row.kind !== "user" && Object.keys(row.payload || {}).length > 0
            checkable: true
            text: checked ? qsTr("Hide details") : qsTr("Inspect details")
        }
        TextEdit {
            width: parent.width
            visible: disclosure.visible && disclosure.checked
            text: disclosure.checked ? JSON.stringify(row.payload, null, 2) : ""
            readOnly: true
            selectByMouse: true
            persistentSelection: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.WrapAnywhere
            color: EaStyle.Colors.themeForeground
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
        }
    }
}
