// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A button at the status bar's right end (the owner, 2026-10-26): a framed fit-area item in the base's normal button
// colours adapted to the bar, the light frame and the theme's text, the accent while it is checked and the disabled
// colour while it cannot act. Reset and Follow; the Fit button takes its strong colours while it can act.
FitStatusItem {
    property bool checked: false

    framed: true
    showKey: false
    iconColor: !clickable ? EaStyle.Colors.themeForegroundDisabled : checked ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
    valueColor: iconColor
}
