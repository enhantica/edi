// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import edi.app

// The status bar's Fit button (the owner, 2026-10-26): from any page, what the Analysis page's fit button does at the
// moment, with its icon, so a fit can be run again after changing a value elsewhere. A click while a fit runs stops it.
// A framed fit-area item, so it has the fit status's padding and height; near-black with white text in light mode,
// the other way round in dark mode.
FitStatusItem {
    id: control

    property FitViewModel fit: null

    readonly property bool running: fit !== null && fit.running

    framed: true
    showKey: false
    // Shown while it cannot start a fit too, dimmed, so its tool tip can say why.
    clickable: fit !== null && (running || fit.available)
    opacity: clickable ? 1 : 0.4
    // The Analysis page's fit button's icons and the short forms of its texts (the owner, 2026-10-26).
    keyIcon: running ? "stop-circle" : "play-circle"
    valueText: running ? qsTr("Stop") : fit !== null && fit.continuable ? qsTr("Continue") : qsTr("Fit")
    iconColor: AppColors.fitButtonForeground
    valueColor: AppColors.fitButtonForeground
    frameColor: AppColors.fitButtonBackground
    frameHoverColor: AppColors.fitButtonBackgroundHovered
    // The Analysis page's button's text, or why a fit cannot start.
    ToolTip.text: fit === null ? "" : running ? qsTr("Stop fitting") : !fit.available ? fit.unavailableReason : fit.continuable ? qsTr("Continue fitting") : qsTr("Start fitting")
    onClicked: running ? fit.cancel() : fit.start()
}
