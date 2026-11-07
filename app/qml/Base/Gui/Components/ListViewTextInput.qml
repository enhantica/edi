// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) 2021-2026 EasyScience contributors.
// App-owned pinned ListViewTextInput overlay; Escape ownership: ADR-0029.
import QtQuick
import edi.app

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

EaElements.TextInput {
    id: control

    property string headerText: ""

    // A table's measuring rows make and drop their cells while the cells have no parent yet or any more.
    height: parent ? parent.height : 0
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    hoverEnabled: true

    // ListView has its own row selection, so we don't need the TableView-style
    // "highlight the last-edited cell" behaviour — hence this separate component
    // with a color override. Track activeFocus (real keyboard focus) rather than
    // the per-FocusScope `focus` flag used in TextInput.qml, so sibling
    // ListViewDelegates don't stay blue after editing ends.
    color: enterFlash ? EaStyle.Colors.themeForeground : warned ? EaStyle.Colors.red : !enabled || readOnly || minored ? EaStyle.Colors.themeForegroundMinor : activeFocus || selected || hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
    Behavior on color {
        EaAnimations.ThemeChange {}
    }

    function cancelTextEdit(event) {
        ApplicationInfo.listTextInputEscape(control, event);
    }
    Keys.onEscapePressed: event => control.cancelTextEdit(event)

    onActiveFocusChanged: ApplicationInfo.editorTextChanged()
    onTextChanged: ApplicationInfo.editorTextChanged()

    // Tooltip with full text when content overflows the cell. Suppressed
    // while editing — the live text is what the user is interacting with.
    readonly property bool overflows: contentWidth > width
    EaElements.ToolTip {
        text: control.text
        requested: control.overflows && control.hovered && !control.activeFocus
    }
}
