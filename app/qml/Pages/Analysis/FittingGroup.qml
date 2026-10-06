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

    objectName: "group.fitting"
    collapsible: false

    Row {
        id: buttons

        readonly property bool scan: Session.project !== null && Session.project.scan
        readonly property real third: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "fitting.start"
            width: buttons.scan ? buttons.third : implicitWidth
            enabled: group.fit !== null && (group.fit.running || group.fit.available)
            fontIcon: group.fit && group.fit.running ? "stop-circle" : "play-circle"
            text: group.fit && group.fit.running ? qsTr("Stop fitting") : group.fit && group.fit.continuable ? qsTr("Continue fitting") : qsTr("Start fitting")
            ToolTip.text: group.fit && !group.fit.available && !group.fit.running ? group.fit.unavailableReason : ""
            onClicked: group.fit.running ? group.fit.cancel() : group.fit.start()
        }
        EaElements.SideBarButton {
            objectName: "fitting.reset"
            visible: buttons.scan
            width: buttons.third
            enabled: group.fit !== null && group.fit.canReset
            fontIcon: "eraser"
            text: qsTr("Reset fits")
            ToolTip.text: qsTr("Clear every dataset's fit result")
            onClicked: group.fit.reset()
        }
        EaElements.SideBarButton {
            objectName: "fitting.follow"
            width: buttons.scan ? buttons.third : implicitWidth
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
