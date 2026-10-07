// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Elements as EaElements

import edi.app

// A plain value of a category as a field (the base's ParamTextField without a parameter's vary
// toggle): a name, a token, a number. `committed` carries what the user typed; the owner writes it
// through the view-model, whose value then comes back through `value`. A refused commit (text that
// is not of the kind the field `accepts`, or a value the core refuses) returns the field to the
// model's value and shows why, as ParameterField does.
EaElements.ParamTextField {
    id: field

    property string label: ""
    property var fieldValue: ""
    property string unit: ""
    property bool editable: true
    // "text", "number" or "integer": what the field accepts before anything reaches the model.
    property string accepts: "text"
    // An empty text is committed as it is (the owner reads it as "no value") rather than refused.
    property bool clearable: false
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    signal committed(string text)

    // A number the field accepts as a number is shown by the app's one rule for numbers (NumberText).
    // Display only: the model keeps the full value, and an unedited field commits nothing. Anything else (a
    // name, a token, a whole number) is shown as it is.
    parameter: ({
            "value": field.accepts === "number" && typeof field.fieldValue === "number" ? NumberText.plain(field.fieldValue, 10) : String(field.fieldValue),
            "error": 0,
            "enabled": field.editable,
            "fittable": false,
            "shortPrettyName": field.label,
            "units": field.unit
        })
    readOnly: !editable
    warned: refusal !== ""
    ToolTip.text: refusal
    ToolTip.visible: refusal !== "" && (hovered || activeFocus)

    onFieldValueChanged: refusal = ""
    // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
    Component.onCompleted: FieldTitles.align(field)
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the field both commit; the second of the two finds nothing new.
    function commit() {
        if (!editable || text === field.value)
            return;
        refusal = clearable && text === "" ? "" : TypedInput.refusal(text, accepts);
        if (refusal === "") {
            committed(text);
            refusal = Session.project ? Session.project.lastError : "";
        }
        text = Qt.binding(() => field.value);
    }
}
