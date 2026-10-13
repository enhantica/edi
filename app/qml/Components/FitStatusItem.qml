// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One item of the status bar's fit area, as the bar's other items look (StatusBarItem: an icon, the key while the bar
// has room for every key, the value; the owner, 2026-10-13), its value's digits in fixed-width cells (DigitText).
Control {
    id: control

    property string keyIcon: ""
    property string keyText: ""
    property string valueText: ""
    property color iconColor: EaStyle.Colors.statusBarIconForeground
    property color valueColor: EaStyle.Colors.themeForeground
    // The key is shown only while every item of the bar fits with its key (StatusBar.keysFit).
    property bool showKey: true
    property bool clickable: false
    property bool shown: valueText !== ""
    // The hover frame's height, which the fit's progress bar shares (the owner, 2026-10-13).
    readonly property real frameHeight: Math.round(font.pixelSize * 1.8)
    // The item's width with its key shown, whether or not it is, and with its icon and value only: what the bar
    // measures.
    readonly property real labelledWidth: iconLabel.implicitWidth + keyLabel.implicitWidth + value.implicitWidth + 2 * contentRow.spacing + leftPadding + rightPadding
    readonly property real compactWidth: iconLabel.implicitWidth + value.implicitWidth + contentRow.spacing + leftPadding + rightPadding
    signal clicked

    visible: shown
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    padding: 0
    // A clickable item keeps its hover frame clear of its icon and text (the owner, 2026-10-13).
    leftPadding: clickable ? Math.round(font.pixelSize * 0.5) : 0
    rightPadding: leftPadding
    font.family: EaStyle.Fonts.fontFamily
    font.pixelSize: EaStyle.Sizes.fontPixelSize

    contentItem: Row {
        id: contentRow
        spacing: control.font.pixelSize * 0.5

        EaElements.Label {
            id: iconLabel
            anchors.verticalCenter: parent.verticalCenter
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: control.font.pixelSize
            color: control.iconColor
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.keyIcon
        }
        EaElements.Label {
            id: keyLabel
            visible: control.showKey
            anchors.verticalCenter: parent.verticalCenter
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
        DigitText {
            id: value
            objectName: "statusBar.fit.value"
            anchors.verticalCenter: parent.verticalCenter
            font: control.font
            color: control.valueColor
            text: control.valueText
        }
    }

    // A clickable item highlights on hover, as the bar's Messages item does.
    background: Item {
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: control.frameHeight
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
