// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// The wordmark and the version as Home and About show them, one composition for both (edi ADR-0017 §1):
// the wordmark centred as one unit, then the version line centred on its own below it, one x-height of the
// version's font apart (the owner, 2026-09-29).
Column {
    id: block

    property string link: ""  // opened by a click on the mark, when set
    property string versionObjectName: ""

    spacing: versionMetrics.xHeight

    Wordmark {
        anchors.horizontalCenter: parent.horizontalCenter
        markDiameter: AppSizes.homeMarkDiameter
        link: block.link
    }

    EaElements.Label {
        id: version
        objectName: block.versionObjectName
        anchors.horizontalCenter: parent.horizontalCenter
        text: qsTr("Version %1 (%2)").arg(ApplicationInfo.version).arg(ApplicationInfo.releaseDate)
    }

    FontMetrics {
        id: versionMetrics
        font: version.font
    }
}
