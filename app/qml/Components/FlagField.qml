// SPDX-License-Identifier: BSD-3-Clause
// A true/false item as a field: the value field's box with its title above, as every field has, and a check box inside
// in place of the text. Read only, it is styled as a read-only value field is. Every flag a group shows uses it, so
// none shows true or false as text and none draws its label beside the box.
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

EaElements.ParamTextField {
    id: flag

    property string uid: ""
    property string label: uid !== "" ? Session.label(uid) : ""
    property bool checked: false
    property bool editable: true
    // Why the flag cannot be changed and what changes it, shown instead of its help while it cannot (edi ADR-0077).
    property string disabledReason: ""

    signal toggled(bool checked)

    parameter: ({
            "value": "",
            "shortPrettyName": flag.label,
            "enabled": flag.editable
        })
    // The box holds no text: it is never focused or typed into.
    focusPolicy: Qt.NoFocus
    maximumLength: 0
    // One popup, the base field's, as a value field's: the reason while read only, else the item's help.
    ToolTip.text: !editable && disabledReason !== "" ? disabledReason : uid !== "" ? Session.tooltip(uid) : ""
    // The title sits where every value field's does.
    Component.onCompleted: FieldTitles.align(flag)

    EaElements.CheckBox {
        objectName: flag.objectName !== "" ? `${flag.objectName}.box` : ""
        anchors.right: parent.right
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.25
        y: flag.topInset + (flag.height - flag.topInset - height) / 2
        checked: flag.checked
        enabled: flag.editable
        onToggled: flag.toggled(checked)
    }
}
