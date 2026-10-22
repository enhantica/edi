// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Components as EaComponents

// The one row type of every edi table (edi ADR-0017 §11): the base's ListViewDelegate, whose rows keep their
// alternating background, the current one too, with the list's accent marker on the current row and its number,
// a ListViewLabel with marksCurrentRow, bold in the accent colour.
EaComponents.ListViewDelegate {
    id: row

    required property int index
    // False for a read-only list (the About window's third-party licences): the row shows no hover tint and keeps the
    // arrow pointer, as nothing in it can be chosen.
    property bool highlightsHover: true

    Component.onCompleted: {
        // Every control in the row takes focus when clicked, a check box or a combo box too (some platforms give a
        // button focus only from the keyboard), so the click makes the row current as an editor's does.
        const focusOnClick = item => {
            if ("focusPolicy" in item)
                item.focusPolicy = Qt.StrongFocus;
            for (const child of item.children ?? [])
                focusOnClick(child);
        };
        for (const cell of row.contentRowData)
            focusOnClick(cell);
        if (row.highlightsHover)
            return;
        for (const child of row.data) {
            if (child instanceof HoverHandler)
                child.enabled = false;
        }
    }
}
