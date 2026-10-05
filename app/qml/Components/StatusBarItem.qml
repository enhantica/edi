// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One status bar entry, as the base's StatusBarItem draws it (icon, key, value), with its value colour
// kept BOUND to the theme. The base's item assigns the value's colour on every text change, which breaks
// its binding, so after the first change the value kept the colour of the theme it was set under. Here a
// change only raises `flashing`, and the colour stays a binding over the theme's tokens: the hovered
// accent while flashing, the foreground otherwise.
Control {
    id: control

    property string keyIcon: ""
    property string keyText: ""
    property string valueText: ""
    property bool flashing: false
    // The value in the theme's red (the warnings item while any is unviewed; edi ADR-0017 §14).
    property bool alert: false
    // A clickable item (the warnings item) takes the pointing cursor and emits `clicked`.
    property bool clickable: false
    // The key is shown only while every item of the bar fits with its key (StatusBar.keysFit).
    property bool showKey: true
    // The item's width with its key shown, whether or not it is: what the bar measures.
    readonly property real labelledWidth: iconLabel.implicitWidth + keyLabel.implicitWidth + valueLabel.implicitWidth + 2 * contentRow.spacing
    signal clicked

    visible: valueText !== ""
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    padding: 0
    font.family: EaStyle.Fonts.fontFamily
    font.pixelSize: EaStyle.Sizes.fontPixelSize

    onValueTextChanged: {
        flashing = true;
        flashEnd.restart();
    }

    Timer {
        id: flashEnd
        interval: 1000
        onTriggered: control.flashing = false
    }

    contentItem: Row {
        id: contentRow
        spacing: control.font.pixelSize * 0.5

        EaElements.Label {
            id: iconLabel
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: control.font.pixelSize
            color: EaStyle.Colors.statusBarIconForeground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.keyIcon
        }
        EaElements.Label {
            id: keyLabel
            visible: control.showKey
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: control.font.family
            font.pixelSize: control.font.pixelSize
            color: EaStyle.Colors.statusBarTextForeground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.keyText
        }
        EaElements.Label {
            id: valueLabel
            objectName: "statusBar.value"
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: control.font.family
            font.pixelSize: control.font.pixelSize
            color: control.alert ? EaStyle.Colors.red : control.flashing ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.valueText
        }
    }

    // A clickable item highlights on hover, as the fit area's outcome does (FitOutcomeLabel).
    background: Item {
        Rectangle {
            anchors.fill: parent
            anchors.margins: -control.font.pixelSize * 0.25
            radius: 2
            visible: control.clickable && hover.hovered
            color: AppColors.hoverHighlight
        }
    }

    HoverHandler {
        id: hover
        cursorShape: control.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: control.clickable
        onTapped: control.clicked()
    }

    EaElements.ToolTip {
        text: control.ToolTip.text
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
