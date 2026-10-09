// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// One editable text cell (the base's ListViewTextInput): shows `value`; `committed` carries what the
// user typed, which the owner writes through its model (the value then comes back from the model). A
// number the cell accepts as a number is shown at the base's default three significant digits, as a
// field is; the model keeps it whole and an unedited cell commits nothing. Names, tokens and whole
// numbers are shown as they are. A refused commit (text that is not of the kind the cell `accepts`, or
// a value the core refuses) returns the cell to the model's value and shows why, as ParameterField
// does.
EaComponents.ListViewTextInput {
    id: cell

    // "text", "number" or "integer": what the cell accepts before anything reaches the model.
    property string accepts: "text"
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    // A number by the app's one rule for numbers in cells (NumberText).
    readonly property string shown: accepts === "number" && typeof value === "number" && isFinite(value) ? NumberText.plain(value, 8) : String(value)
    property var value: ""

    signal committed(string text)

    // Return and leaving the cell both commit; the second of the two finds nothing new.
    function commit() {
        if (text === shown)
            return;
        refusal = TypedInput.refusal(text, accepts);
        if (refusal === "") {
            committed(text);
            refusal = Session.project ? Session.project.lastError : "";
        }
        text = Qt.binding(() => cell.shown);
    }

    ToolTip.text: refusal
    ToolTip.visible: refusal !== "" && (hovered || activeFocus)
    text: shown
    warned: refusal !== ""

    onAccepted: commit()
    onEditingFinished: commit()
    onValueChanged: refusal = ""
}
