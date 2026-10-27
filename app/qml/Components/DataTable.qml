// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    // The selection model needs an explicit empty model while a page is being attached.
    property var sourceModel: null
    model: sourceModel ?? null
    multiSelection: false
    // A click on any cell makes its row current, an editable cell's too (the owner, 2026-10-22): an editor taking
    // focus selects its row, as a click on the row's background does.
    selectOnEdit: true
    // A row the user made current, by a click on any of its cells or by moving into one of its editors: a table whose
    // page holds its current row (marksCurrentRow) sets it from this.
    signal rowActivated(int row)

    // Up and Down move the current row as a click does (the owner, 2026-10-22): the row is selected in a selectable
    // table and reported as activated, so a page holding its current row moves too. A passive table (nothing
    // selectable and no current row) keeps the keys, and a text editor keeps its own.
    Keys.onPressed: event => {
        if ((event.key !== Qt.Key_Up && event.key !== Qt.Key_Down) || table.count === 0 || (!table.selectable && !table.marksCurrentRow))
            return;
        const focused = table.Window.activeFocusItem;
        if (focused !== null && "cursorPosition" in focused)
            return;
        const from = table.markerRow;
        const row = Math.max(0, Math.min(table.count - 1, from < 0 ? 0 : from + (event.key === Qt.Key_Down ? 1 : -1)));
        table.currentIndex = row;
        table.positionViewAtIndex(row, ListView.Contain);
        if (table.selectable)
            table.selectWithModifiers(row, Qt.NoModifier);
        table.rowActivated(row);
        event.accepted = true;
    }
    // Rows are made when they come into view, never ahead of it: rows made ahead are built a few per frame in
    // the background, and a page's tables kept laying out for about a second after a project opened.
    cacheBuffer: 0
    readonly property real numberColumnWidth: Math.ceil(metrics.advanceWidth(String(Math.max(1, count)))) + AppSizes.fieldSpacing * 2
    property int modelRevision: 0
    // The one column rule (ADR-0029): `columns` as the base's `columnWidths`, where every flex column (-1) but the
    // last fits its header and its widest shown cell, so the columns start at the left and the last flex column,
    // aligned left, takes the rest of the row; fixed columns, the row buttons among them, keep their widths.
    // `equalColumns` keeps the flex columns equal instead (atom sites and atomic displacements).
    property var columns: []
    property bool equalColumns: false
    property var fittedWidths: []
    columnWidths: {
        const fitted = fittedWidths;
        const last = columns.lastIndexOf(-1);
        return columns.map((w, i) => !equalColumns && w === -1 && i !== last && (fitted[i] ?? 0) > 0 ? fitted[i] : w);
    }
    function fitColumns() {
        const header = headerItem && headerItem.implicitColumnWidths ? headerItem.implicitColumnWidths : [];
        const widths = columns.map((w, i) => (header[i] ?? 0) + autoColumnPadding);
        // An editor's implicit width is a default, not its text: a cell is measured by its text where it has one.
        const measure = cell => "contentWidth" in cell ? cell.contentWidth + (cell.leftPadding ?? 0) + (cell.rightPadding ?? 0) : cell.implicitWidth;
        // The filling column reads from the left, as its header, so its value sits next to the columns before it and
        // the space it takes is left after it (a right-aligned number would move to the row's far edge).
        const fill = equalColumns ? -1 : columns.lastIndexOf(-1);
        const align = cells => {
            if (fill >= 0 && fill < cells.length && "horizontalAlignment" in cells[fill])
                cells[fill].horizontalAlignment = Text.AlignLeft;
        };
        // The cells as the base sizes them: a row's visual children, in order.
        const cellsOf = row => row && row.contentRowData ? Array.from(row.contentRowData).filter(cell => cell instanceof Item) : null;
        if (cellsOf(headerItem))
            align(cellsOf(headerItem));
        for (const item of contentItem.children) {
            const cells = cellsOf(item);
            if (!cells)
                continue;
            align(cells);
            for (let i = 0; i < cells.length && i < widths.length; ++i)
                widths[i] = Math.max(widths[i], Math.ceil(measure(cells[i])));
        }
        if (JSON.stringify(widths) !== JSON.stringify(fittedWidths))
            fittedWidths = widths;
    }
    onColumnsChanged: Qt.callLater(fitColumns)
    onModelRevisionChanged: Qt.callLater(fitColumns)
    onCountChanged: Qt.callLater(fitColumns)
    Component.onCompleted: Qt.callLater(fitColumns)
    Connections {
        target: table.contentItem
        function onChildrenChanged() {
            Qt.callLater(table.fitColumns);
        }
    }
    // Long IDs and paths must leave room for the numeric cells and row controls.
    property real maximumTextColumnShare: 0.25
    // Each measured role's text width per row. An update measures only the rows it names, and the column
    // only changes when one of those widths did: a scan's rows update one by one, hundreds of times.
    property var rowWidths: ({})

    function textWidth(row: int, role: string): real {
        const text = typeof model.text === "function" ? model.text(row, role) : typeof model.get === "function" ? String(model.get(row)[role] ?? "") : "";
        return metrics.advanceWidth(text);
    }
    // The width of `text` in the table's font.
    function advance(text: string): real {
        return metrics.advanceWidth(text);
    }
    function textColumnWidth(role: string, title: string): real {
        return Math.min(naturalTextColumnWidth(role, title), width * maximumTextColumnShare);
    }
    // The widest of the column's texts and its title, with a cell's margins, however wide the table is.
    function naturalTextColumnWidth(role: string, title: string): real {
        const revision = modelRevision;
        let widths = rowWidths[role];
        if (!widths || widths.length !== count) {
            widths = [];
            for (let row = 0; model && row < count; ++row)
                widths.push(textWidth(row, role));
            rowWidths[role] = widths;
        }
        const result = widths.reduce((widest, measured) => Math.max(widest, measured), metrics.advanceWidth(title));
        return Math.ceil(result) + AppSizes.fieldSpacing * 2;
    }
    // Cleared in place: the bindings that read the cache depend on modelRevision, never on the cache itself.
    function forgetWidths() {
        for (const role in rowWidths)
            delete rowWidths[role];
    }
    function remeasure() {
        forgetWidths();
        modelRevision++;
    }

    // A table with a current row (the base's `currentRow`, which its moving accent marker shows; edi ADR-0017 §11)
    // selects no row, since the base draws a bar on a selected (clicked) row, which would show at once beside the
    // marker (the owner, 2026-10-13).
    property bool marksCurrentRow: false
    selectable: !marksCurrentRow

    onModelChanged: forgetWidths()

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        onFontChanged: table.remeasure()
    }
    Connections {
        target: table.model
        ignoreUnknownSignals: true
        function onDataChanged(topLeft, bottomRight) {
            let changed = false;
            for (const role in table.rowWidths) {
                const widths = table.rowWidths[role];
                for (let row = topLeft.row; row <= bottomRight.row && row < widths.length; ++row) {
                    const measured = table.textWidth(row, role);
                    if (measured !== widths[row]) {
                        widths[row] = measured;
                        changed = true;
                    }
                }
            }
            if (changed)
                table.modelRevision++;
        }
        function onCountChanged() {
            table.remeasure();
        }
        function onModelReset() {
            table.remeasure();
        }
        function onRowsMoved() {
            table.remeasure();
        }
        function onLayoutChanged() {
            table.remeasure();
        }
    }
}
