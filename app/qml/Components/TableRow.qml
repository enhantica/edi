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

    // The row becomes current as soon as one of its editors takes focus, by a click or by Tab.
    onEditingChanged: {
        if (row.editing)
            row.activated();
    }
    function activated() {
        if (row.listView !== null && row.listView.rowActivated !== undefined && row.index >= 0)
            row.listView.rowActivated(row.index);
    }

    Component.onCompleted: {
        // A control that takes focus from the keyboard only (a button or check box on some platforms) takes it from a
        // click too, so the click makes the row current as an editor's does. Every item has a focus policy, labels and
        // mouse areas too (NoFocus), and they keep theirs: one that took focus would take it from the editor under it.
        const focusOnClick = item => {
            if (item.focusPolicy === Qt.TabFocus)
                item.focusPolicy = Qt.StrongFocus;
            for (const child of item.children ?? [])
                focusOnClick(child);
        };
        for (const cell of row.contentRowData)
            focusOnClick(cell);
        // The light row tint shows only under the mouse (the owner, 2026-10-22): the base also keeps it on a row whose
        // cell is being edited, which read as a second current-row mark. Its tint is the full-row rectangle with the
        // row's background click area; it follows the row's hover handler alone.
        let hover = null;
        for (const child of row.data) {
            if (child instanceof HoverHandler)
                hover = child;
        }
        for (const child of row.data) {
            if (child instanceof Rectangle && child.anchors.fill === row && child.children.length > 0) {
                child.opacity = Qt.binding(() => hover !== null && hover.enabled && hover.hovered ? 1 : 0);
                // The same rectangle holds the click area of the row's background: a click on a cell that is not an
                // editor lands there.
                for (const area of child.children) {
                    if (area instanceof MouseArea)
                        area.clicked.connect(row.activated);
                }
            }
        }
        if (!row.highlightsHover && hover !== null)
            hover.enabled = false;
    }
}
