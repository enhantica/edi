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
        "units": item.displayUnits
    } : ({})

    // The value as edited: the same text, so a field left as it was changes nothing.
    readonly property string editText: written ? item.fileValue : item !== null ? NumberText.full(item.value) : value

    // A value wider than the field shows from its start and clips at the end, without an ellipsis, as a table
    // cell does; it is shown in full while edited.
    onActiveFocusChanged: ApplicationInfo.parameterEditorFocusChanged(ApplicationInfo.ParameterFieldEditor)
    onTextChanged: ApplicationInfo.editorTextChanged()
    Component.onCompleted: ApplicationInfo.parameterEditorCompleted()

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
    property var editorLife: ({
            alive: true
        })
    property bool assistantEditing: false
    property bool assistantCommitReady: false
    readonly property bool manualEditing: draft !== null && draft.kind === "manual"
    readonly property ParameterItem manualItem: manualEditing ? draft.item : null
    readonly property ParameterItem manualDraftParameter: manualItem
    readonly property bool assistantManualDraft: inputMethodComposing || (draft !== null && (draft.kind !== "assistant" || draft.owner !== ownerToken))
    onEditOwnerChanged: ApplicationInfo.editorRetireOwner()
    onObjectNameChanged: ApplicationInfo.editorRetireOwner()
    Component.onDestruction: ApplicationInfo.editorDestroyed()
    onItemChanged: ApplicationInfo.parameterEditorItemChanged(ApplicationInfo.ParameterFieldEditor)
    Binding {
        target: field
        property: "text"
        value: field.activeFocus ? field.editText : field.value
        when: field.draft === null && !field.assistantEditing && !field.assistantCommitReady && field.commitInProgress === null && !field.inputMethodComposing
        restoreMode: Binding.RestoreNone
    }
    function refreshCleanText() {
        ApplicationInfo.editorRefreshCleanText();
    }
    function rememberManualDraft() {
        ApplicationInfo.editorRememberDraft(ApplicationInfo.ParameterFieldEditor);
    }
    onTextEdited: rememberManualDraft()
    onInputMethodComposingChanged: ApplicationInfo.editorCompositionChanged(ApplicationInfo.ParameterFieldEditor)
    onValueChanged: ApplicationInfo.editorValueChanged(ApplicationInfo.ParameterFieldEditor)
    onEditTextChanged: refreshCleanText()
    function beginAssistantEdit() {
        ApplicationInfo.editorBeginAssistantEdit(ApplicationInfo.ParameterFieldEditor);
    }
    function allowAssistantCommit() {
        ApplicationInfo.editorAllowAssistantCommit(ApplicationInfo.ParameterFieldEditor);
    }
    function resetEditorText() {
        ApplicationInfo.parameterEditorReset();
    }
    function cancelAssistantEdit() {
        ApplicationInfo.editorCancelAssistantEdit(ApplicationInfo.ParameterFieldEditor);
    }
    Keys.onEscapePressed: event => ApplicationInfo.editorEscape(ApplicationInfo.ParameterFieldEditor, event)
    // editingFinished owns Return as well as focus loss; accepted is the same
    // Return's second signal and cannot acquire a successor draft.
    onEditingFinished: commit()
    function commit() {
        ApplicationInfo.editorCommit(ApplicationInfo.ParameterFieldEditor);
    }
    onFitToggled: checked => ApplicationInfo.parameterEditorFitToggled(checked)
}
