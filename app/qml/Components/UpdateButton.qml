// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import edi.app

FitStatusItem {
    id: button

    property var updates: DesktopUpdates
    readonly property color ink: EaStyle.Colors.isDarkPalette ? "#ff9b9b" : "#b52a2a"

    objectName: "statusBar.button.update"
    shown: updates.available
    clickable: updates.managed
    framed: true
    showKey: false
    valueText: qsTr("Update")
    valueColor: ink
    tintsOnHover: false
    frameColor: EaStyle.Colors.isDarkPalette ? "#492c2c" : "#fde9e9"
    frameHoverColor: EaStyle.Colors.isDarkPalette ? "#633333" : "#fbd6d6"
    frameBorderColor: EaStyle.Colors.isDarkPalette ? "#684747" : "#e9cbcb"
    ToolTip.text: qsTr("Update to EasyDiffraction %1").arg(updates.availableVersion)
}
