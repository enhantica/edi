// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

// The base's Dialog, centred on whole pixels (edi ADR-0017 §14). The base centres with a half, so a dialog of
// odd height sat on a half pixel and each platform drew its edges and its table's lines differently (edi PR
// 97: the three-row Messages dialog, 239 high, at y 264.5). Every dialog of edi's is one of these.
EaElements.Dialog {
    id: dialog

    // Enter presses the dialog's OK, as a standard dialog's default button. Opted into by dialogs with no text field
    // of their own, where Enter has nothing else to do.
    property bool enterAccepts: false

    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)

    Shortcut {
        sequences: ["Return", "Enter"]
        enabled: dialog.enterAccepts && dialog.opened
        onActivated: dialog.accept()
    }
}
