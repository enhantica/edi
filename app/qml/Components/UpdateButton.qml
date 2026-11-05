// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

EaElements.Button {
    id: button
    property var updates: DesktopUpdates
    objectName: "statusBar.button.update"
    visible: updates.available
    enabled: updates.managed
    text: qsTr("Update")
    ToolTip.text: qsTr("Update to EasyDiffraction %1").arg(updates.availableVersion)
    Accessible.name: ToolTip.text
    readonly property color ink: EaStyle.Colors.isDarkPalette ? "#ff9b9b" : "#b52a2a"
    contentItem: EaElements.Label {
        text: button.text
        font: button.font
        color: button.ink
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: height / 2
        color: EaStyle.Colors.isDarkPalette ? (button.hovered ? "#633333" : "#492c2c") : (button.hovered ? "#fbd6d6" : "#fde9e9")
        border.color: EaStyle.Colors.isDarkPalette ? "#c86666" : "#d95555"
        border.width: button.visualFocus ? 2 : 1
    }
}
