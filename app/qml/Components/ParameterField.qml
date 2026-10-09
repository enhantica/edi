// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

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

    // A fixed setting is edited but never fitted: no fit toggle.
    readonly property bool canFit: refinable && (item === null || item.fittable)
    required property ParameterItem item
    property string label: item ? item.shortName : ""
    readonly property bool refinable: item === null || item.refinable
    readonly property string refusal: typedRefusal !== "" ? typedRefusal : item !== null ? item.lastError : ""
    // Why the last typed text was refused before reaching the core; the core's own refusal is the item's.
    property string typedRefusal: ""

    // Return and leaving the field both commit; the second of the two finds nothing new.
    function commit() {
        if (item !== null && text !== field.value) {
            typedRefusal = TypedInput.refusal(text, "number");
            if (typedRefusal === "") {
                item.value = Number(text);
            }
            text = Qt.binding(() => field.value);
        }
    }

    ToolTip.text: refusal
    ToolTip.visible: refusal !== "" && (hovered || activeFocus)
    color: warned ? EaStyle.Colors.red : !enabled || readOnly ? EaStyle.Colors.themeForegroundMinor : item && item.free && canFit ? EaStyle.Colors.chartForegroundsExtra[1] : EaStyle.Colors.themeForeground
    enabled: refinable
    // The value and its uncertainty as text, by the app's one rule for numbers (NumberText).
    parameter: item ? {
        "value": NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0, 10),
        "error": item.hasUncertainty ? NumberText.error(item.uncertainty) : "",
        "enabled": field.refinable,
        "fittable": field.canFit,
        "fit": item.free && field.canFit,
        "category": item.category,
        "name": item.name,
        "shortPrettyName": field.label,
        "units": item.displayUnits
    } : ({})
    warned: refusal !== ""

    // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
    Component.onCompleted: FieldTitles.align(field)
    fitCheckBox.onToggled: if (item !== null)
        item.free = fitCheckBox.checked
    onAccepted: commit()
    onEditingFinished: commit()
    onValueChanged: typedRefusal = ""
}
