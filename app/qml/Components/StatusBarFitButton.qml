// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The status bar's Fit button (the owner, 2026-10-26): from any page, what the Analysis page's fit button does at the
// moment, with its icon, so a fit can be run again after changing a value elsewhere. A click while a fit runs stops it.
// As tall as the fit's progress bar and as round; near-black with white text in light mode, the other way round in
// dark mode.
Control {
    id: control

    property FitViewModel fit: null
    property real frameHeight: Math.round(font.pixelSize * 1.8)

    readonly property bool running: fit !== null && fit.running

    enabled: fit !== null && (running || fit.available)
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    implicitHeight: frameHeight
    leftPadding: Math.round(font.pixelSize * 0.75)
    rightPadding: leftPadding
    topPadding: 0
    bottomPadding: 0
    font.family: EaStyle.Fonts.fontFamily
    font.pixelSize: EaStyle.Sizes.fontPixelSize
    opacity: enabled ? 1 : 0.4

    contentItem: Row {
        spacing: control.font.pixelSize * 0.4

        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: control.font.pixelSize
            color: AppColors.fitButtonForeground
            // The Analysis page's fit button's icons.
            text: control.running ? "stop-circle" : "play-circle"
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font: control.font
            color: AppColors.fitButtonForeground
            text: qsTr("Fit")
        }
    }

    background: Rectangle {
        implicitHeight: control.frameHeight
        radius: height / 2
        color: hover.hovered && control.enabled ? AppColors.fitButtonBackgroundHovered : AppColors.fitButtonBackground
        Behavior on color {
            EaAnimations.ThemeChange {}
        }
    }

    HoverHandler {
        id: hover
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: control.enabled
        onTapped: control.running ? control.fit.cancel() : control.fit.start()
    }

    // The Analysis page's button's text, or why a fit cannot start.
    EaElements.ToolTip {
        text: control.fit === null ? "" : control.running ? qsTr("Stop fitting") : !control.fit.available ? control.fit.unavailableReason : control.fit.continuable ? qsTr("Continue fitting") : qsTr("Start fitting")
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
