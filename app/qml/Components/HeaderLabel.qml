// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import edi.app

// A table column's header for a `.edi` item: its forms from the label registry (the dictionary's label, a short form,
// an icon), with its units when asked, and as its tooltip the label and the `.edi` name it labels, so every header says
// which item of the file its column shows. A header is never cut (T9): it shows the widest form that fits.
AdaptiveLabel {
    id: header

    // The item, `category.name`, and the token its label depends on (an ADP's type).
    property string uid: ""
    key: uid
    // Whether the units follow the label in brackets: `2θ (deg)`.
    property bool withUnits: false
    // A tooltip of the header's own, before the item's label and `.edi` name; empty: those alone.
    property string toolTipText: ""

    readonly property string units: uid !== "" ? Session.units(uid, variant) : ""
    readonly property string unitsText: withUnits && units !== "" ? ` (${units})` : ""
    longText: (forms.longText ?? "") !== "" ? forms.longText + unitsText : ""
    shortText: (forms.shortText ?? "") !== "" ? forms.shortText + unitsText : ""

    // What the column reserves for its title: the short one where there is one, whichever it shows, so the width never
    // follows the choice (T6).
    readonly property real reservedWidth: shortWidth
    horizontalAlignment: Text.AlignHCenter

    // The base label owns the popup (edi ADR-0076 point 6): the help, and the whole header while another form shows.
    ToolTip.text: uid === "" ? toolTipText : toolTipText !== "" ? `${toolTipText} (${Session.tooltip(uid, variant)})` : Session.tooltip(uid, variant)
}
