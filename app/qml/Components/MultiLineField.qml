// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

// A text field of several lines, in the one-line text fields' look (the owner, 2026-10-27): three lines at first,
// growing with its text to ten, then scrolling. A line break is typed with Return.
ScrollView {
    id: field

    property alias text: area.text
    property alias placeholderText: area.placeholderText
    property int minimumLines: 3
    property int maximumLines: 10

    readonly property real lineHeight: Math.ceil(metrics.lineSpacing)

    implicitHeight: Math.min(maximumLines, Math.max(minimumLines, area.lineCount)) * lineHeight + area.topPadding + area.bottomPadding
    clip: true

    EaElements.TextArea {
        id: area

        padding: EaStyle.Sizes.fontPixelSize * 0.5 + 1
        wrapMode: TextEdit.Wrap
        color: !enabled ? EaStyle.Colors.themeForegroundDisabled : readOnly ? EaStyle.Colors.themeForegroundMinor : hovered || activeFocus ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
        background: Rectangle {
            color: area.enabled && !area.readOnly && (area.activeFocus || area.hovered) ? EaStyle.Colors.appBarComboBoxBackgroundHovered : EaStyle.Colors.appBarComboBoxBackground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            border.color: area.enabled && !area.readOnly && (area.activeFocus || area.hovered) ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.appBarComboBoxBorder
            Behavior on border.color {
                EaAnimations.ThemeChange {}
            }
        }
    }
    FontMetrics {
        id: metrics
        font: area.font
    }
}
