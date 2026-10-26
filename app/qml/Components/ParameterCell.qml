// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// One parameter as a table cell (the base's ListViewParameter, as the original's tables use its TableViewParameter): the
// value rounded by its uncertainty, bold when free, the vary toggle in the context menu; a typed value
// goes through the core (ParameterItem.value -> assign_value); a refused one (typed text that is not a
// number, or a value the core refuses) shows why and the cell returns to the model's value, as
// ParameterField does; and, as there, a parameter the space group fixes or ties (edi ADR-0019) is shown
// disabled, with the value symmetry implies. A value outside its admissible range — a fit writes its
// values unchecked — is red, its tooltip naming the range.
EaComponents.ListViewParameter {
    id: cell

    errorTitle: qsTr("s.u.")
    fitTitle: qsTr("free")

    property ParameterItem item: null
    // The value shown as usual, free in green bold, with its context menu (free or fixed), but not typed into: an
    // auto-estimated background's points or terms (the owner, 2026-10-20). readOnly would grey it and hide the toggle.
    property bool locked: false
    activeFocusOnPress: !locked
    activeFocusOnTab: !locked
    // Why the last typed text was refused before reaching the core; the core's own refusal is the item's.
    property string typedRefusal: ""
    readonly property string refusal: typedRefusal !== "" ? typedRefusal : item !== null ? item.lastError : ""
    readonly property bool outsideRange: item !== null && item.outsideRange
    // Why the value is red: refused, or outside its range. Its own binding, so a cell that gives the attached
    // tooltip help text (the ADP cells) keeps the warning and its style.
    readonly property string warningText: refusal !== "" ? refusal : outsideRange ? qsTr("Outside its range, %1 to %2").arg(item.minimum).arg(item.maximum) : item !== null ? item.domainWarning : ""
    readonly property bool refinable: item === null || item.refinable
    // A fixed setting is edited but never fitted: no fit toggle.
    readonly property bool canFit: refinable && (item === null || item.fittable)
    // Without measured data in any experiment nothing is fitted, so the free toggle is disabled (edi ADR-0046).
    readonly property bool measured: Session.project === null || Session.project.fit.measured
    Binding {
        target: cell.fitCheckBox
        when: cell.fitCheckBox !== null
        property: "enabled"
        value: cell.measured
    }

    // The column's alignment, unless the value is wider than the cell: then it shows from its start and clips at
    // the end, without an ellipsis (ADR-0029).
    property int columnAlignment: Text.AlignHCenter
    // The most significant digits of a value without an uncertainty (NumberText.parameter).
    property int significantDigits: 6
    // With fitDigits, the text is made smaller when its significant digits would not fit the cell, so all of them show
    // (a beta component's small values). Measured at the full size, in the cell's family and weight; only a fitDigits
    // cell measures for this, as every value change runs these bindings again in every cell.
    property bool fitDigits: false
    readonly property real room: width - leftPadding - rightPadding
    // The value as its rule writes it, and as the cell shows it: in scientific notation when that text would not fit
    // (NumberText.fitted; the owner, 2026-10-22), unless the cell makes its text smaller instead (fitDigits). Measured
    // in the shown weight, read from the item: the `parameter` map that sets the weight is made from this text.
    // The value as the project file and the Text tab spell it (edi ADR-0051); a parameter the dictionary does not know
    // by the app's rule for numbers.
    readonly property bool written: item !== null && item.fileValue !== ""
    readonly property string valueText: written ? item.fileValue : item !== null ? NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0, significantDigits) : ""
    // Its scientific form: the written token's own digits, every one of them (NumberText.compact); without one, digits
    // that follow the uncertainty and the project's rule when the plain text does not change (9e5 or 9.0e5 for
    // 900000 ± 200000).
    readonly property string narrowText: item === null || fitDigits ? "" : written ? NumberText.compact(item.fileValue) : NumberText.narrowParameter(item.value, item.hasUncertainty ? item.uncertainty : 0, significantDigits)
    // Set from the changes it follows rather than bound, and only once the table has given the cell its column's width:
    // until then the cell is as wide as its own text, which fits, and following that width back to the text would loop.
    property string shownValue: valueText
    function refit() {
        const sized = Math.abs(width - implicitWidth) >= 0.5;
        shownValue = fitDigits || !sized || item === null ? valueText : NumberText.fitted(valueText, room, shownMetrics, narrowText);
    }
    onRoomChanged: refit()
    onValueTextChanged: refit()
    onNarrowTextChanged: refit()
    onFontChanged: refit()
    Component.onCompleted: refit()
    readonly property FontMetrics shownMetrics: FontMetrics {
        font: cell.font
    }
    readonly property string fullText: fitDigits ? valueText : ""
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

    // The value as edited: the same text, so a cell left as it was changes nothing.
    readonly property string editText: written ? item.fileValue : item !== null ? NumberText.full(item.value) : value

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
    // A free value is in the status bar's green, the one green token (EaStyle.Colors.green; the owner, 2026-10-22).
    color: warned ? EaStyle.Colors.red : !enabled || readOnly ? EaStyle.Colors.themeForegroundMinor : item && item.free && canFit ? EaStyle.Colors.green : EaStyle.Colors.themeForeground

    // On hover: the value as written when the cell shows it shorter or clipped, else the item's label and `.edi` name
    // (edi ADR-0051).
    EaElements.ToolTip {
        text: cell.shownValue !== cell.valueText ? (cell.written ? cell.valueText : NumberText.plainFull(cell.item.value)) : cell.contentWidth > cell.width ? cell.text : cell.item !== null ? cell.item.toolTip : ""
        visible: text !== "" && cell.hovered && !cell.activeFocus && !cell.warned && cell.ToolTip.text === "" && EaGlobals.Vars.showToolTips
    }

    enabled: refinable
    // The value and its uncertainty as text, by the app's one rule for numbers in cells (NumberText).
    parameter: item ? {
        "value": cell.shownValue,
        "error": cell.written ? item.fileSu : item.hasUncertainty ? NumberText.error(item.uncertainty, 0, item.value) : "",
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

    onValueChanged: typedRefusal = ""
    onAccepted: commit()
    onEditingFinished: commit()

    // Return and leaving the cell both commit; the second of the two finds nothing new. Text left as shown, rounded or
    // in full, changes nothing.
    function commit() {
        if (item === null)
            return;
        if (locked) {
            text = Qt.binding(() => cell.value);
            return;
        }
        if (text !== cell.value && text !== cell.editText) {
            typedRefusal = TypedInput.refusal(text, "number");
            if (typedRefusal === "") {
                item.value = Number(text);
            }
        }
        text = Qt.binding(() => cell.value);
    }
    onFitToggled: checked => {
        if (item !== null)
            item.free = checked;
    }
}
