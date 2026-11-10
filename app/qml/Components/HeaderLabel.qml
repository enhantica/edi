// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table column's header for a `.edi` item: its label, and its units when asked, from crysta's dictionary through
// Session, and as its tooltip the label and the `.edi` name it labels, so every header says which item of the file
// its column shows.
EaComponents.ListViewLabel {
    elide: Text.ElideRight
    id: header

    // The item, `category.name`, and the token its label depends on (an ADP's type).
    property string uid: ""
    property string variant: ""
    // Whether the units follow the label in brackets: `2θ (deg)`.
    property bool withUnits: false
    // A tooltip of the header's own, before the item's label and `.edi` name; empty: those alone.
    property string toolTipText: ""

    readonly property string units: uid !== "" ? Session.units(uid, variant) : ""

    horizontalAlignment: Text.AlignHCenter
    text: uid === "" ? "" : withUnits && units !== "" ? `${Session.label(uid, variant)} (${units})` : Session.label(uid, variant)

    // The base label owns the popup (edi ADR-0076 point 6): the help, and the whole header while it is elided.
    ToolTip.text: uid === "" ? toolTipText : toolTipText !== "" ? `${toolTipText} (${Session.tooltip(uid, variant)})` : Session.tooltip(uid, variant)
}
