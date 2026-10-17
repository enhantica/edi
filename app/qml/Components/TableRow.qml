// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

// A row of a table with a current row: every row keeps its alternating background, the current one too, and the
// table marks the current row with its accent bar (DataTable.currentRow, edi ADR-0017 §11).
EaComponents.ListViewDelegate {
    required property int index

    color: index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1
}
