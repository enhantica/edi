// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Fitting (easydiffractionbeta Pages/Analysis/SideBarBasic/Fitting.qml): Start fitting runs the project's fit
// on the worker and turns into Stop fitting while it runs; a stop keeps the partial result. In a scan project the
// button follows the datasets' fits (edi ADR-0017 §17): Start fitting while none is fitted, Continue fitting while
// some are not (it fits from the first unfitted one), disabled once all are. Reset fits, between it and Follow,
// clears every dataset's fit result in one Undo step. Follow is enabled while a scan runs: on, the pattern tab shows
// the file being fitted. A scan project's three buttons share the row in thirds; the other modes' two in halves.
// Untitled and fixed open, as the original's group.
EaElements.GroupBox {
    id: group

    readonly property FitViewModel fit: Session.project ? Session.project.fit : null

    collapsible: false
    objectName: "group.fitting"

    Row {
        id: buttons

        readonly property bool scan: Session.project !== null && Session.project.scan
        readonly property real third: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            ToolTip.text: group.fit && !group.fit.available && !group.fit.running ? group.fit.unavailableReason : ""
            enabled: group.fit !== null && (group.fit.running || group.fit.available)
            fontIcon: group.fit && group.fit.running ? "stop-circle" : "play-circle"
            objectName: "fitting.start"
            text: group.fit && group.fit.running ? qsTr("Stop fitting") : group.fit && group.fit.continuable ? qsTr("Continue fitting") : qsTr("Start fitting")
            width: buttons.scan ? buttons.third : implicitWidth

            onClicked: group.fit.running ? group.fit.cancel() : group.fit.start()
        }
        EaElements.SideBarButton {
            ToolTip.text: qsTr("Clear every dataset's fit result")
            enabled: group.fit !== null && group.fit.canReset
            fontIcon: "eraser"
            objectName: "fitting.reset"
            text: qsTr("Reset fits")
            visible: buttons.scan
            width: buttons.third

            onClicked: group.fit.reset()
        }
        EaElements.SideBarButton {
            ToolTip.text: qsTr("Show the dataset being fitted")
            checkable: true
            checked: group.fit !== null && group.fit.scanning && group.fit.following
            enabled: group.fit !== null && group.fit.scanning
            fontIcon: "crosshairs"
            objectName: "fitting.follow"
            text: qsTr("Follow")
            width: buttons.scan ? buttons.third : implicitWidth

            onToggled: group.fit.following = checked
        }
    }
}
