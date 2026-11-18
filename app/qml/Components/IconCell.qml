// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A table's colour column cell (easydiffractionbeta's): one icon in its colour, the icon-only column's width, on the
// centre line of the row's text (IconLine; edi ADR-0017 §8, §10), with a tooltip naming what the colour is; with
// `clickable` it also acts on a click.
Item {
    id: cell

    property string icon: ""
    property string iconColor: ""
    property string toolTip: ""
    // Drawn as a hollow circle instead of the icon (IconLine's `ring`).
    property bool ring: false
    // A cell that acts on a click (a status that can be switched) shows the pointing hand and emits `clicked`.
    property bool clickable: false
    signal clicked
    property int horizontalAlignment: Text.AlignHCenter

    width: AppSizes.iconOnlyColumnWidth
    height: parent ? parent.height : EaStyle.Sizes.tableRowHeight

    IconLine {
        anchors.verticalCenter: parent.verticalCenter
        x: cell.horizontalAlignment === Text.AlignRight ? cell.width - width : cell.horizontalAlignment === Text.AlignLeft ? 0 : (cell.width - width) / 2
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
        cursorShape: cell.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: cell.clickable
        onTapped: cell.clicked()
    }
    EaElements.ToolTip {
        text: cell.toolTip
        requested: hover.hovered
    }
}
