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
    // The one column rule (ADR-0029; the owner, 2026-10-27): the row-number column and every flex column (-1) but the
    // last fit their header and their widest shown cell, each with the same margin, so the columns start at the left
    // and every two neighbours sit as far apart; the last data column, aligned left, takes the rest of the row: a
    // text there stretches, a number leaves the space after it empty. No column before another data column fills.
    // Fixed columns, the row buttons among them, keep their widths, at the right. `equalColumns` keeps the flex
    // columns equal instead (atom sites and atomic displacements). Only a row too narrow for the texts themselves
    // narrows them, where a number shows its short form.
    property var columns: []
    property bool equalColumns: false
    // The one margin every fitted column has, half again the base's (the owner, 2026-10-27).
    autoColumnPadding: EaStyle.Sizes.tableColumnSpacing * 3
    readonly property var fillColumns: [columns.lastIndexOf(-1)]
    // Each column's widest text, its header's or a shown cell's, without the margin.
    property var fittedWidths: []
    columnWidths: {
        const fitted = fittedWidths;
        // Before the first fit every flex column shares the row, as the base lays it out.
        if (equalColumns || fitted.length !== columns.length)
            return columns;
        const fits = columns.map((w, i) => (w === -1 || (i === 0 && w === numberColumnWidth)) && !fillColumns.includes(i));
        const fitting = fits.filter(Boolean).length;
        if (fitting === 0)
            return columns;
        const fixed = columns.reduce((sum, w, i) => sum + (w > 0 && !fits[i] ? w : 0), 0);
        const texts = fitted.reduce((sum, w, i) => sum + (fits[i] ? w : 0), 0);
        const filling = fillColumns.reduce((sum, i) => sum + (fitted[i] ?? 0), 0);
        // The filling columns give up their room first; the others narrow only when their texts alone do not fit, as
        // a number's short form is not always narrower.
        const room = width - fixed - EaStyle.Sizes.tableColumnSpacing * (columns.length - 1) - EaStyle.Sizes.borderThickness * 2 - rowPadding * 2;
        const margin = Math.max(0, Math.min(autoColumnPadding, (room - texts - filling) / fitting));
        const scale = texts > room && texts > 0 ? Math.max(0, room) / texts : 1;
        return columns.map((w, i) => fits[i] ? Math.floor(fitted[i] * scale + margin) : w);
    }
    function fitColumns() {
        const header = headerItem && headerItem.implicitColumnWidths ? headerItem.implicitColumnWidths : [];
        const widths = columns.map((w, i) => header[i] ?? 0);
        // A cell is measured by its whole text: a number cell by the number it would show if it fitted (it shortens
        // itself to the width it is given), a label by its natural width, an editor by its text (its implicit width
        // is a default, not its text).
        const padded = (cell, w) => w + (cell.leftPadding ?? 0) + (cell.rightPadding ?? 0);
        // A cell that only holds a control (a combo box in an Item) is as wide as the control, its arrow and padding
        // included.
        const control = child => "fittedWidth" in child ? child.fittedWidth : child.implicitWidth ?? 0;
        const held = cell => Array.from(cell.children).reduce((widest, child) => Math.max(widest, control(child)), cell.implicitWidth);
        const measure = cell => "number" in cell ? padded(cell, metrics.advanceWidth(cell.number)) : "elide" in cell ? cell.implicitWidth : "contentWidth" in cell ? padded(cell, cell.contentWidth) : held(cell);
        // A filling column reads from the left, as its header, so its value sits next to the columns before it and
        // the space it takes is left after it (a right-aligned number would move to the row's far edge).
        const align = cells => {
            for (const fill of equalColumns ? [] : fillColumns) {
                if (fill >= 0 && fill < cells.length && "horizontalAlignment" in cells[fill])
                    cells[fill].horizontalAlignment = Text.AlignLeft;
            }
        };
        // The cells as the base sizes them: the children of the row's inner Row, in order, so a Repeater's cells
        // (placed before the Repeater) line up with their columns.
        const cellsOf = row => {
            const first = row && row.contentRowData ? Array.from(row.contentRowData).find(cell => cell instanceof Item) : null;
            return first && first.parent ? Array.from(first.parent.children) : null;
        };
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
    onFillColumnsChanged: Qt.callLater(fitColumns)
    onModelRevisionChanged: Qt.callLater(fitColumns)
    onCountChanged: Qt.callLater(fitColumns)
    Component.onCompleted: Qt.callLater(fitColumns)
    Connections {
        target: table.contentItem
        function onChildrenChanged() {
            Qt.callLater(table.fitColumns);
        }
    }
    // A header whose cells change after it was made (a column per structure arriving with the calculation) has
    // them sized and the columns fitted again.
    Connections {
        target: table.headerItem
        ignoreUnknownSignals: true
        function onImplicitColumnWidthsChanged() {
            const first = table.headerItem && table.headerItem.contentRowData ? Array.from(table.headerItem.contentRowData).find(cell => cell instanceof Item) : null;
            if (first && first.parent)
                table.applyWidths(first.parent);
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
            // A value arriving later (a calculated curve) can widen its column.
            Qt.callLater(table.fitColumns);
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
