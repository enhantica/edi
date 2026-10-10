// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A category's type selector: the base's ParamComboBox over the core's supported options for the
// block's type, showing the stored token. `selected` carries the token the user chose; the owner
// writes it through the view-model's core call. A refused choice returns the selector to the
// stored token and shows the core's message, as ParameterField does.
EaElements.ParamComboBox {
    id: selector

    required property OptionListModel options
    property string label: ""
    property string token: ""
    property bool writable: true
    // Why the last choice was refused; empty once a choice takes or the token changes.
    property string refusal: ""
    signal selected(string token)

    // Shares the row's width with its siblings at the input spacing, as ParamTextField does (the base's
    // ParamComboBox assumes a wider gap).
    width: (EaStyle.Sizes.sideBarContentWidth - (parent.children.length - 1) * AppSizes.inputSpacing) / parent.children.length
    parameter: ({
            "value": selector.token,
            "shortPrettyName": selector.label
        })
    model: options
    textRole: "label"
    valueRole: "token"
    enabled: writable && options !== null && options.count > 0
    currentIndex: options ? options.indexOf(token) : -1
    ToolTip.text: refusal
    WarningToolTip {
        text: selector.refusal
        visible: text !== "" && selector.hovered
    }

    onTokenChanged: refusal = ""
    // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
    Component.onCompleted: FieldTitles.align(selector)

    onActivated: index => {
        const chosen = options.tokenAt(index);
        if (chosen !== token) {
            selected(chosen);
            refusal = Session.project ? Session.project.lastError : "";
        }
        currentIndex = Qt.binding(() => options ? options.indexOf(selector.token) : -1);
    }
}
