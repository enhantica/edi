// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A dialog's choice (Open project and Save project as: Folder or Zip archive). The base's radio button greys only its
// text when disabled, and its circle still answers the pointer; here a choice the platform cannot do is disabled
// whole, circle and text, with no hover or press feedback (owner, 2026-10-25). The rows sit closer than usual, as one
// group.
EaElements.RadioButton {
    id: control

    verticalPadding: AppSizes.choiceRowPadding

    indicator: Rectangle {
        x: control.mirrored ? control.width - width - control.rightPadding : control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        implicitWidth: EaStyle.Sizes.fontPixelSize
        implicitHeight: EaStyle.Sizes.fontPixelSize
        radius: width / 2
        border.width: 0.1 * EaStyle.Sizes.fontPixelSize
        color: "transparent"
        border.color: !control.enabled ? EaStyle.Colors.themeForegroundDisabled : control.checked || control.hovered ? EaStyle.Colors.themeForegroundHovered : control.color
        Behavior on border.color {
            EaAnimations.ThemeChange {}
        }

        // The hover and press halo, as the base's, for an enabled choice only.
        Rectangle {
            anchors.centerIn: parent
            implicitWidth: EaStyle.Sizes.touchSize
            implicitHeight: EaStyle.Sizes.touchSize
            radius: height * 0.5
            visible: control.enabled
            color: control.hovered ? (control.down ? EaStyle.Colors.appBarButtonBackgroundPressed : EaStyle.Colors.appBarButtonBackgroundHovered) : EaStyle.Colors.appBarButtonBackground
        }
        // The chosen dot.
        Rectangle {
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            width: EaStyle.Sizes.fontPixelSize * 0.6
            height: EaStyle.Sizes.fontPixelSize * 0.6
            radius: width / 2
            visible: control.checked || control.down
            color: parent.border.color
        }
    }

    HoverHandler {
        enabled: control.enabled
        cursorShape: Qt.PointingHandCursor
    }
}
