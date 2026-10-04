// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// One parameter as a table cell (the base's TableViewParameter, as the original's tables use it): the
// value rounded by its uncertainty, bold when free, the vary toggle in the context menu; a typed value
// goes through the core (ParameterItem.value -> assign_value); a refused one (typed text that is not a
// number, or a value the core refuses) shows why and the cell returns to the model's value, as
// ParameterField does; and, as there, a parameter the space group fixes or ties (edi ADR-0019) is shown
// disabled, with the value symmetry implies. A value outside its admissible range — a fit writes its
// values unchecked — is red, its tooltip naming the range.
EaComponents.TableViewParameter {
    id: cell

    property ParameterItem item: null
    // Why the last typed text was refused before reaching the core; the core's own refusal is the item's.
    property string typedRefusal: ""
    readonly property string refusal: typedRefusal !== "" ? typedRefusal : item !== null ? item.lastError : ""
    readonly property bool outsideRange: item !== null && item.outsideRange
    readonly property bool refinable: item === null || item.refinable

    enabled: refinable
    parameter: item ? {
        "value": item.value,
        "error": item.hasUncertainty ? item.uncertainty : 0,
        "enabled": cell.refinable,
        "fittable": cell.refinable,
        "fit": item.free && cell.refinable,
        "category": item.category,
        "name": item.name,
        "units": item.displayUnits
    } : ({})

    warned: refusal !== "" || outsideRange
    ToolTip.text: refusal !== "" ? refusal : outsideRange ? qsTr("Outside its range, %1 to %2").arg(item.minimum).arg(item.maximum) : ""
    ToolTip.visible: ToolTip.text !== "" && (hovered || activeFocus)

    onValueChanged: typedRefusal = ""
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the cell both commit; the second of the two finds nothing new.
    function commit() {
        if (item !== null && text !== cell.value) {
            typedRefusal = TypedInput.refusal(text, "number");
            if (typedRefusal === "") {
                item.value = Number(text);
            }
            text = Qt.binding(() => cell.value);
        }
    }
    fitCheckBox.onToggled: if (item !== null)
        item.free = fitCheckBox.checked
}
