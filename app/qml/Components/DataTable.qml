// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    function revealRow(index: int): bool {
        if (index < 0 || index >= count) return false;
        const originalModel = sourceModel;
        positionViewAtIndex(index, ListView.Contain);
        forceLayout();
        const row = itemAtIndex(index);
        if (sourceModel !== originalModel || row === null || row.index !== index) return false;
        const top = row.mapToItem(table, 0, 0).y;
        const header = headerItem ? headerItem.height : 0;
        if (top < header) contentY -= header - top;
        else if (top + row.height > height) contentY += top + row.height - height;
        forceLayout();
        return sourceModel === originalModel && itemAtIndex(index) === row && row.index === index;
    }
    function revealItem(item: Item): bool {
        if (item === null) return false;
        let row = item;
        while (row !== null && row.parent !== contentItem) row = row.parent;
        if (row === null || !("index" in row) || itemAtIndex(row.index) !== row) return false;
        const index = row.index, originalModel = sourceModel;
        return revealRow(index) && sourceModel === originalModel && itemAtIndex(index) === row;
    }

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
    // the background, and a page's tables kept laying out for about a second after a project opened. So the
    // columns fit the rows measured since the content last changed: scrolling only ever widens a column, for a wider
    // row, and never moves one back and forth (the owner, 2026-10-27).
    cacheBuffer: 0
    readonly property real numberColumnWidth: Math.ceil(metrics.advanceWidth(String(Math.max(1, count)))) + AppSizes.fieldSpacing * 2
    property int modelRevision: 0
    // The one column rule (ADR-0029; the owner, 2026-10-24 and 2026-10-27). The row-number column and every flex
    // column (-1) fit their header and their widest cell, each with the same margin, so every two neighbours sit as
    // far apart. Numbers are right-aligned under right-aligned headers, text left-aligned, icons centred. An empty
    // filler cell after the last data column takes the rest of the row, so nothing moves towards the row buttons,
    // which keep their widths at the right. `equalColumns` keeps the flex columns equal instead (atom sites, atomic
    // displacements, the Analysis parameters), and `spreadColumns` shares the rest among those columns after their
    // fitted widths (Measured data). A row too narrow for its texts loses the margins first, then narrows the
    // texts, where a number shows its short form. Widths follow the content: scrolling only widens a column for a
    // wider row, and a change of the content fits them again.
    property var columns: []
    property bool equalColumns: false
    property var spreadColumns: []
    autoColumnPadding: EaStyle.Sizes.tableColumnSpacing * 4
    // The last data column, which holds the spare width as empty space after its content; -1 for none.
    readonly property int fillerIndex: equalColumns || spreadColumns.length > 0 ? -1 : columns.lastIndexOf(-1)
    // Each column's widest text, its header's or a cell's, without the margin.
    property var fittedWidths: []
    property bool refitting: true
    columnWidths: {
        const fitted = fittedWidths;
        // Before the first fit every flex column shares the row, as the base lays it out.
        if (equalColumns || fitted.length !== columns.length)
            return columns;
        // The row-number column keeps the width of its widest number, whichever rows are drawn.
        const fits = columns.map(w => w === -1);
        const fitting = fits.filter(Boolean).length;
        const fixed = columns.reduce((sum, w, i) => sum + (w > 0 && !fits[i] ? w : 0), 0);
        const texts = fitted.reduce((sum, w, i) => sum + (fits[i] ? w : 0), 0);
        const gaps = columns.length - 1;
        const room = width - fixed - EaStyle.Sizes.tableColumnSpacing * gaps - EaStyle.Sizes.borderThickness * 2 - rowPadding * 2;
        const margin = fitting > 0 ? Math.max(0, Math.min(autoColumnPadding, (room - texts) / fitting)) : 0;
        const scale = texts > room && texts > 0 ? Math.max(0, room) / texts : 1;
        const spread = spreadColumns.length > 0 ? Math.max(0, room - texts - margin * fitting) / spreadColumns.length : 0;
        const widths = columns.map((w, i) => fits[i] ? Math.floor(fitted[i] * scale + margin + (spreadColumns.includes(i) ? spread : 0)) : w);
        if (fillerIndex >= 0) {
            const used = widths.reduce((sum, w) => sum + w, 0);
            const spare = Math.max(0, width - EaStyle.Sizes.tableColumnSpacing * gaps - EaStyle.Sizes.borderThickness * 2 - rowPadding * 2 - used);
            widths[fillerIndex] += Math.floor(spare);
        }
        return widths;
    }
    // The spare width the last data column holds after its content, as empty space before the row buttons: its
    // cells keep their text where it fits, a right-aligned number by its neighbours.
    property real fillerWidth: 0
    // Each padded cell's own paddings and alignment kind, by cell.
    property var basePaddings: new Map()
    property var cellKinds: new Map()
    // A cell's padding: its own, a spacing more on the side it aligns to, so a right-aligned number and a
    // left-aligned text in neighbouring columns never meet, and in the last data column the spare width after it.
    function padForFiller(cell, column) {
        if (!("rightPadding" in cell) || "keepsAlignment" in cell)
            return;
        if (!basePaddings.has(cell))
            basePaddings.set(cell, {
                "left": cell.leftPadding,
                "right": cell.rightPadding
            });
        const base = basePaddings.get(cell);
        const kind = cellKinds.get(cell) ?? "";
        const gap = EaStyle.Sizes.tableColumnSpacing;
        cell.leftPadding = base.left + (kind === "text" ? gap : 0);
        cell.rightPadding = base.right + (kind === "number" || kind === "check" ? gap : 0) + (column === fillerIndex ? fillerWidth : 0);
    }
    // A cell's kind, which sets how it aligns: a number, an icon or button, or text.
    function kindOf(cell) {
        if ("checked" in cell && "horizontalAlignment" in cell)
            return "check";
        if ("ring" in cell || "fontIcon" in cell)
            return "icon";
        if ("number" in cell || "columnAlignment" in cell || "item" in cell || ("numeric" in cell && cell.numeric))
            return "number";
        return "text";
    }
    function alignCell(cell, kind) {
        if ("keepsAlignment" in cell)
            return;
        cellKinds.set(cell, kind);
        const alignment = kind === "number" || kind === "check" ? Text.AlignRight : kind === "icon" ? Text.AlignHCenter : Text.AlignLeft;
        if ("columnAlignment" in cell)
            cell.columnAlignment = alignment;
        else if ("horizontalAlignment" in cell)
            cell.horizontalAlignment = alignment;
    }
    function fitColumns() {
        const header = headerItem && headerItem.implicitColumnWidths ? headerItem.implicitColumnWidths.filter((w, i) => true) : [];
        // A cell is measured by its whole text: a number cell by the number it would show if it fitted (it shortens
        // itself to the width it is given), a label by its natural width, an editor by its text (its implicit width
        // is a default, not its text).
        const padded = (cell, w) => w + (cell.leftPadding ?? 0) + (cell.rightPadding ?? 0);
        // A cell that only holds a control (a combo box in an Item) is as wide as the control, its arrow and padding
        // included.
        const control = child => "fittedWidth" in child ? child.fittedWidth : child.implicitWidth ?? 0;
        const held = cell => Array.from(cell.children).reduce((widest, child) => Math.max(widest, control(child)), cell.implicitWidth);
        const measure = cell => "number" in cell ? padded(cell, metrics.advanceWidth(cell.number)) : "elide" in cell ? cell.implicitWidth : "contentWidth" in cell ? padded(cell, cell.contentWidth) : held(cell);
        // The cells of a row's inner Row, in column order, the filler left out.
        const cellsOf = row => {
            const first = row && row.contentRowData ? Array.from(row.contentRowData).find(cell => cell instanceof Item) : null;
            return first && first.parent ? Array.from(first.parent.children) : null;
        };
        const headerCells = cellsOf(headerItem);
        const headerWidths = headerCells ? headerCells.map((cell, i) => Math.ceil(cell.implicitWidth - (i === fillerIndex && basePaddings.has(cell) ? fillerWidth : 0))) : header;
        const widths = columns.map((w, i) => Math.max(headerWidths[i] ?? 0, refitting ? 0 : (fittedWidths[i] ?? 0)));
        let kinds = null;
        for (const item of contentItem.children) {
            const cells = cellsOf(item);
            if (!cells || item === headerItem)
                continue;
            kinds = kinds ?? cells.map(cell => kindOf(cell));
            for (let i = 0; i < cells.length && i < widths.length; ++i) {
                if (i > 0 && kinds[i])
                    alignCell(cells[i], kinds[i]);
                padForFiller(cells[i], i);
                widths[i] = Math.max(widths[i], Math.ceil(measure(cells[i]) - (i === fillerIndex ? fillerWidth : 0)));
            }
        }
        if (kinds && headerCells) {
            for (let i = 1; i < headerCells.length && i < kinds.length; ++i) {
                alignCell(headerCells[i], kinds[i]);
                padForFiller(headerCells[i], i);
            }
        }
        refitting = false;
        if (JSON.stringify(widths) !== JSON.stringify(fittedWidths))
            fittedWidths = widths;
    }
    // A change of the content fits the columns afresh; scrolling only adds rows to what was measured.
    function refit() {
        refitting = true;
        Qt.callLater(fitColumns);
    }
    onColumnsChanged: refit()
    // The spare width follows the columns: the last data column's cells take it as padding after their content.
    onColumnWidthsChanged: {
        const spare = fillerIndex >= 0 && fittedWidths.length === columns.length ? Math.max(0, columnWidths[fillerIndex] - (fittedWidths[fillerIndex] ?? 0) - autoColumnPadding) : 0;
        if (spare !== fillerWidth) {
            fillerWidth = spare;
            Qt.callLater(fitColumns);
        }
    }
    onModelRevisionChanged: refit()
    onCountChanged: refit()
    Component.onCompleted: refit()
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
            table.refit();
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
