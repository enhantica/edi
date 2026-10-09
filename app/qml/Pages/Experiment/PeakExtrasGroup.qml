// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `peak` in Extras: the peak window `cutoff_fwhm`, a calculation setting rather than
// a profile parameter, in a group of its own category's name; the profile stays in Basic (PeakGroup). Beside
// it, Set automatically — no automatic cutoff exists yet, so it is disabled, with a tooltip saying so (edi
// ADR-0017 §4). Field and button take half the row each, their bottoms aligned.
EaElements.GroupRow {
    id: group

    property ExperimentViewModel experiment: null

    ValueField {
        id: cutoffField

        accepts: "number"
        fieldValue: group.experiment ? group.experiment.cutoffFwhm : ""
        label: qsTr("cutoff (FWHM)")
        objectName: "peak.cutoff_fwhm"

        onCommitted: text => group.experiment.cutoffFwhm = Number(text)
    }

    // A disabled button takes no hover, so its tooltip hangs on the item around it. The button is exactly as
    // tall as the field's box (the field less its title inset) and shares its bottom, so top and bottom line
    // up: the base sizes a text field's box by its text and padding and a sidebar button by a fixed token,
    // which differ (edi ADR-0017 §4).
    Item {
        anchors.bottom: parent.bottom
        height: autoButton.height
        width: autoButton.width

        EaElements.SideBarButton {
            id: autoButton

            enabled: false
            fontIcon: "magic"
            height: cutoffField.height - cutoffField.topInset
            objectName: "peak.cutoff_fwhm.auto"
            text: qsTr("Set automatically")
        }
        HoverHandler {
            id: autoHover
        }
        EaElements.ToolTip {
            text: qsTr("Not available yet")
            visible: autoHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
}
