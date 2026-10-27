// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A category's type selector: the base's ParamComboBox over the core's supported options for the
// block's type, showing the stored token. `selected` carries the token the user chose; the owner
// writes it through the view-model's core call. A refused choice returns the selector to the
// stored token and shows the core's message, as ParameterField does. A selector of a `.edi` item names it by `uid`:
// its label comes from crysta's dictionary and its tooltip names the item and the token stored (edi ADR-0051).
EaElements.ParamComboBox {
    id: selector

    required property OptionListModel options
    property string uid: ""
    property string label: uid !== "" ? Session.label(uid) : ""
    property string token: ""
    property bool writable: true
    // Why the last choice was refused; empty once a choice takes or the token changes.
    property string refusal: ""
    // What `auto` resolves to, shown after it in grey ("auto · arpls"); empty shows the choice alone.
    property string resolved: ""
    // A help text set as `ToolTip.text` shows in the app's tooltip on hover, unless a refusal is shown.
    property bool helpToolTip: false
    signal selected(string token)
    property var editorLife: ({ alive: true })
    property var activation: null
    Component.onDestruction: editorLife.alive = false

    // Shares the row's width with its siblings at the input spacing, as ParamTextField does (the base's
    // ParamComboBox assumes a wider gap).
    width: (EaStyle.Sizes.sideBarContentWidth - (parent.children.length - 1) * AppSizes.inputSpacing) / parent.children.length
    parameter: ({
            "value": selector.token,
            "shortPrettyName": selector.label
        })
    model: options
    textRole: "label"
    displayText: resolved !== "" && token === "auto" ? `${currentText} <font color="${EaStyle.Colors.themeForegroundDisabled}">· ${resolved}</font>` : currentText
    valueRole: "token"
    enabled: writable && options !== null && options.count > 0
    currentIndex: options ? options.indexOf(token) : -1
    ToolTip.text: uid !== "" ? Session.optionTooltip(uid, token) : ""
    ToolTip.visible: ToolTip.text !== "" && hovered && refusal === "" && EaGlobals.Vars.showToolTips
    WarningToolTip {
        text: selector.refusal
        visible: text !== "" && selector.hovered
    }
    // The app's tooltip, never the attached one Qt draws in its own style.
    EaElements.ToolTip {
        text: selector.ToolTip.text
        visible: selector.helpToolTip && text !== "" && selector.refusal === "" && selector.hovered && EaGlobals.Vars.showToolTips
    }

    onTokenChanged: refusal = ""
    // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
    Component.onCompleted: FieldTitles.align(selector)

    onActivated: index => {
        const life = editorLife;
        const originalOwner = Session.project;
        const originalOptions = options;
        const original = ({});
        activation = original;
        const current = () => life.alive && selector.activation === original && Session.project === originalOwner && selector.options === originalOptions;
        if (!current() || originalOptions === null) return;
        const chosen = originalOptions.tokenAt(index);
        if (!current()) return;
        if (chosen !== token) {
            selected(chosen);
            if (!current()) return;
            const message = originalOwner ? originalOwner.lastError : "";
            if (!current()) return;
            refusal = message;
            if (!current()) return;
        }
        currentIndex = Qt.binding(() => options ? options.indexOf(selector.token) : -1);
    }
}
