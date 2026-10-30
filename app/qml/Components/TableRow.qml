// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Components as EaComponents

import edi.app

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
    onEditingChanged: ApplicationInfo.tableRowEditing()
    // A row's own click handler (one that opens what the row names) calls this too, so its click makes the row current
    // as any other does: selected in a selectable table, and reported to a page that holds its current row.
    function activated() {
        ApplicationInfo.tableRowActivated();
    }

    Component.onCompleted: ApplicationInfo.tableRowCompleted((child, hover) => {
        child.opacity = Qt.binding(() => hover !== null && hover.enabled && hover.hovered ? 1 : 0);
    })
}
