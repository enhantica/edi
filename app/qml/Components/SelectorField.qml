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
    // A help text of the caller's own, shown instead of the dictionary's; set it here, not as `ToolTip.text`, which this
    // component derives so that a refusal and a disabled reason come first.
    property string helpText: ""
    signal selected(string token)
    property var editorLife: ({
            alive: true
        })
    property var activation: null
    Component.onDestruction: ApplicationInfo.editorDestroyed()

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
    currentIndex: options && options.revision >= 0 ? options.indexOf(token) : -1
    // Why the selector is disabled and what enables it, shown instead of its help while it is.
    property string disabledReason: ""
    // The base combo box shows it, and not while its list is open; while refused, the warning below shows instead.
    ToolTip.text: !enabled && disabledReason !== "" ? disabledReason : helpText !== "" ? helpText : uid !== "" ? Session.optionTooltip(uid, token) : ""
    warned: refusal !== ""
    WarningToolTip {
        text: selector.refusal
        requested: toolTipHover.hovered && !selector.popup.visible
    }
    // Reports hover while the selector is disabled too.
    HoverHandler {
        id: toolTipHover
    }

    onTokenChanged: refusal = ""
    // Its title as every field's: left, inset as a combo box's, ending in "…" (edi ADR-0017 §5).
    Component.onCompleted: FieldTitles.align(selector)

    onActivated: index => ApplicationInfo.activateSelector(index, () => {
            currentIndex = Qt.binding(() => options && options.revision >= 0 ? options.indexOf(selector.token) : -1);
        })
}
