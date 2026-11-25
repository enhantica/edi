// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// A read-only table cell that shows a number (an s.u., a range end, a fit result). When the number's text does not
// fit the cell it is shown in scientific notation with the same significant digits, and hovering shows it in full
// (NumberText.fitted; the owner, 2026-10-22), so no number is cut short.
CellLabel {
    id: label
    // A number is fitted (fewer digits, then ×10ⁿ), never cut with an ellipsis (the owner, 2026-11-22).
    elide: Text.ElideNone

    // The number as written by its rule (NumberText), before it is fitted to the cell, and the shorter form the cell
    // shows when that does not fit (its scientific notation, unless the column gives another: an s.u.'s own).
    property string number: ""
    property string narrow: NumberText.compact(number)
    // What hovering shows when the cell shows the number shorter: the number in full (NumberText.plainFull) where the
    // column has it, else as written.
    property string full: number
    // What the cell shows: the number, or the shorter form where its column is narrower. Set from the changes it
    // follows rather than bound, and only once a table has sized the cell: until then the cell is as wide as its own
    // text, and following that width back to the text would loop (as ParameterCell does).
    property string shown: number
    // Once sized it stays so: the shorter form can be just as wide as the cell.
    property bool sized: false
    function refit() {
        if (Math.abs(width - implicitWidth) >= 0.5)
            sized = true;
        shown = sized ? NumberText.fitted(number, width - leftPadding - rightPadding, metrics, narrow) : number;
    }
    onWidthChanged: refit()
    onLeftPaddingChanged: refit()
    onRightPaddingChanged: refit()
    onNumberChanged: refit()
    onNarrowChanged: refit()
    onFontChanged: refit()
    Component.onCompleted: refit()

    text: shown
    // The base's tooltip shows the number in full while the cell shows it shorter or elided.
    fullText: full
    shortened: shown !== number || truncated

    FontMetrics {
        id: metrics
        font: label.font
    }
}
