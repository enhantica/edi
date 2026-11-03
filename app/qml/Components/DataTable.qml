// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQml.Models

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
    // the background, and a page's tables kept laying out for about a second after a project opened. The columns fit
    // every row of the model, measured when the content changes (fitWholeModel), so scrolling never moves one (the
    // owner, 2026-10-27).
    cacheBuffer: 0
    // The row-number column fits the widest number in the bold the current row's number takes, measured again when
    // the font changes (a web font arriving after the first layout).
    readonly property real numberColumnWidth: modelRevision >= 0 ? Math.ceil(boldMetrics.advanceWidth(String(Math.max(1, count)))) + AppSizes.fieldSpacing * 2 : 0
    property int modelRevision: 0
    // The one column rule (ADR-0029; the owner, 2026-10-24 and 2026-10-27). The row-number column and every flex
    // column (-1) fit their header and their widest cell, each with the same margin, so every two neighbours sit as
    // far apart. Numbers are right-aligned under right-aligned headers, text left-aligned, icons centred. An empty
    // filler cell after the last data column takes the rest of the row, so nothing moves towards the row buttons,
    // which keep their widths at the right. `equalColumns` keeps the flex columns equal instead (atom sites, atomic
    // displacements, the Analysis parameters), and `spreadColumns` shares the rest among those columns after their
    // fitted widths (Measured data). A row too narrow for its texts loses the margins first, then narrows the
    // texts, where a number shows its short form. Widths follow the content: a change of the content fits them again,
    // and scrolling changes none.
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
    // The columns whose right-aligned values are followed by a combo box or by the row buttons: they keep a font size
    // more after their values (the owner, 2026-10-27: "WP is too close to z. Occ too close to buttons"). A value's
    // units column stays beside it.
    property var wideEdges: []
    // A cell's padding: its own, a spacing more on the side it aligns to, so a right-aligned number and a
    // left-aligned text in neighbouring columns never meet, and in the last data column the spare width after it. A
    // check box, which centres itself in its room, is pushed to the right edge by its left padding. A `fresh` cell, made
    // only to be measured, still has its own paddings and goes in no map: a JS map lookup scans every entry, and with a
    // thousand rows measured the maps made each measure take minutes.
    function padForFiller(cell, column, kind = undefined, fresh = false) {
        if (!("rightPadding" in cell) || "keepsAlignment" in cell)
            return;
        if (!fresh && !basePaddings.has(cell))
            basePaddings.set(cell, {
                "left": cell.leftPadding,
                "right": cell.rightPadding
            });
        const base = fresh ? {
            "left": cell.leftPadding,
            "right": cell.rightPadding
        } : basePaddings.get(cell);
        kind = (fresh ? kind : cellKinds.get(cell)) ?? "";
        const gap = EaStyle.Sizes.tableColumnSpacing;
        const right = kind === "number" || kind === "check";
        cell.rightPadding = base.right + (right ? gap : 0) + (right && wideEdges[column] ? EaStyle.Sizes.fontPixelSize : 0) + (column === fillerIndex ? fillerWidth : 0);
        if (kind === "check" && cell.indicator) {
            // Set, not bound: the box's implicit width follows its padding, and its column's width its implicit one.
            cell.leftPadding = Math.max(base.left, cell.width - cell.rightPadding - cell.indicator.width);
            if (!fresh && !checkCells.has(cell)) {
                checkCells.add(cell);
                cell.widthChanged.connect(() => table.padForFiller(cell, column));
            }
        } else {
            cell.leftPadding = base.left + (kind === "text" ? gap : 0);
        }
        return base;
    }
    property var checkCells: new Set()
    // A cell's kind, which sets how it aligns: a number, an icon or button, or text. A row button is checkable too, so
    // it is told from a check box by its icon first.
    function kindOf(cell) {
        if ("ring" in cell || "fontIcon" in cell)
            return "icon";
        if ("checked" in cell && "horizontalAlignment" in cell)
            return "check";
        if ("number" in cell || "columnAlignment" in cell || "item" in cell || "parameter" in cell || ("numeric" in cell && cell.numeric))
            return "number";
        return "text";
    }
    function alignCell(cell, kind, fresh = false) {
        if ("keepsAlignment" in cell)
            return;
        if (!fresh)
            cellKinds.set(cell, kind);
        const alignment = kind === "number" || kind === "check" ? Text.AlignRight : kind === "icon" ? Text.AlignHCenter : Text.AlignLeft;
        if ("columnAlignment" in cell)
            cell.columnAlignment = alignment;
        else if ("horizontalAlignment" in cell)
            cell.horizontalAlignment = alignment;
    }
    function sameValues(a, b) {
        return a.length === b.length && a.every((value, i) => value === b[i]);
    }
    // Styles the cells of `rows` (alignment and padding) and, with `measure`, fits the columns to them and the header.
    // Only the whole model is measured (fitWholeModel); a row the view makes, scrolled into view, is only styled and
    // takes the widths the model was measured to (the owner, 2026-10-27). Without `measure` it returns the widths
    // `rows` need, at least `from` (a part of the model measured before).
    function fitColumns(measure = false, rows = null, from = null) {
        const header = headerItem && headerItem.implicitColumnWidths ? headerItem.implicitColumnWidths.filter((w, i) => true) : [];
        // A cell is measured by its whole text: a number cell by the number it would show if it fitted (it shortens
        // itself to the width it is given), a label by its natural width, an editor by its text (its implicit width
        // is a default, not its text).
        const padded = (cell, w) => w + (cell.leftPadding ?? 0) + (cell.rightPadding ?? 0);
        // A cell that only holds a control (a combo box in an Item) is as wide as the control, its arrow and padding
        // included.
        const control = child => "fittedWidth" in child ? child.fittedWidth : child.implicitWidth ?? 0;
        const held = cell => Array.from(cell.children).reduce((widest, child) => Math.max(widest, control(child)), cell.implicitWidth);
        // A check box by its box and its own paddings, never the padding that pushes it right.
        const measured = (cell, kind, base) => kind === "check" && cell.indicator ? (base?.left ?? 0) + cell.indicator.width + cell.rightPadding : "number" in cell ? padded(cell, metrics.advanceWidth(cell.number)) : "elide" in cell ? cell.implicitWidth : "contentWidth" in cell ? padded(cell, cell.contentWidth) : padded(cell, held(cell));
        // The cells of a row's inner Row, in column order, the filler left out.
        const cellsOf = row => {
            const first = row && row.contentRowData ? Array.from(row.contentRowData).find(cell => cell instanceof Item) : null;
            return first && first.parent ? Array.from(first.parent.children) : null;
        };
        const headerCells = cellsOf(headerItem);
        const headerWidths = headerCells ? headerCells.map((cell, i) => Math.ceil(cell.implicitWidth - (i === fillerIndex && basePaddings.has(cell) ? fillerWidth : 0))) : header;
        const widths = from ? from.slice() : columns.map((w, i) => Math.max(headerWidths[i] ?? 0, refitting ? 0 : (fittedWidths[i] ?? 0)));
        let kinds = null;
        const fresh = rows !== null;
        for (const item of rows ?? contentItem.children) {
            const cells = cellsOf(item);
            if (!cells || item === headerItem)
                continue;
            if (!kinds) {
                kinds = cells.map(cell => kindOf(cell));
                const rightAligned = kind => kind === "number" || kind === "check";
                const edges = kinds.map((kind, i) => i > 0 && i + 1 < kinds.length && rightAligned(kind) && (kinds[i + 1] === "icon" || "fills" in cells[i + 1]));
                if (!sameValues(edges, wideEdges))
                    wideEdges = edges;
            }
            for (let i = 0; i < cells.length && i < widths.length; ++i) {
                const kind = i > 0 && kinds[i] && !("keepsAlignment" in cells[i]) ? kinds[i] : undefined;
                if (kind)
                    alignCell(cells[i], kind, fresh);
                const base = padForFiller(cells[i], i, kind, fresh);
                widths[i] = Math.max(widths[i], Math.ceil(measured(cells[i], fresh ? kind : cellKinds.get(cells[i]), fresh ? base : basePaddings.get(cells[i])) - (i === fillerIndex ? fillerWidth : 0)));
            }
        }
        if (kinds && headerCells) {
            for (let i = 1; i < headerCells.length && i < kinds.length; ++i) {
                alignCell(headerCells[i], kinds[i]);
                padForFiller(headerCells[i], i);
            }
        }
        if (!measure)
            return widths;
        refitting = false;
        if (!sameValues(widths, fittedWidths))
            fittedWidths = widths;
    }
    // A change of the content fits the columns afresh to every row of the model (fitWholeModel), once the table shows.
    function refit() {
        unmadeRetries = 0;
        refitting = true;
        Qt.callLater(fitWholeModel);
    }
    // The cells of rows the view made, styled as the measured ones are.
    function styleCells() {
        if (!gone)
            fitColumns(false);
    }
    // Set as the table is destroyed. Its rows going queue calls (Qt.callLater) that run after its context is gone,
    // where reading any of its functions is an error; a property can still be read.
    property bool gone: false
    Component.onDestruction: gone = true
    // Every row of the model is made beside the view, measured with the header, and dropped: the columns fit the widest
    // row wherever it is, and scrolling changes no width. A table not shown waits until it is.
    function fitWholeModel() {
        if (!refitting || gone)
            return;
        if (!visible || !(onScreen || count <= measuredAtOnce)) {
            refitting = false;
            unfitted = true;
            return;
        }
        unfitted = false;
        measuredWidths = null;
        unmadeRows = 0;
        measureRows(++measureRun, 0);
    }
    // A model of up to this many rows is measured at once. A larger one (a pattern's points) is measured a frame's
    // worth of rows at a time, so the window keeps responding; a new change of the content starts it again.
    readonly property int measuredAtOnce: 100
    property int measureRun: 0
    property var measuredWidths: null
    function measureRows(run, from) {
        if (gone || run !== measureRun)
            return;
        if (!visible || !(onScreen || count <= measuredAtOnce)) {
            refitting = false;
            unfitted = true;
            return;
        }
        measuringRows.model = model;
        const total = measuringRows.count;
        const started = Date.now();
        const rows = [];
        let next = from;
        // A row is null while what it is in is still being made in the background; it is not measured, as the view's
        // rows are not, and a later change of the content measures it.
        while (next < total && (total <= measuredAtOnce || Date.now() - started < 20)) {
            const row = measuringRows.items.create(next++);
            if (row !== null)
                row.parent = measuringHost;
            rows.push(row);
        }
        measuredWidths = fitColumns(false, rows, measuredWidths);
        unmadeRows += rows.filter(row => row === null).length;
        // Drops the rows, and stops making any still being made.
        measuringRows.model = null;
        if (next < total) {
            measureLater.run = run;
            measureLater.from = next;
            measureLater.start();
            return;
        }
        refitting = false;
        if (!sameValues(measuredWidths, fittedWidths))
            fittedWidths = measuredWidths;
        styleCells();
        if (unmadeRows > 0 && unmadeRetries < 100)
            measureMade.start();
    }
    // Rows not made while their page was still being built: they are measured again a little later, when they can be
    // made, at most for ten seconds. Measured without them, a column fits only its header (the Analysis parameters'
    // names were cut to their icons).
    property int unmadeRows: 0
    property int unmadeRetries: 0
    Timer {
        id: measureMade
        interval: 100
        onTriggered: {
            if (table.gone)
                return;
            table.unmadeRetries++;
            table.refitting = true;
            table.fitWholeModel();
        }
    }
    Timer {
        id: measureLater
        property int run: 0
        property int from: 0
        // Not 0 ms, which keeps a slice always due (PageIncubation in engine_setup.cpp).
        interval: 1
        onTriggered: table.measureRows(run, from)
    }
    // Content that changed while the table was not shown, measured once it is.
    property bool unfitted: false
    onVisibleChanged: {
        if (visible && unfitted)
            refit();
    }
    onOnScreenChanged: {
        if (visible && onScreen && unfitted)
            refit();
    }
    // Whether the table can be seen: in no collapsed group, and on the current item of every SwipeView it is in (a page,
    // a sidebar tab). A SwipeView keeps its other items visible and a collapsed group only clips its content. A large
    // model waits until its table can be seen: a pattern's points kept the window busy for many seconds after a project
    // opened. A small one is measured as soon as it is visible, as it takes little time.
    readonly property bool onScreen: {
        const chain = [];
        for (let item = table; item !== null; item = item.parent) {
            if (item["collapsed"] === true)
                return false;
            if (item instanceof SwipeView && !chain.includes((item as SwipeView).currentItem))
                return false;
            chain.push(item);
        }
        return true;
    }
    // Outside the window: its rows are only measured, and a row in a window costs far more to make and to drop (each
    // cell joins and leaves the window's signals, a scan of all of them).
    readonly property Item measuringHost: Item {
        width: table.width
        DelegateModel {
            id: measuringRows
            model: null
            delegate: table.delegate
        }
    }
    onColumnsChanged: refit()
    // The spare width follows the columns: the last data column's cells take it as padding after their content.
    onColumnWidthsChanged: {
        const spare = fillerIndex >= 0 && fittedWidths.length === columns.length ? Math.max(0, columnWidths[fillerIndex] - (fittedWidths[fillerIndex] ?? 0) - autoColumnPadding) : 0;
        if (spare !== fillerWidth) {
            fillerWidth = spare;
            Qt.callLater(styleCells);
        }
    }
    onModelRevisionChanged: {
        refit();
        Qt.callLater(repairRows);
    }
    onCountChanged: {
        refit();
        Qt.callLater(repairRows);
    }
    onHeightChanged: Qt.callLater(repairRows)
    Component.onCompleted: refit()
    // A view whose rows were all replaced before it laid out again could stop filling and show one stale row of what
    // its count promised (the owner, 2026-11-03): once it has laid out, such a view is rebuilt (ViewRows).
    function repairRows() {
        if (gone || !visible || count === 0)
            return;
        forceLayout();
        ViewRows.refill(table);
    }
    Connections {
        target: table.contentItem
        function onChildrenChanged() {
            Qt.callLater(table.styleCells);
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
            table.refit();
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
    FontMetrics {
        id: boldMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        font.bold: true
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
