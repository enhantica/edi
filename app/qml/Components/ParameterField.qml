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
    // The fit toggle where a fit can vary the value, or while it is free so the flag can be cleared (edi ADR-0053).
    readonly property bool canFit: item === null || item.fittable || item.free
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
    // The value and its uncertainty as the project file and the Text tab spell them (edi ADR-0051); a parameter the
    // dictionary does not know by the app's rule for numbers (NumberText).
    readonly property bool written: item !== null && item.fileValue !== ""
    parameter: item ? {
        "value": written ? item.fileValue : NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0),
        "error": written ? item.fileSu : item.hasUncertainty ? NumberText.error(item.uncertainty, 0, item.value) : "",
        "enabled": field.refinable,
        "fittable": field.canFit,
        "fit": item.free && field.canFit,
        "category": item.category,
        "name": item.name,
        "shortPrettyName": field.label,
        "url": Session.documentationUrl(item.uid).toString(),
        "units": item.displayUnits
    } : ({})

    // The value as edited: the same text, so a field left as it was changes nothing.
    readonly property string editText: written ? item.fileValue : item !== null ? NumberText.full(item.value) : value

    // A value wider than the field shows from its start and clips at the end, without an ellipsis, as a table
    // cell does; it is shown in full while edited.
    onActiveFocusChanged: {
        if (activeFocus) {
            refreshCleanText();
        } else {
            const life = editorLife;
            const originalOwner = ownerToken, originalProject = editOwner, originalItem = item;
            commit();
            if (life.alive && ownerToken === originalOwner && editOwner === originalProject && item === originalItem &&
                !activeFocus && draft === null && commitInProgress === null && !inputMethodComposing)
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
    // The warning, else the item's label and `.edi` name (edi ADR-0051).
    ToolTip.text: warningText !== "" ? warningText : item !== null ? item.toolTip : ""
    ToolTip.visible: ToolTip.text !== "" && !warned && hovered && EaGlobals.Vars.showToolTips
    WarningToolTip {
        text: field.warningText
        visible: field.warned && (field.hovered || field.activeFocus)
    }
    EaElements.ToolTip {
        text: field.hint
        visible: field.hint !== "" && !field.warned && field.hovered && EaGlobals.Vars.showToolTips
    }

    readonly property var editOwner: Session.project
    property var ownerToken: ({})
    property var draft: null
    property var commitInProgress: null
    property var editorLife: ({ alive: true })
    property bool assistantEditing: false
    property bool assistantCommitReady: false
    readonly property bool manualEditing: draft !== null && draft.kind === "manual"
    readonly property ParameterItem manualItem: manualEditing ? draft.item : null
    readonly property ParameterItem manualDraftParameter: manualItem
    readonly property bool assistantManualDraft: inputMethodComposing ||
        (draft !== null && (draft.kind !== "assistant" || draft.owner !== ownerToken))
    onEditOwnerChanged: ownerToken = ({})
    onObjectNameChanged: ownerToken = ({})
    Component.onDestruction: editorLife.alive = false
    onItemChanged: {
        ownerToken = ({});
        if (draft !== null)
            typedRefusal = qsTr("This draft belongs to a different parameter. Escape cancels it.");
        else
            refreshCleanText();
    }
    Binding {
        target: field
        property: "text"
        value: field.activeFocus ? field.editText : field.value
        when: field.draft === null && !field.assistantEditing && !field.assistantCommitReady &&
              field.commitInProgress === null && !field.inputMethodComposing
        restoreMode: Binding.RestoreNone
    }
    function refreshCleanText() {
        // The binding follows raw precision as well as display formatting, and
        // detaches without assigning text while IME or a draft owns the editor.
        if (draft !== null || commitInProgress !== null || inputMethodComposing ||
            assistantEditing || assistantCommitReady) return;
        text = activeFocus ? editText : value;
    }
    function rememberManualDraft() {
        if (assistantEditing && draft !== null && draft.kind === "assistant" && draft.owner === ownerToken)
            return;
        const life = editorLife;
        const context = ownerToken;
        const original = { owner: draft !== null ? draft.owner : ownerToken,
                           item: draft !== null ? draft.item : item, kind: "manual" };
        draft = original;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        assistantCommitReady = false;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        assistantEditing = false;
    }
    onTextEdited: rememberManualDraft()
    onInputMethodComposingChanged: if (inputMethodComposing) rememberManualDraft()
    onValueChanged: if (draft === null && commitInProgress === null && !inputMethodComposing) typedRefusal = ""
    onEditTextChanged: refreshCleanText()
    function beginAssistantEdit() {
        if (commitInProgress !== null || draft !== null || assistantManualDraft) return;
        const life = editorLife;
        const originalOwner = ownerToken;
        const original = { owner: originalOwner, item: item, kind: "assistant" };
        draft = original;
        if (!life.alive || ownerToken !== originalOwner || draft !== original) return;
        assistantEditing = true;
        if (!life.alive || ownerToken !== originalOwner || draft !== original) return;
        assistantCommitReady = false;
    }
    function allowAssistantCommit() {
        if (commitInProgress !== null || inputMethodComposing || draft === null ||
            draft.kind !== "assistant" || draft.owner !== ownerToken || draft.item !== item) return;
        const life = editorLife;
        const original = draft;
        assistantCommitReady = true;
        if (!life.alive || draft !== original || original.owner !== ownerToken) return;
        assistantEditing = false;
    }
    function resetEditorText() {
        if (commitInProgress !== null || inputMethodComposing) return;
        const life = editorLife;
        const original = draft;
        const context = ownerToken;
        assistantCommitReady = false;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        assistantEditing = false;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        typedRefusal = "";
        if (!life.alive || draft !== original || ownerToken !== context) return;
        draft = null;
    }
    function cancelAssistantEdit() {
        if (draft !== null && draft.kind === "assistant" && draft.owner === ownerToken && draft.item === item)
            resetEditorText();
    }
    Keys.onEscapePressed: event => {
        if (commitInProgress !== null || inputMethodComposing) return;
        event.accepted = true;
        resetEditorText();
    }
    // editingFinished owns Return as well as focus loss; accepted is the same
    // Return's second signal and cannot acquire a successor draft.
    onEditingFinished: commit()
    function commit() {
        if (commitInProgress !== null || inputMethodComposing) return;
        if (assistantEditing) { cancelAssistantEdit(); return; }
        if (draft === null && !assistantCommitReady) return;
        if (draft === null || draft.owner !== ownerToken || draft.item !== item || item === null) {
            typedRefusal = qsTr("This draft no longer belongs to the displayed parameter. Escape cancels it.");
            return;
        }
        const life = editorLife;
        const originalOwner = ownerToken;
        const originalProject = editOwner;
        const originalDraft = draft;
        const originalItem = item;
        const originalText = text;
        const original = {};
        const current = () => life.alive && field.ownerToken === originalOwner &&
            field.editOwner === originalProject && field.item === originalItem &&
            field.draft === originalDraft && field.commitInProgress === original;
        const clearing = () => life.alive && field.ownerToken === originalOwner &&
            field.editOwner === originalProject && field.item === originalItem &&
            field.draft === null && field.commitInProgress === original;
        commitInProgress = original;
        try {
            if (!current()) return;
            let message = "";
            if (originalText !== value && originalText !== editText) {
                message = TypedInput.refusal(originalText, "number");
                if (!current()) return;
                if (message === "") {
                    originalItem.value = Number(originalText);
                    if (!current()) return;
                    message = originalItem.lastError;
                    if (!current()) return;
                }
            }
            assistantCommitReady = false;
            if (!current()) return;
            assistantEditing = false;
            if (!current()) return;
            draft = null;
            if (!clearing()) return;
            typedRefusal = message;
        } finally {
            if (life.alive && field.commitInProgress === original)
                field.commitInProgress = null;
        }
    }
    onFitToggled: checked => {
        if (item !== null)
            item.free = checked;
    }
}
