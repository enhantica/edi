// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table cell that shows a value as text. In a read-only table (DataTable.readOnly) it takes the grey of a cell that
// is shown, not edited, as a calculated table's TextCell does, so the tables a user can edit stand out. A column that
// stays interactive in such a table (a click-to-exclude status) uses its own cell type and keeps its own look.
EaComponents.ListViewLabel {
    readonly property bool readOnlyRow: (row as TableRow)?.readOnly ?? false

    color: currentRow ? EaStyle.Colors.themeAccent : !enabled ? EaStyle.Colors.themeForegroundDisabled : marksCurrentRow || readOnlyRow ? EaStyle.Colors.themeForegroundMinor : selected ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
}
