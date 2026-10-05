// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Fitting (easydiffractionbeta Pages/Analysis/SideBarBasic/Fitting.qml): Start fitting runs the project's fit
// on the worker and turns into Stop fitting while it runs; a stop keeps the partial result. After a scan
// stopped part way it reads Continue fitting, which fits only the remaining files. Follow, beside it at the
// same width, is enabled while a scan runs: on, the pattern tab shows the file being fitted (edi ADR-0017 §17).
// The scan modes are not fitted here yet: Start fitting stays disabled and says why. Untitled and fixed open,
// as the original's group.
EaElements.GroupBox {
    id: group

    readonly property FitViewModel fit: Session.project ? Session.project.fit : null

    objectName: "group.fitting"
    collapsible: false

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "fitting.start"
            enabled: group.fit !== null && (group.fit.running || group.fit.available)
            fontIcon: group.fit && group.fit.running ? "stop-circle" : "play-circle"
            text: group.fit && group.fit.running ? qsTr("Stop fitting") : group.fit && group.fit.continuable ? qsTr("Continue fitting") : qsTr("Start fitting")
            ToolTip.text: group.fit && !group.fit.available && !group.fit.running ? group.fit.unavailableReason : ""
            onClicked: group.fit.running ? group.fit.cancel() : group.fit.start()
        }
        EaElements.SideBarButton {
            objectName: "fitting.follow"
            enabled: group.fit !== null && group.fit.scanning
            checkable: true
            checked: group.fit !== null && group.fit.scanning && group.fit.following
            fontIcon: "crosshairs"
            text: qsTr("Follow")
            ToolTip.text: qsTr("Show the dataset being fitted")
            onToggled: group.fit.following = checked
        }
    }
}
