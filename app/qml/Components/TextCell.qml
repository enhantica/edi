// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// One editable text cell (the base's ListViewTextInput): shows `value`; `committed` carries what the
// user typed, which the owner writes through its model (the value then comes back from the model). A
// number of a `.edi` item (`uid`) is shown as the project file spells it (edi ADR-0051); the model keeps it
// whole and an unedited cell commits nothing. Names, tokens and whole numbers are shown as they are. A refused commit (text that is not of the kind the cell `accepts`, or
// a value the core refuses) returns the cell to the model's value and shows why, as ParameterField
// does.
EaComponents.ListViewTextInput {
    id: cell

    property var value: ""
    // The item a numeric cell shows, `category.name`.
    property string uid: ""
    // A number as the file spells it (by the app's rule for numbers without an item), in scientific notation when
    // that would not fit the cell (NumberText.fitted; the owner, 2026-10-22), with the file's spelling, or the number
    // in full without an item, on hover.
    readonly property bool numeric: accepts === "number" && typeof value === "number" && isFinite(value)
    readonly property string written: numeric ? (uid !== "" ? Session.written(uid, value) : NumberText.plain(value, 8)) : String(value)
    readonly property string shown: numeric ? NumberText.fitted(written, width - leftPadding - rightPadding, metrics) : written
    // "text", "number" or "integer": what the cell accepts before anything reaches the model.
    property string accepts: "text"
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    // Read-only but shown as usual, not greyed (an auto-estimated background; the owner, 2026-10-20): nothing can be
    // typed or committed.
    property bool locked: false
    signal committed(string text)

    readOnly: locked
    activeFocusOnPress: !locked
    activeFocusOnTab: !locked
    // The base's colours, with a locked cell kept in the normal colour rather than the read-only grey.
    color: enterFlash ? EaStyle.Colors.themeForeground : warned ? EaStyle.Colors.red : !enabled || (readOnly && !locked) || minored ? EaStyle.Colors.themeForegroundMinor : activeFocus || selected || hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground

    // RestoreNone removes the clean binding without assigning text. This is
    // essential for IME preedit, which must survive even before textEdited.
    Binding {
        target: cell
        property: "text"
        value: cell.shown
        when: cell.draft === null && !cell.assistantEditing && !cell.assistantCommitReady &&
              cell.commitInProgress === null && !cell.inputMethodComposing
        restoreMode: Binding.RestoreNone
    }
    warned: refusal !== ""
    ToolTip.text: refusal
    WarningToolTip {
        text: cell.refusal
        visible: text !== "" && (cell.hovered || cell.activeFocus)
    }
    FontMetrics {
        id: metrics
        font: cell.font
    }
    EaElements.ToolTip {
        text: cell.uid !== "" ? cell.written : NumberText.plainFull(cell.value)
        visible: cell.shown !== cell.written && cell.hovered && !cell.activeFocus && !cell.warned && EaGlobals.Vars.showToolTips
    }
    onValueChanged: refusal = ""
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the cell both commit; the second of the two finds nothing new.
    function commit() {
        if (locked || text === shown) {
            text = Qt.binding(() => cell.shown);
            return;
        }
        refusal = TypedInput.refusal(text, accepts);
        if (refusal === "") {
            committed(text);
            refusal = Session.project ? Session.project.lastError : "";
        }
        text = Qt.binding(() => cell.shown);
    }
}
