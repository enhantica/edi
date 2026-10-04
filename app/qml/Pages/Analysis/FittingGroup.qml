// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Elements as EaElements

import edi.app

// Fitting (easydiffractionbeta Pages/Analysis/SideBarBasic/Fitting.qml): Start fitting runs the project's fit
// on the worker and turns into Cancel fitting while it runs. The scan modes are not fitted here: the button
// stays disabled and says why. Untitled and fixed open, as the original's group.
EaElements.GroupBox {
    id: group

    readonly property FitViewModel fit: Session.project ? Session.project.fit : null

    objectName: "group.fitting"
    collapsible: false

    EaElements.SideBarButton {
        objectName: "fitting.start"
        wide: true
        enabled: group.fit !== null && group.fit.available
        fontIcon: group.fit && group.fit.running ? "stop-circle" : "play-circle"
        text: group.fit && group.fit.running ? qsTr("Cancel fitting") : qsTr("Start fitting")
        ToolTip.text: group.fit && !group.fit.available ? group.fit.unavailableReason : ""
        onClicked: group.fit.running ? group.fit.cancel() : group.fit.start()
    }
}
