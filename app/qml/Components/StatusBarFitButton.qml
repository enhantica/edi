// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The status bar's Fit button, in its right corner (the owner, 2026-10-26): from any page, it fits the project and reads
// Fit, Continue, Refit or Stop, with the matching icon; a click while a fit runs stops it. Black with white text in light mode
// and the other way round in dark mode while it can act, its background the accent on hover
// (AppColors.fitButtonBackground); otherwise it looks like Reset and Follow. It keeps its word when the bar runs short of
// room.
StatusBarButton {
    id: control

    property FitViewModel fit: null

    readonly property bool running: fit !== null && fit.running

    clickable: fit !== null && (running || fit.available)
    keyIcon: running ? "stop-circle" : "play-circle"
    // Refit while a scan's results are outdated: every file again from the template (the owner, 2026-10-26).
    valueText: running ? qsTr("Stop") : fit !== null && fit.outOfDate ? qsTr("Refit") : fit !== null && fit.continuable ? qsTr("Continue") : qsTr("Fit")
    iconColor: clickable ? AppColors.fitButtonForeground : EaStyle.Colors.themeForegroundDisabled
    frameColor: clickable ? AppColors.fitButtonBackground : AppColors.statusButtonBackground
    frameHoverColor: clickable ? EaStyle.Colors.themeAccent : frameColor
    // No border while it can act, so its hover is the accent alone, without a ring.
    outlined: !clickable
    tintsOnHover: !clickable
    // Shown only while tool tips are on, as every tool tip is.
    ToolTip.text: qsTr("Fit the free parameters")
    onClicked: running ? fit.cancel() : fit.start()
}
