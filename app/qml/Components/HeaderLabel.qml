// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table column's header for a `.edi` item: its label, and its units when asked, from crysta's dictionary through
// Session, and as its tooltip the label and the `.edi` name it labels, so every header says which item of the file
// its column shows.
EaComponents.ListViewLabel {
    id: header

    // The item, `category.name`, and the token its label depends on (an ADP's type).
    property string uid: ""
    property string variant: ""
    // Whether the units follow the label in brackets: `2θ (deg)`.
    property bool withUnits: false

    readonly property string units: uid !== "" ? Session.units(uid, variant) : ""

    horizontalAlignment: Text.AlignHCenter
    text: uid === "" ? "" : withUnits && units !== "" ? `${Session.label(uid, variant)} (${units})` : Session.label(uid, variant)

    EaElements.ToolTip {
        text: header.uid !== "" ? Session.tooltip(header.uid, header.variant) : ""
        visible: header.uid !== "" && header.hovered && EaGlobals.Vars.showToolTips
    }
}
