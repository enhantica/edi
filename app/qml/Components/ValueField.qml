// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A plain value of a category as a field (the base's ParamTextField without a parameter's vary
// toggle): a name, a token, a number. `committed` carries what the user typed; the owner writes it
// through the view-model, whose value then comes back through `value`. A refused commit (text that
// is not of the kind the field `accepts`, or a value the core refuses) returns the field to the
// model's value and shows why, as ParameterField does. A field of a `.edi` item names it by `uid` (and `variant`):
// its label and units then come from crysta's dictionary, a number shows as the project file spells it, and its
// tooltip names the item it shows (edi ADR-0051).
EaElements.ParamTextField {
    id: field

    property string uid: ""
    property string variant: ""
    property string label: uid !== "" ? Session.label(uid, variant) : ""
    property var fieldValue: ""
    property string unit: uid !== "" ? Session.units(uid, variant) : ""
    property bool editable: true
    // "text", "number" or "integer": what the field accepts before anything reaches the model.
    property string accepts: "text"
    // An empty text is committed as it is (the owner reads it as "no value") rather than refused.
    property bool clearable: false
    // A narrower rule than `accepts`, as a function of the text (true when admitted), and why it refuses: the
    // text is red while typed against it, as a filterable combo box's is, and a commit of it is refused.
    property var admits: null
    property string admitsRule: ""
    readonly property bool typedAdmitted: admits === null || text === "" || admits(text)
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    signal committed(string text)

    // A number of an item shows as the project file spells it, any other number by the app's rule for numbers
    // (NumberText). Display only: the model keeps the full value, and an unedited field commits nothing. Anything
    // else (a name, a token, a whole number) is shown as it is.
    parameter: ({
            "value": field.accepts === "number" && typeof field.fieldValue === "number" ? (field.uid !== "" ? Session.written(field.uid, field.fieldValue) : NumberText.plain(field.fieldValue, 10)) : String(field.fieldValue),
            "error": 0,
            "enabled": field.editable,
            "fittable": false,
            "shortPrettyName": field.label,
            "units": field.unit
        })
    readOnly: !editable
    warned: refusal !== "" || !typedAdmitted
    ToolTip.text: uid !== "" ? Session.tooltip(uid, variant) : ""
    ToolTip.visible: ToolTip.text !== "" && hovered && refusal === "" && EaGlobals.Vars.showToolTips
    WarningToolTip {
        text: field.refusal
        visible: text !== "" && (field.hovered || field.activeFocus)
    }

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
        if (refusal === "" && !typedAdmitted)
            refusal = admitsRule;
        if (refusal === "") {
            committed(text);
            refusal = Session.project ? Session.project.lastError : "";
        }
        text = Qt.binding(() => field.value);
    }
}
