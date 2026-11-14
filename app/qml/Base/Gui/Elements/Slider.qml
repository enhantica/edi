// SPDX-License-Identifier: BSD-3-Clause
// Pinned gui-components copy; upstream's value tooltip follows the tooltip level. Here the value shown while the
// slider is dragged or hovered is a data tooltip, always shown (owner record 2026-11-11, items 2 and 5).
import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Material
import QtQuick.Controls.Material.impl

import EasyApplication.Gui.Logic as EaLogic
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

T.Slider {
    id: control

    // The bubble's text while enabled, the value by default; a caller may give its own (an input, never the shown text,
    // which a disabled slider's reason replaces).
    property string toolTipText: EaLogic.Utils.toDefaultPrecision(control.value)
    property bool toolTipSelfExplanatory: false

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitHandleWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset, implicitHandleHeight + topPadding + bottomPadding)

    padding: 6

    handle: EaElements.SliderHandle {
        x: control.leftPadding + (control.horizontal ? control.visualPosition * (control.availableWidth - width) : (control.availableWidth - width) / 2)
        y: control.topPadding + (control.horizontal ? (control.availableHeight - height) / 2 : control.visualPosition * (control.availableHeight - height))
        value: control.value
        handleHasFocus: control.visualFocus
        handlePressed: control.pressed
        handleHovered: control.hovered

        // The value while it is dragged or hovered; on a disabled slider with a tooltip of its own, that text, which
        // says why it is disabled.
        EaElements.ToolTip {
            id: toolTip

            readonly property bool reason: !control.enabled && control.T.ToolTip.text !== ""
            requested: control.pressed || toolTipHover.hovered
            text: reason ? control.T.ToolTip.text : control.toolTipText
            selfExplanatory: control.toolTipSelfExplanatory
            // The value is data, shown whatever the tooltip level; the reason is help, which follows it.
            data: !reason
        }
    }

    // Reports hover on a disabled slider too.
    HoverHandler {
        id: toolTipHover
    }

    background: Rectangle {
        x: control.leftPadding + (control.horizontal ? 0 : (control.availableWidth - width) / 2)
        y: control.topPadding + (control.horizontal ? (control.availableHeight - height) / 2 : 0)
        implicitWidth: control.horizontal ? 200 : 4
        implicitHeight: control.horizontal ? 4 : 200
        width: control.horizontal ? control.availableWidth : implicitWidth
        height: control.horizontal ? implicitHeight : control.availableHeight

        radius: 2
        scale: control.horizontal && control.mirrored ? -1 : 1
        color: EaStyle.Colors.appBorder
        Behavior on color {
            EaAnimations.ThemeChange {}
        }

        Rectangle {
            y: control.horizontal ? 0 : control.visualPosition * parent.height
            width: control.horizontal ? control.position * parent.width : 4
            height: control.horizontal ? 4 : control.position * parent.height

            radius: 2
            color: EaStyle.Colors.themeForegroundHovered
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
        }
    }
}
