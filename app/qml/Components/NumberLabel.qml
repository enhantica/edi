// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A read-only table cell that shows a number (an s.u., a range end, a fit result). When the number's text does not
// fit the cell it is shown in scientific notation with the same significant digits, and hovering shows it in full
// (NumberText.fitted; the owner, 2026-10-22), so no number is cut short.
EaComponents.TableViewLabel {
    id: label

    // The number as written by its rule (NumberText), before it is fitted to the cell, and the shorter form the cell
    // shows when that does not fit (its scientific notation, unless the column gives another: an s.u.'s own).
    property string number: ""
    property string narrow: NumberText.compact(number)
    readonly property string shown: NumberText.fitted(number, width - leftPadding - rightPadding, metrics, narrow)

    text: shown

    FontMetrics {
        id: metrics
        font: label.font
    }
    EaElements.ToolTip {
        text: label.number
        visible: label.shown !== label.number && label.hovered && EaGlobals.Vars.showToolTips
    }
}
