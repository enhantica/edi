// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A table's colour column cell (easydiffractionbeta's): one icon in its colour, one table row wide, on the
// centre line of the row's text (IconLine; edi ADR-0017 §8, §10), with a tooltip naming what the colour is.
Item {
    id: cell

    property string icon: ""
    property string iconColor: ""
    property string toolTip: ""
    // Drawn as a hollow circle instead of the icon (IconLine's `ring`).
    property bool ring: false

    width: EaStyle.Sizes.tableRowHeight
    height: parent ? parent.height : EaStyle.Sizes.tableRowHeight

    IconLine {
        anchors.centerIn: parent
        segments: [
            {
                "icon": cell.icon,
                "color": cell.iconColor,
                "ring": cell.ring,
                "slot": cell.ring
            }
        ]
    }
    HoverHandler {
        id: hover
    }
    EaElements.ToolTip {
        text: cell.toolTip
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
