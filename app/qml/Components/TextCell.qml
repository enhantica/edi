// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Logic as EaLogic
import EasyApplication.Gui.Components as EaComponents

import edi.app

// One editable text cell (the base's TableViewTextInput): shows `value`; `committed` carries what the
// user typed, which the owner writes through its model (the value then comes back from the model). A
// number the cell accepts as a number is shown at the base's default three significant digits, as a
// field is; the model keeps it whole and an unedited cell commits nothing. Names, tokens and whole
// numbers are shown as they are. A refused commit (text that is not of the kind the cell `accepts`, or
// a value the core refuses) returns the cell to the model's value and shows why, as ParameterField
// does.
EaComponents.TableViewTextInput {
    id: cell

    property var value: ""
    readonly property string shown: accepts === "number" && typeof value === "number" && isFinite(value) ? EaLogic.Utils.toDefaultPrecision(value) : String(value)
    // "text", "number" or "integer": what the cell accepts before anything reaches the model.
    property string accepts: "text"
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    signal committed(string text)

    text: shown
    warned: refusal !== ""
    ToolTip.text: refusal
    ToolTip.visible: refusal !== "" && (hovered || activeFocus)
    onValueChanged: refusal = ""
    onAccepted: commit()
    onEditingFinished: commit()

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
}
