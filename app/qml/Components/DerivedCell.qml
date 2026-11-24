// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A value derived from fitted ones (|M|, θ, ϕ, a weight fraction), as a table cell: its value alone, never
// "value(s.u.)"; a click opens the parameter popup with the full value and its s.u., the Free box disabled, as it cannot
// be fitted (the owner, 2026-11-23; ADR-0103 F3a). A value the app converts back (a moment's component in another form)
// is typed into the popup and committed.
EaComponents.ListViewParameter {
    id: cell

    property string shownValue: ""
    property string fullValue: ""
    property string uncertainty: ""
    // The name the popup shows: its `.edi` full name, where it is an item.
    property string derivedName: ""
    // The item's `.edi` identity, `category.name`, for its documentation link.
    property string uid: ""
    property string derivedUnits: ""
    // Typed into the popup, starting from `editText`, a number.
    property bool editable: false
    property string editText: ""
    signal committed(real number)
    property int columnAlignment: Text.AlignRight

    // The value as its column has room for it: fewer digits, then ×10ⁿ, never cut. Set from the changes it follows, and
    // the cell as wide as the whole value until its table sizes it (as ParameterCell).
    property string fittedValue: shownValue
    function refit() {
        const unit = shownValue.endsWith("\u00b0") ? "\u00b0" : "";
        fittedValue = width > 0 && Math.abs(width - implicitWidth) >= 0.5 ? NumberText.fitted(shownValue.slice(0, shownValue.length - unit.length), width - leftPadding - rightPadding - cellMetrics.advanceWidth(unit), cellMetrics) + unit : shownValue;
    }
    implicitWidth: Math.ceil(cellMetrics.advanceWidth(shownValue)) + leftPadding + rightPadding
    onShownValueChanged: refit()
    onWidthChanged: refit()
    onLeftPaddingChanged: refit()
    onRightPaddingChanged: refit()
    Component.onCompleted: refit()
    FontMetrics {
        id: cellMetrics
        font: cell.font
    }

    errorTitle: qsTr("s.u.")
    fitTitle: qsTr("Free")
    horizontalAlignment: columnAlignment
    parameter: ({
            "value": cell.fittedValue,
            "error": cell.uncertainty,
            "fittable": true,
            "fit": false,
            "enabled": true,
            "fullName": cell.derivedName,
            "units": cell.derivedUnits,
            "url": cell.uid !== "" ? Session.documentationUrl(cell.uid).toString() : ""
        })
    menuValue: fullValue !== "" ? fullValue : shownValue
    clickOpensMenu: shownValue !== "" && (editable || shownValue !== "—")
    // Nothing is typed into the cell itself.
    readOnly: true
    color: !enabled ? EaStyle.Colors.themeForegroundMinor : hovered || activeFocus ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
    activeFocusOnPress: false
    activeFocusOnTab: editable
    Keys.onReturnPressed: if (clickOpensMenu)
        openContextMenu(cell)
    Binding {
        target: cell.fitCheckBox
        when: cell.fitCheckBox !== null
        property: "enabled"
        value: false
    }
    Loader {
        anchors.fill: parent
        active: cell.hovered && cell.ToolTip.text !== ""
        sourceComponent: Component {
            EaElements.ToolTip {
                text: cell.ToolTip.text
                requested: cell.hovered
            }
        }
    }
    editorComponent: Component {
        EaElements.TextField {
            id: field

            objectName: cell.objectName + ".popup.value"
            // The unit inside the field, as in a parameter's own popup.
            rightPadding: unit.width
            readOnly: !cell.editable
            readonly property real room: width - leftPadding - rightPadding
            fullText: cell.menuValue
            shortened: !activeFocus && text !== fullText
            property string refusal: ""
            warned: refusal !== ""
            onTextEdited: refusal = ""
            onAccepted: focus = false
            // Escape drops the draft before the menu closes, which would otherwise commit it.
            Keys.onShortcutOverride: event => {
                if (event.key === Qt.Key_Escape && cell.editable)
                    text = cell.editText;
            }
            Binding {
                target: field
                property: "text"
                value: cell.editable ? cell.editText : NumberText.fitted(cell.menuValue, field.room, valueMetrics)
            }
            onEditingFinished: {
                if (!cell.editable || text === cell.editText)
                    return;
                refusal = TypedInput.refusal(text, "number");
                if (refusal === "")
                    cell.committed(Number(text));
                text = cell.editText;
            }
            FontMetrics {
                id: valueMetrics
                font: field.font
            }
            PlaceholderText {
                id: unit
                x: field.width - width
                height: field.height
                leftPadding: text !== "" ? EaStyle.Sizes.fontPixelSize * 0.5 : 0
                rightPadding: EaStyle.Sizes.fontPixelSize * 0.75
                verticalAlignment: Text.AlignVCenter
                font.family: field.font.family
                font.pixelSize: field.font.pixelSize
                color: field.placeholderTextColor
                text: cell.units
                textFormat: Text.RichText
            }
            WarningToolTip {
                text: field.refusal
                requested: field.warned && (field.hovered || field.activeFocus)
            }
        }
    }
}
