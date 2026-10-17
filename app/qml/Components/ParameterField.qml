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

    required property ParameterItem item
    property string label: item ? item.shortName : ""
    // Why the last typed text was refused before reaching the core; the core's own refusal is the item's.
    property string typedRefusal: ""
    readonly property string refusal: typedRefusal !== "" ? typedRefusal : item !== null ? item.lastError : ""
    readonly property bool refinable: item === null || item.refinable
    // A fixed setting is edited but never fitted: no fit toggle.
    readonly property bool canFit: refinable && (item === null || item.fittable)
    // A value outside its range (a fit writes its values unchecked) is red with the range, as in a table cell.
    readonly property bool outsideRange: item !== null && item.outsideRange
    readonly property string warningText: refusal !== "" ? refusal : outsideRange ? qsTr("Outside its range, %1 to %2").arg(item.minimum).arg(item.maximum) : ""

    color: warned ? EaStyle.Colors.red : !enabled || readOnly ? EaStyle.Colors.themeForegroundMinor : item && item.free && canFit ? EaStyle.Colors.chartForegroundsExtra[1] : EaStyle.Colors.themeForeground

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
        if (activeFocus) {
            refreshCleanText();
        } else {
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

    onValueChanged: {
        typedRefusal = "";
        refreshCleanText();
    }
    onEditTextChanged: refreshCleanText()
    onItemChanged: {
        if (manualEditing && manualItem !== item)
            typedRefusal = qsTr("This draft belongs to a different parameter. Escape cancels it without applying it.");
        else
            refreshCleanText();
    }
    onInputMethodComposingChanged: {
        if (inputMethodComposing && !assistantEditing) {
            if (!manualEditing)
                manualItem = item;
            manualEditing = true;
            // Do not assign text here: that would destroy the IME preedit.
        }
    }
    // textEdited is real text input, unlike focus formatting or model publication.
    onTextEdited: {
        if (assistantEditing)
            return;
        if (!manualEditing)
            manualItem = item;
        manualEditing = true;
        // TextInput editing can retain a QML binding. Detach only the genuine
        // user draft so unrelated publication cannot replace what was typed.
        const draft = text;
        text = draft;
    }
    Keys.onEscapePressed: event => {
        resetEditorText();
        event.accepted = true;
    }
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the field both commit; the second of the two finds nothing new. Text left as shown, rounded or
    // in full, changes nothing.
    // Host-owned cancellation restores the current committed model binding,
    // never the old pre-animation number or a newer manual model edit.
    property bool assistantEditing: false
    property bool assistantCommitReady: false
    property bool manualEditing: false
    property ParameterItem manualItem: null
    readonly property bool assistantManualDraft: manualEditing || inputMethodComposing
    // The Analysis slider uses the exact draft owner, including a recycled cell.
    readonly property ParameterItem manualDraftParameter: manualEditing ? manualItem : null
    property bool committing: false
    function refreshCleanText() {
        if (manualEditing || inputMethodComposing || assistantEditing || assistantCommitReady)
            return;
        // Raw editText changes refresh a clean focused spelling, even when its
        // rounded display is unchanged. No live binding can replace IME preedit.
        if (activeFocus)
            text = editText;
        else
            text = Qt.binding(() => field.value);
    }
    function resetEditorText() {
        manualEditing = false;
        manualItem = null;
        assistantCommitReady = false;
        // Keep the assistant partial-text guard until the authoritative binding
        // is back. This never writes an old pre-slider value to science.
        if (activeFocus)
            text = editText;
        else
            text = Qt.binding(() => field.value);
        typedRefusal = "";
        deselect();
        if (!activeFocus)
            cursorPosition = 0;
        assistantEditing = false;
    }
    function beginAssistantEdit() {
        assistantEditing = true;
        assistantCommitReady = false;
        const draft = text;
        text = draft;
    }
    function allowAssistantCommit() {
        assistantCommitReady = true;
        assistantEditing = false;
    }
    function cancelAssistantEdit() {
        // An original real manual event may already own this editor. A late
        // assistant cleanup never clears that new user's genuine draft.
        if (!manualEditing)
            resetEditorText();
    }
    function commit() {
        if (committing || inputMethodComposing)
            return;
        // Focus loss while paced typing is not permission to commit a partial number.
        if (assistantEditing) { cancelAssistantEdit(); return; }
        // Clean full-precision display is never a user edit, even if the model
        // changed after focus (slider/fit/Undo/SU refresh).
        if (!manualEditing && !assistantCommitReady) { refreshCleanText(); return; }
        if (item === null || (manualEditing && manualItem !== item)) {
            typedRefusal = qsTr("This draft no longer belongs to the displayed parameter. Escape cancels it.");
            return;
        }
        committing = true;
        try {
            if (text !== field.value && text !== field.editText) {
                typedRefusal = TypedInput.refusal(text, "number");
                if (typedRefusal === "")
                    item.value = Number(text);
            }
            const refusal = typedRefusal;
            resetEditorText();
            typedRefusal = refusal;
        } finally { committing = false; }
    }
    onFitToggled: checked => {
        if (item !== null)
            item.free = checked;
    }
}
