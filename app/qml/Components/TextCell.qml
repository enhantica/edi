// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// One editable text cell (the base's ListViewTextInput): shows `value`; `committed` carries what the
// user typed, which the owner writes through its model (the value then comes back from the model). A
// number of a `.edi` item (`uid`) is shown as the project file spells it (edi ADR-0051); the model keeps it
// whole and an unedited cell commits nothing. Names, tokens and whole numbers are shown as they are. A refused commit (text that is not of the kind the cell `accepts`, or
// a value the core refuses) returns the cell to the model's value and shows why, as ParameterField
// does.
EaComponents.ListViewTextInput {
    id: cell

    property var value: ""
    // The item a numeric cell shows, `category.name`.
    property string uid: ""
    // A number as the file spells it (by the app's rule for numbers without an item), in scientific notation when
    // that would not fit the cell (NumberText.fitted; the owner, 2026-10-22), with the file's spelling, or the number
    // in full without an item, on hover.
    readonly property bool numeric: accepts === "number" && typeof value === "number" && isFinite(value)
    readonly property string written: numeric ? (uid !== "" ? Session.written(uid, value) : NumberText.plain(value, 8)) : String(value)
    readonly property string shown: numeric ? NumberText.fitted(written, width - leftPadding - rightPadding, metrics) : written
    // Existing row declarations supply their actual delegate/model/index. The
    // visual parent is the base's internal contentRow, not the data delegate.
    // Original project/row/model/index changes retire a draft's ownership token.
    readonly property var editOwner: Session.project
    property var editMember: null
    property var editModel: null
    property int editIndex: -1
    property string editIdentity: ""
    property var ownerToken: ({})
    property var draft: null
    property var commitInProgress: null
    property var editorLife: ({ alive: true })
    readonly property bool manualEdited: draft !== null && draft.kind === "manual"
    readonly property bool assistantManualDraft: inputMethodComposing ||
        (draft !== null && (draft.kind !== "assistant" || draft.owner !== ownerToken)) ||
        (!assistantEditing && !assistantCommitReady && text !== shown)
    readonly property string editText: shown
    property bool assistantEditing: false
    property bool assistantCommitReady: false

    onEditOwnerChanged: ownerToken = ({})
    onEditMemberChanged: ownerToken = ({})
    onEditModelChanged: ownerToken = ({})
    onEditIndexChanged: ownerToken = ({})
    onEditIdentityChanged: ownerToken = ({})
    onObjectNameChanged: ownerToken = ({})
    onAcceptsChanged: ownerToken = ({})
    onLockedChanged: ownerToken = ({})
    Component.onDestruction: editorLife.alive = false

    function rememberManualDraft() {
        if (assistantEditing && draft !== null && draft.kind === "assistant" && draft.owner === ownerToken)
            return; // Exact paced key path; real takeover cancels it before delivery.
        const life = editorLife;
        const context = ownerToken;
        // Further typing does not retarget an obsolete row's unfinished draft.
        const original = { owner: draft !== null ? draft.owner : ownerToken, kind: "manual" };
        draft = original;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        assistantCommitReady = false;
        if (!life.alive || draft !== original || ownerToken !== context) return;
        assistantEditing = false;
    }
    onTextEdited: rememberManualDraft()
    onInputMethodComposingChanged: if (inputMethodComposing) rememberManualDraft()

    function beginAssistantEdit() {
        if (commitInProgress !== null || draft !== null || assistantManualDraft) return;
        const life = editorLife;
        const originalOwner = ownerToken;
        const original = { owner: originalOwner, kind: "assistant" };
        draft = original;
        if (!life.alive || ownerToken !== originalOwner || draft !== original) return;
        assistantEditing = true;
        if (!life.alive || ownerToken !== originalOwner || draft !== original) return;
        assistantCommitReady = false;
    }
    function allowAssistantCommit() {
        if (commitInProgress !== null || inputMethodComposing || draft === null ||
            draft.kind !== "assistant" || draft.owner !== ownerToken) return;
        const life = editorLife;
        const original = draft;
        assistantCommitReady = true;
        if (!life.alive || draft !== original || original.owner !== ownerToken) return;
        assistantEditing = false;
    }
    function cancelAssistantEdit() {
        if (inputMethodComposing || draft === null || draft.kind !== "assistant" || draft.owner !== ownerToken) return;
        const life = editorLife;
        const original = draft;
        assistantCommitReady = false;
        if (!life.alive || draft !== original || original.owner !== ownerToken) return;
        assistantEditing = false;
        if (!life.alive || draft !== original || original.owner !== ownerToken) return;
        draft = null; // The clean binding resumes only while no commit owns it.
    }
    Keys.onEscapePressed: event => {
        // An explicit human Escape may discard an obsolete/manual draft. Old
        // assistant cleanup has no such permission to touch a newer draft.
        if (commitInProgress !== null || inputMethodComposing) return;
        const life = editorLife;
        const original = draft;
        const originalOwner = ownerToken;
        event.accepted = true;
        assistantCommitReady = false;
        if (!life.alive || draft !== original || ownerToken !== originalOwner) return;
        assistantEditing = false;
        if (!life.alive || draft !== original || ownerToken !== originalOwner) return;
        refusal = "";
        if (!life.alive || draft !== original || ownerToken !== originalOwner) return;
        draft = null;
    }
    // "text", "number" or "integer": what the cell accepts before anything reaches the model.
    property string accepts: "text"
    // Why the last commit was refused; empty once a commit takes or the value changes.
    property string refusal: ""
    // Read-only but shown as usual, not greyed (an auto-estimated background; the owner, 2026-10-20): nothing can be
    // typed or committed.
    property bool locked: false
    signal committed(string text)

    readOnly: locked
    activeFocusOnPress: !locked
    activeFocusOnTab: !locked
    // The base's colours, with a locked cell kept in the normal colour rather than the read-only grey.
    color: enterFlash ? EaStyle.Colors.themeForeground : warned ? EaStyle.Colors.red : !enabled || (readOnly && !locked) || minored ? EaStyle.Colors.themeForegroundMinor : activeFocus || selected || hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground

    // RestoreNone removes the clean binding without assigning text. This is
    // essential for IME preedit, which must survive even before textEdited.
    Binding {
        target: cell
        property: "text"
        value: cell.shown
        when: cell.draft === null && !cell.assistantEditing && !cell.assistantCommitReady &&
              cell.commitInProgress === null && !cell.inputMethodComposing
        restoreMode: Binding.RestoreNone
    }
    warned: refusal !== ""
    ToolTip.text: refusal
    WarningToolTip {
        text: cell.refusal
        visible: text !== "" && (cell.hovered || cell.activeFocus)
    }
    FontMetrics {
        id: metrics
        font: cell.font
    }
    EaElements.ToolTip {
        text: cell.uid !== "" ? cell.written : NumberText.plainFull(cell.value)
        visible: cell.shown !== cell.written && cell.hovered && !cell.activeFocus && !cell.warned && EaGlobals.Vars.showToolTips
    }
    onValueChanged: if (draft === null && commitInProgress === null && !inputMethodComposing) refusal = ""
    // Qt emits editingFinished and then accepted for the SAME Return. Commit
    // only here: accepted keeps the base's visual feedback, and cannot acquire
    // a newer draft admitted during synchronous publication of this edit.
    // A genuine later Return or focus loss has its own editingFinished.
    onEditingFinished: commit()

    // The same original draft can emit only once while its model publishes.
    // Each genuine text/preedit event installs a new record, even identical text.
    function commit() {
        if (commitInProgress !== null || inputMethodComposing || locked) return;
        if (assistantEditing) { cancelAssistantEdit(); return; }
        if (draft === null && !assistantCommitReady) return;
        if (draft === null || draft.owner !== ownerToken) {
            refusal = qsTr("This draft belongs to a different row or project. Escape cancels it.");
            return;
        }
        const life = editorLife;
        const originalOwner = ownerToken;
        const originalProject = editOwner;
        const originalDraft = draft;
        const originalText = text;
        const originalKind = accepts;
        const original = {};
        // Local closures survive receiver destruction without reading its fields.
        const current = () => life.alive && cell.ownerToken === originalOwner &&
            cell.editOwner === originalProject && cell.draft === originalDraft &&
            cell.commitInProgress === original;
        const clearing = () => life.alive && cell.ownerToken === originalOwner &&
            cell.editOwner === originalProject && cell.draft === null &&
            cell.commitInProgress === original;
        commitInProgress = original;
        try {
            if (!current()) return;
            let message = "";
            if (originalText !== shown) {
                message = TypedInput.refusal(originalText, originalKind);
                if (!current()) return;
                if (message === "") {
                    committed(originalText);
                    if (!current()) return;
                    // Never read a replacement project's diagnostic as A's.
                    message = originalProject ? originalProject.lastError : "";
                    if (!current()) return;
                }
            }
            assistantCommitReady = false;
            if (!current()) return;
            assistantEditing = false;
            if (!current()) return;
            draft = null;
            if (!clearing()) return;
            refusal = message;
            // No original presentation writes follow this notifying assignment.
        } finally {
            // Releasing only this original in-progress latch cannot clear B's
            // draft. Binding.when observes any newer draft before resuming.
            if (life.alive && cell.commitInProgress === original)
                cell.commitInProgress = null;
        }
    }
}
