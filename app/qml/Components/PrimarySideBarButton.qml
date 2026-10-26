// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A sidebar button in the status bar's Fit button's colours (the owner, 2026-10-26): dark grey with a white icon and
// text in light mode, the other way round in dark mode, darker on hover and dimmed while disabled. The base button's
// layout, with its background and content drawn in those colours; the Analysis page's fit button.
EaElements.SideBarButton {
    id: control

    opacity: enabled ? 1 : 0.4

    contentItem: Item {
        Row {
            anchors.centerIn: parent
            spacing: control.spacing

            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                font.pixelSize: control.smallIcon ? control.font.pixelSize : control.font.pixelSize * 1.25
                color: AppColors.fitButtonForeground
                text: control.fontIcon
            }
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                font: control.font
                color: AppColors.fitButtonForeground
                text: control.text
            }
        }
    }

    background: Rectangle {
        implicitWidth: control.wide ? EaStyle.Sizes.sideBarContentWidth : (EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize) / 2
        implicitHeight: EaStyle.Sizes.sideBarButtonHeight
        radius: control.radius
        color: control.hovered && control.enabled ? AppColors.fitButtonBackgroundHovered : AppColors.fitButtonBackground
        Behavior on color {
            EaAnimations.ThemeChange {}
        }
    }
}
