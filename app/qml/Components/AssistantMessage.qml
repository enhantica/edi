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
    color: kind === "user" ? EaStyle.Colors.contentBackground : EaStyle.Colors.appBarBackground
    radius: AppSizes.unit * 0.5
    implicitHeight: content.implicitHeight + AppSizes.unit * 1.5
    Column {
        id: content
        x: AppSizes.unit
        y: AppSizes.unit * 0.75
        width: parent.width - AppSizes.unit * 2
        spacing: AppSizes.unit * 0.4
        EaElements.Label {
            text: row.kind === "user" ? qsTr("You") : row.kind === "assistant" ? qsTr("Assistant") : qsTr("Activity")
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
            text: visible ? JSON.stringify(row.payload, null, 2) : ""
            readOnly: true
            selectByMouse: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.WrapAnywhere
            color: EaStyle.Colors.themeForeground
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
        }
    }
}
