// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One parameter as an editable field (the base's ParamTextField, as the original's groups use it):
// the value with its uncertainty, the units inside the field, the "vary" toggle in its context menu.
// A value the user typed goes through the core (ParameterItem.value -> assign_value); a refused one
// (typed text that is not a number, or a value the core refuses) shows why and the field returns to
// the model's value. A parameter the space group fixes or ties to another (edi ADR-0019) is shown
// disabled, with the value symmetry implies: no typing, no vary toggle.
EaElements.ParamTextField {
    id: field

    required property ParameterItem item
    property string label: item ? item.shortName : ""
    // What the value means, shown while hovering when nothing is wrong with it.
    property string hint: ""
    // Why the last typed text was refused before reaching the core; the core's own refusal is the item's.
    property string typedRefusal: ""
    readonly property string refusal: typedRefusal !== "" ? typedRefusal : item !== null ? item.lastError : ""
    readonly property bool refinable: item === null || item.refinable
    // A fixed setting is edited but never fitted: no fit toggle.
    readonly property bool canFit: refinable && (item === null || item.fittable)
    // Without measured data in any experiment nothing is fitted, so the free toggle is disabled (edi ADR-0046).
    readonly property bool measured: Session.project === null || Session.project.fit.measured
    Binding {
        target: field.fitCheckBox
        when: field.fitCheckBox !== null
        property: "enabled"
        value: field.measured
    }
    // A value outside its range (a fit writes its values unchecked) is red with the range, as in a table cell.
    readonly property bool outsideRange: item !== null && item.outsideRange
    readonly property string warningText: refusal !== "" ? refusal : outsideRange ? qsTr("Outside its range, %1 to %2").arg(item.minimum).arg(item.maximum) : item !== null ? item.domainWarning : ""

    // A free value is in the status bar's green, the one green token (EaStyle.Colors.green; the owner, 2026-10-22).
    color: warned ? EaStyle.Colors.red : !enabled || readOnly ? EaStyle.Colors.themeForegroundMinor : item && item.free && canFit ? EaStyle.Colors.green : EaStyle.Colors.themeForeground

    enabled: refinable
    // The value and its uncertainty as text, by the app's one rule for numbers (NumberText).
    parameter: item ? {
        "value": NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0),
        "error": item.hasUncertainty ? NumberText.error(item.uncertainty, 0, item.value) : "",
        "enabled": field.refinable,
        "fittable": field.canFit,
        "fit": item.free && field.canFit,
        "category": item.category,
        "name": item.name,
        "shortPrettyName": field.label,
        "units": item.displayUnits
    } : ({})

    // The value as edited: in full, where the cell shows it rounded (NumberText).
    readonly property string editText: item !== null ? NumberText.full(item.value) : value

    // A value wider than the field shows from its start and clips at the end, without an ellipsis, as a table
    // cell does; it is shown in full while edited.
    onActiveFocusChanged: {
        if (activeFocus && text === value) {
            text = editText;
        } else if (!activeFocus) {
            commit();
            cursorPosition = 0;
        }
    }
    onTextChanged: if (!activeFocus)
        cursorPosition = 0
    Component.onCompleted: {
        // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
        FieldTitles.align(field);
        cursorPosition = 0;
    }

    warned: warningText !== ""
    ToolTip.text: warningText
    WarningToolTip {
        text: field.warningText
        visible: field.warned && (field.hovered || field.activeFocus)
    }
    EaElements.ToolTip {
        text: field.hint
        visible: field.hint !== "" && !field.warned && field.hovered && EaGlobals.Vars.showToolTips
    }

    onValueChanged: typedRefusal = ""
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the field both commit; the second of the two finds nothing new. Text left as shown, rounded or
    // in full, changes nothing.
    function commit() {
        if (item === null)
            return;
        if (text !== field.value && text !== field.editText) {
            typedRefusal = TypedInput.refusal(text, "number");
            if (typedRefusal === "") {
                item.value = Number(text);
            }
        }
        text = Qt.binding(() => field.value);
    }
    onFitToggled: checked => {
        if (item !== null)
            item.free = checked;
    }
}
