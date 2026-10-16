// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
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
    // Why the value is red: refused, or outside its range. Its own binding, so a cell that gives the attached
    // tooltip help text (the ADP cells) keeps the warning and its style.
    readonly property string warningText: refusal !== "" ? refusal : outsideRange ? qsTr("Outside its range, %1 to %2").arg(item.minimum).arg(item.maximum) : ""
    readonly property bool refinable: item === null || item.refinable
    // A fixed setting is edited but never fitted: no fit toggle.
    readonly property bool canFit: refinable && (item === null || item.fittable)

    // The column's alignment, unless the value is wider than the cell: then it shows from its start and clips at
    // the end, without an ellipsis (ADR-0029).
    property int columnAlignment: Text.AlignHCenter
    // The most significant digits of a value without an uncertainty (NumberText.parameter).
    property int significantDigits: 6
    // With fitDigits, the text is made smaller when its significant digits would not fit the cell, so all of them show
    // (a beta component's small values). Measured at the full size, in the cell's family and weight; only a fitDigits
    // cell measures, as every value change runs these bindings again in every cell.
    property bool fitDigits: false
    readonly property real room: width - leftPadding - rightPadding
    readonly property string fullText: fitDigits && item !== null ? NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0, significantDigits) : ""
    readonly property FontMetrics fullMetrics: FontMetrics {
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        font.bold: cell.fit && cell.enabled
    }
    // Width scales about linearly with the size; the size found is checked once more, as hinting can differ a pixel.
    readonly property int scaledPixelSize: {
        const full = EaStyle.Sizes.fontPixelSize;
        if (!fitDigits || room <= 0)
            return full;
        const needed = fullMetrics.advanceWidth(fullText);
        return needed > room ? Math.max(1, Math.floor(full * room / needed)) : full;
    }
    readonly property FontMetrics scaledMetrics: FontMetrics {
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: cell.scaledPixelSize
        font.bold: cell.fit && cell.enabled
    }
    font.pixelSize: fitDigits && scaledPixelSize > 1 && scaledPixelSize < EaStyle.Sizes.fontPixelSize && scaledMetrics.advanceWidth(fullText) > room ? scaledPixelSize - 1 : scaledPixelSize
    readonly property bool overflows: contentWidth > width - leftPadding - rightPadding
    horizontalAlignment: overflows ? Text.AlignLeft : columnAlignment
    clip: true

    // The value as edited: in full, where the cell shows it rounded (NumberText).
    readonly property string editText: item !== null ? NumberText.full(item.value) : value

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
    color: warned ? EaStyle.Colors.red : !enabled || readOnly ? EaStyle.Colors.themeForegroundMinor : item && item.free && canFit ? EaStyle.Colors.chartForegroundsExtra[1] : EaStyle.Colors.themeForeground

    EaElements.ToolTip {
        text: cell.text
        visible: cell.contentWidth > cell.width && cell.hovered && !cell.activeFocus && !cell.warned && cell.ToolTip.text === "" && EaGlobals.Vars.showToolTips
    }

    enabled: refinable
    // The value and its uncertainty as text, by the app's one rule for numbers in cells (NumberText).
    parameter: item ? {
        "value": NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0, cell.significantDigits),
        "error": item.hasUncertainty ? NumberText.error(item.uncertainty, 0, item.value) : "",
        "enabled": cell.refinable,
        "fittable": cell.canFit,
        "fit": item.free && cell.canFit,
        "category": item.category,
        "name": item.name,
        "units": item.displayUnits
    } : ({})

    warned: warningText !== ""
    ToolTip.text: warningText
    WarningToolTip {
        text: cell.warningText
        visible: cell.warned && (cell.hovered || cell.activeFocus)
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

    // Return and leaving the cell both commit; the second of the two finds nothing new. Text left as shown, rounded or
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
            text = Qt.binding(() => cell.value);
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
            text = Qt.binding(() => cell.value);
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
            if (text !== cell.value && text !== cell.editText) {
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
