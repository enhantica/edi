// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

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

    // The base takes its row's height; a cell made or dropped without a row yet has none.
    height: parent ? parent.height : 0

    property var value: ""
    // The item a numeric cell shows, `category.name`.
    property string uid: ""
    // A number as the file spells it (by the app's rule for numbers without an item), in scientific notation when
    // that would not fit the cell (NumberText.fitted; the owner, 2026-10-22), with the file's spelling, or the number
    // in full without an item, on hover.
    readonly property bool numeric: accepts === "number" && typeof value === "number" && isFinite(value)
    // A read-only value the program computed (an output category's) is shown by its item's display format instead, as
    // every read-only surface is (edi ADR-0051): rounded, so a value within rounding of zero reads as zero.
    property bool displayed: false
    readonly property string written: numeric ? (uid !== "" ? (displayed ? Session.display(uid, value) : Session.written(uid, value)) : NumberText.plain(value, 8)) : String(value)
    readonly property real room: width - leftPadding - rightPadding
    // Like ParameterCell, do not bind displayed text back to its own implicit width.
    property string shownValue: written
    readonly property string shown: shownValue
    function refit() {
        ApplicationInfo.textCellRefit();
    }
    onRoomChanged: refit()
    onWrittenChanged: refit()
    onNumericChanged: refit()
    Component.onCompleted: refit()
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
    property var editorLife: ({
            alive: true
        })
    readonly property bool manualEdited: draft !== null && draft.kind === "manual"
    readonly property bool assistantManualDraft: inputMethodComposing || (draft !== null && (draft.kind !== "assistant" || draft.owner !== ownerToken)) || (!assistantEditing && !assistantCommitReady && text !== shown)
    readonly property string editText: shown
    property bool assistantEditing: false
    property bool assistantCommitReady: false

    onEditOwnerChanged: ApplicationInfo.editorRetireOwner()
    onEditMemberChanged: ApplicationInfo.editorRetireOwner()
    onEditModelChanged: ApplicationInfo.editorRetireOwner()
    onEditIndexChanged: ApplicationInfo.editorRetireOwner()
    onEditIdentityChanged: ApplicationInfo.editorRetireOwner()
    onObjectNameChanged: ApplicationInfo.editorRetireOwner()
    onAcceptsChanged: ApplicationInfo.editorRetireOwner()
    onLockedChanged: ApplicationInfo.editorRetireOwner()
    Component.onDestruction: ApplicationInfo.editorDestroyed()

    function rememberManualDraft() {
        ApplicationInfo.editorRememberDraft(ApplicationInfo.TextCellEditor);
    }
    onTextEdited: rememberManualDraft()
    onInputMethodComposingChanged: ApplicationInfo.editorCompositionChanged(ApplicationInfo.TextCellEditor)

    function beginAssistantEdit() {
        ApplicationInfo.editorBeginAssistantEdit(ApplicationInfo.TextCellEditor);
    }
    function allowAssistantCommit() {
        ApplicationInfo.editorAllowAssistantCommit(ApplicationInfo.TextCellEditor);
    }
    function cancelAssistantEdit() {
        ApplicationInfo.editorCancelAssistantEdit(ApplicationInfo.TextCellEditor);
    }
    function cancelTextEdit(event) {
        ApplicationInfo.editorEscape(ApplicationInfo.TextCellEditor, event);
    }
    // As wide as the whole number, not the shown text: a cell no table has sized (DataTable's measuring rows) takes this
    // width, and a width that followed `shown` would feed back into it.
    implicitWidth: Math.ceil(metrics.advanceWidth(written)) + leftPadding + rightPadding
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
        when: cell.draft === null && !cell.assistantEditing && !cell.assistantCommitReady && cell.commitInProgress === null && !cell.inputMethodComposing
        restoreMode: Binding.RestoreNone
    }
    warned: refusal !== ""
    ToolTip.text: refusal
    // The tooltips are made only when they can show: a table makes and drops whole rows to measure them, and a
    // popup per cell was a third of a row's cost.
    Loader {
        anchors.fill: parent
        active: cell.refusal !== "" && (cell.hovered || cell.activeFocus)
        sourceComponent: Component {
            WarningToolTip {
                text: cell.refusal
                visible: text !== "" && (cell.hovered || cell.activeFocus)
            }
        }
    }
    FontMetrics {
        id: metrics
        font: cell.font
        onFontChanged: cell.refit()
    }
    Loader {
        anchors.fill: parent
        active: cell.hovered && !cell.activeFocus && !cell.warned && EaGlobals.Vars.showToolTips
        sourceComponent: Component {
            EaElements.ToolTip {
                text: cell.uid !== "" && !cell.displayed ? cell.written : NumberText.plainFull(cell.value)
                visible: cell.shown !== cell.written && cell.hovered && !cell.activeFocus && !cell.warned && EaGlobals.Vars.showToolTips
            }
        }
    }
    onValueChanged: ApplicationInfo.editorValueChanged(ApplicationInfo.TextCellEditor)
    // Qt emits editingFinished and then accepted for the SAME Return. Commit
    // only here: accepted keeps the base's visual feedback, and cannot acquire
    // a newer draft admitted during synchronous publication of this edit.
    // A genuine later Return or focus loss has its own editingFinished.
    onEditingFinished: commit()
    // A double click selects the whole text, as the app's other text fields do (the owner, 2026-11-04).
    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !cell.locked
        onDoubleTapped: cell.selectAll()
    }

    // The same original draft can emit only once while its model publishes.
    // Each genuine text/preedit event installs a new record, even identical text.
    function commit() {
        ApplicationInfo.editorCommit(ApplicationInfo.TextCellEditor);
    }
}
