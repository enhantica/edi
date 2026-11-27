// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

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
    // A short form per token, shown when the whole name does not fit the box; the list shows the whole names (the owner,
    // 2026-11-23). By default the label registry's for the option (`uid=token`: beam mode's CWL, TOF).
    property var shortForms: ({})
    readonly property string registryShortForm: uid !== "" && token !== "" ? (Session.labelForms(`${uid}=${token}`).shortText ?? "") : ""
    readonly property bool showsResolved: resolved !== "" && token === "auto"
    readonly property real textRoom: width - leftPadding - rightPadding - contentItemLabel.leftPadding - contentItemLabel.rightPadding
    TextMetrics {
        id: choiceMetrics
        font: selector.font
        text: selector.currentText
    }
    // Without a short form of its own, a name with abbreviations in brackets ("... (TCH) + ... (FCJ)") shortens to them.
    readonly property string bracketForm: (currentText.match(/\(([^()]+)\)/g) ?? []).map(part => part.slice(1, -1)).join(" + ")
    readonly property string shortForm: (shortForms[token] ?? "") !== "" ? shortForms[token] : registryShortForm !== "" ? registryShortForm : bracketForm
    displayText: showsResolved ? `${currentText} <font color="${EaStyle.Colors.themeForegroundDisabled}">· ${resolved}</font>` : choiceMetrics.advanceWidth > textRoom && shortForm !== "" ? shortForm : currentText
    // Plain text elides at the box's end; rich text (the resolved choice in grey) cannot, and ran into the next box.
    textFormat: showsResolved ? Text.RichText : Text.PlainText
    elide: Text.ElideRight
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

    // The base's menu item for an option the other choices rule out (OptionListModel's `enabled`): not pickable, and
    // drawn in the disabled colour, which the base's item does not do itself (the owner, 2026-11-16).
    delegate: EaElements.MenuItem {
        required property var model
        required property int index
        readonly property bool allowed: model.enabled !== false
        width: parent !== null ? parent.width : 0
        height: EaStyle.Sizes.comboBoxHeight
        font.family: selector.font.family
        textFormat: Text.RichText
        elide: selector.elide
        text: allowed ? (model.label ?? "") : `<font color="${EaStyle.Colors.themeForegroundDisabled}">${model.label ?? ""}</font>`
        enabled: allowed
        highlighted: selector.highlightedIndex === index
        hoverEnabled: selector.hoverEnabled
    }

    onActivated: index => {
        // A ruled-out option reached by key or wheel is not taken.
        if (options && !options.isEnabled(options.tokenAt(index))) {
            currentIndex = Qt.binding(() => options && options.revision >= 0 ? options.indexOf(selector.token) : -1);
            return;
        }
        ApplicationInfo.activateSelector(index, () => {
            currentIndex = Qt.binding(() => options && options.revision >= 0 ? options.indexOf(selector.token) : -1);
        });
    }
}
