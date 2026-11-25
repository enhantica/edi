// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table column's header for a `.edi` item: its label, and its units when asked, from crysta's dictionary through
// Session, and as its tooltip the label and the `.edi` name it labels, so every header says which item of the file
// its column shows.
EaComponents.ListViewLabel {
    id: header
    elide: Text.ElideRight

    // The item, `category.name`, and the token its label depends on (an ADP's type).
    property string uid: ""
    property string variant: ""
    // Whether the units follow the label in brackets: `2θ (deg)`.
    property bool withUnits: false
    // A tooltip of the header's own, before the item's label and `.edi` name; empty: those alone.
    property string toolTipText: ""

    readonly property string units: uid !== "" ? Session.units(uid, variant) : ""

    // A shorter title for a column too narrow for the whole one ("Sym 1"): a title is never cut (T9).
    property string shortText: ""
    fullText: uid === "" ? "" : withUnits && units !== "" ? `${Session.label(uid, variant)} (${units})` : Session.label(uid, variant)
    TextMetrics {
        id: fullMetrics
        font: header.font
        text: header.fullText
    }
    TextMetrics {
        id: reservedMetrics
        font: header.font
        text: header.shortText !== "" ? header.shortText : header.fullText
    }
    // What the column reserves for its title: the short one where there is one, whichever it shows, so the width never
    // follows the choice (T6).
    readonly property real reservedWidth: Math.ceil(reservedMetrics.advanceWidth) + leftPadding + rightPadding
    horizontalAlignment: Text.AlignHCenter
    text: shortText !== "" && width > 0 && fullMetrics.advanceWidth + leftPadding + rightPadding > width + 0.5 ? shortText : fullText

    // The base label owns the popup (edi ADR-0076 point 6): the help, and the whole header while it is elided.
    ToolTip.text: uid === "" ? toolTipText : toolTipText !== "" ? `${toolTipText} (${Session.tooltip(uid, variant)})` : Session.tooltip(uid, variant)
}
