// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQml.Models

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    function revealRow(index: int): bool {
        return ApplicationInfo.tableRevealRow(index);
    }
    function revealItem(item: Item): bool {
        return ApplicationInfo.tableRevealItem(item);
    }

    // The selection model needs an explicit empty model while a page is being attached.
    property var sourceModel: null
    // An item model is shown through a mirror: another block's model of the same kind (the next experiment's rows)
    // keeps the rows made for the last one, each reading its new data (ADR-0102 rule 2). A plain list is shown as it
    // is. Code that calls the model's own functions uses sourceModel.
    readonly property bool mirrorsRows: sourceModel !== null && typeof sourceModel === "object" && typeof sourceModel.rowCount === "function"
    readonly property ListModelMirror rowsMirror: ListModelMirror {
        source: table.mirrorsRows ? table.sourceModel : null
    }
    model: mirrorsRows && rowsMirror ? rowsMirror : (sourceModel ?? null)
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
    Keys.onPressed: event => ApplicationInfo.tableKeyPressed(event)
    // Rows are made when they come into view, never ahead of it: rows made ahead are built a few per frame in
    // the background, and a page's tables kept laying out for about a second after a project opened. The columns fit
    // every row of the model, measured when the content changes (fitWholeModel), so scrolling never moves one (the
    // owner, 2026-10-27).
    cacheBuffer: 0
    // A table in a sidebar fills the room the shown sidebar leaves it, at least three rows (ADR-0103 decision 3), and
    // shows whole rows only: the scroll bar, always shown then, is the cue that there are more (the owner, 2026-11-21:
    // tables stopped after a few rows with room below, a last row was cut at the panel's edge). The room is the
    // sidebar column's height less where the table starts and what follows it, which a new row count does not move.
    // A table elsewhere (a dialog) keeps the cap, as does one that sets its own.
    property Flickable roomColumn: null
    // The rows the table shows in a sidebar, a half row included when more follow (0 until placed); roomRows is
    // that count rounded up, the base's row cap.
    property real roomShown: 0
    // What the table showed before, and when it left it (placeRoom).
    property real roomLeft: 0
    property double roomLeftAt: 0
    property int roomLeftCount: -1
    readonly property int roomRows: Math.ceil(roomShown)
    // Rows of another height than the table's (tableRowHeight, a list's least row: an example's description takes as
    // many lines as it needs): what each has over it, by its row. A row says its height when it has it (noteRowHeight),
    // and the larger one is kept; a new count, width or least row height reads the rows that are made once more. The
    // table's own height never reads them, so a room placed cannot ask for another.
    property var rowExtras: ({})
    property var notedExtras: ({})
    readonly property real readWidth: Math.round(width)
    onReadWidthChanged: Qt.callLater(readRowHeights)
    onTableRowHeightChanged: Qt.callLater(readRowHeights)
    function noteRowHeight(row: int, height: real): void {
        const extra = height - tableRowHeight;
        if (row < 0 || row >= count || extra <= Math.max(rowExtras[row] ?? 0, notedExtras[row] ?? 0) + 0.5)
            return;
        notedExtras[row] = extra;
        Qt.callLater(placeRowHeights);
    }
    function placeRowHeights(): void {
        // A queued call may come as the table goes away.
        if (!columnFitLife.alive || !roomColumn || Object.keys(notedExtras).length === 0)
            return;
        rowExtras = Object.assign({}, rowExtras, notedExtras);
        notedExtras = {};
        placeRoom();
    }
    function readRowHeights(): void {
        if (!columnFitLife.alive || !roomColumn)
            return;
        const extras = {};
        for (const row of contentItem.children)
            if (row.index >= 0 && row.index < count && row.listView === table && itemAtIndex(row.index) === row && row.height - tableRowHeight > 0.5)
                extras[row.index] = row.height - tableRowHeight;
        notedExtras = {};
        rowExtras = extras;
        placeRoom();
    }
    // The height of the table's first `rows` rows, a half row included.
    function rowsHeight(rows: real): real {
        let height = rows * tableRowHeight;
        for (const row in rowExtras)
            height += rowExtras[row] * Math.max(0, Math.min(1, rows - Number(row)));
        return height;
    }
    // The rows a room shows: all of them, or whole rows and half the next, never under 2.5 (T7).
    function rowsIn(room: real): real {
        if (count === 0 || rowsHeight(count) <= room + 0.01)
            return Math.max(1, count);
        let rows = Math.max(2.5, Math.floor(room / tableRowHeight - 0.5) + 0.5);
        while (rows > 2.5 && rowsHeight(rows) > room + 0.01)
            --rows;
        return rows;
    }
    function findRoomColumn() {
        // The sidebar's scrolling column, the nearest around the table.
        for (let item = parent; item; item = item.parent)
            if (item instanceof EaComponents.SideBarColumn)
                return item;
        return null;
    }
    // The tables and the groups of the column (a group is told by its resting height, a table by its room).
    function roomItems(item, tables, groups) {
        for (const child of item.children) {
            if (child.roomShown !== undefined && child.findRoomColumn !== undefined) {
                tables.push(child);
                continue;
            }
            if (child.restingHeight !== undefined)
                groups.push(child);
            roomItems(child, tables, groups);
        }
    }
    function roomHolds(group): bool {
        for (let up = table.parent; up && up !== roomColumn; up = up.parent)
            if (up === group)
                return true;
        return false;
    }
    // Open: shown and in no folded group but those `opening` (a folded group only clips its content).
    function roomOpen(item, opening): bool {
        if (!item.visible)
            return false;
        for (let up = item.parent; up && up !== roomColumn; up = up.parent)
            if (up.restingHeight !== undefined && up.collapsed && !opening.includes(up))
                return false;
        return true;
    }
    // The positioners around a table brought up to date, so the heights read next belong together.
    function layOut(item: var) {
        for (let up = item.parent; up && up !== roomColumn.contentItem; up = up.parent)
            if (typeof up.forceLayout === "function" && up.delegate === undefined)
                up.forceLayout();
    }
    // T7, one rule for every sidebar table (ADR-0103; the owner, 2026-11-24). The open tables of a column share the
    // room that keeps the whole column in view: the column's height less everything else in it, each group at the
    // height it rests at once its fold ends, so an opening group is counted at its open height. A table whose rows fit
    // its share shows them all; one that does not shows whole rows and half the next, the cue that it scrolls, and only
    // it scrolls. Below 2.5 rows a table keeps 2.5 and the column scrolls instead. Tables needing less than an equal
    // share keep their rows and leave the rest to the others. Every table computes the same split, so they agree.
    function placeRoom() {
        // A queued call may come as the table goes away.
        if (!columnFitLife.alive || !roomColumn || !roomColumn.contentItem)
            return;
        const tables = [], groups = [];
        roomItems(roomColumn.contentItem, tables, groups);
        // The table's own folded groups count as open: it is placed before its group opens, at the height it then has.
        const opening = groups.filter(group => group.collapsed && roomHolds(group));
        const open = tables.filter(t => roomOpen(t, opening));
        for (const t of open)
            layOut(t);
        let content = roomColumn.contentHeight;
        for (const group of groups)
            if (group.visible)
                content += (opening.includes(group) ? group.openHeight : group.restingHeight) - group.height;
        const headerOf = t => t.headerItem ? t.headerItem.height : 0;
        // Everything but the open tables' rows; then each table's rows as they would all show.
        for (const t of open)
            content -= t.height - headerOf(t);
        let left = roomColumn.height - content;
        const need = new Map(open.map(t => [t, t.rowsHeight(Math.max(1, t.count))]));
        const share = new Map();
        let waiting = open.slice();
        while (waiting.length > 0) {
            const each = left / waiting.length;
            const fitting = waiting.filter(t => need.get(t) <= each);
            if (fitting.length === 0) {
                for (const t of waiting)
                    share.set(t, each);
                break;
            }
            for (const t of fitting) {
                share.set(t, need.get(t));
                left -= need.get(t);
            }
            waiting = waiting.filter(t => !fitting.includes(t));
        }
        // Each table's rows as shown: all, or whole rows and half the next (never under 2.5); the room that leaves goes
        // round again, a row at a time in the tables' order, as each table's own rounding dropped it (two long tables
        // with room for six rows between them showed 2.5 and 2.5 where 3.5 and 2.5 fit).
        const shown = new Map();
        let used = 0;
        for (const t of open) {
            shown.set(t, t.rowsIn(share.has(t) ? share.get(t) : 0));
            used += t.rowsHeight(shown.get(t));
        }
        const tableRoom = roomColumn.height - content;
        for (let again = true; again; ) {
            again = false;
            for (const t of open) {
                const next = shown.get(t) >= t.count ? shown.get(t) : Math.min(t.count, shown.get(t) + 1);
                if (next === shown.get(t) || used - t.rowsHeight(shown.get(t)) + t.rowsHeight(next) > tableRoom + 0.5)
                    continue;
                used += t.rowsHeight(next) - t.rowsHeight(shown.get(t));
                shown.set(t, next);
                again = true;
            }
        }
        const placed = shown.has(table) ? shown.get(table) : Math.max(2.5, Math.min(count, Math.floor(rowsIn(roomColumn.height - headerOf(table)))));
        if (placed === roomShown)
            return;
        // Never back up to what it left a moment ago with the same rows: a layout answering to the table's own height
        // would go round for ever, and the smaller of the two always fits. New rows are a new placement: a table
        // emptied and filled again at once (marks restored, a project loaded) otherwise stayed at one row (owner,
        // 2026-11-27).
        if (placed > roomShown && placed === roomLeft && count === roomLeftCount && Date.now() - roomLeftAt < 2000)
            return;
        roomLeft = roomShown;
        roomLeftAt = Date.now();
        roomLeftCount = count;
        roomShown = placed;
    }
    Connections {
        target: table.roomColumn
        function onHeightChanged() {
            Qt.callLater(table.placeRoom);
        }
        // The split is the same whatever height the tables have now, so a table taking its share does not move it.
        function onContentHeightChanged() {
            Qt.callLater(table.placeRoom);
        }
    }
    // A sidebar table's columns span its panel, at the side and below (the owner, 2026-11-22; tableColumnWidths).
    readonly property bool spansWidth: roomColumn !== null
    // The header's cells start at the left, as the rows' do (TableRow.anchorContentLeft).
    onHeaderItemChanged: {
        if (!headerItem)
            return;
        for (const item of headerItem.children)
            if (item instanceof Row) {
                item.anchors.horizontalCenter = undefined;
                item.anchors.left = headerItem.left;
            }
    }
    maxRowCountShow: roomColumn && roomShown > 0 ? Math.floor(roomShown) : EaStyle.Sizes.tableMaxRowCountShow
    // Counted in the table's rows: its own rows' heights, where they are another (rowExtras).
    visibleRowCount: roomColumn && roomShown > 0 ? rowsHeight(Math.min(roomShown, Math.max(count, 1))) / tableRowHeight : hasMoreRows ? maxRowCountShow : count
    // Shown only while its rows overflow the height it was given (a dialog may size a table past the row cap):
    // AsNeeded showed a bar for seconds after any move, rows that fit included (the owner, 2026-11-23).
    scrollBarPolicy: contentHeight > height + 0.5 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
    // The row-number column fits the widest number in the bold the current row's number takes, measured again when
    // the font changes (a web font arriving after the first layout).
    // From the row count alone: a measuring pass advances modelRevision while rows that read this are made.
    readonly property real numberColumnWidth: Math.ceil(boldMetrics.advanceWidth(String(Math.max(1, count)))) + AppSizes.tableCellMargin * 2
    property int modelRevision: 0
    // The one column rule (ADR-0029; the owner, 2026-10-24 and 2026-10-27). The row-number column and every flex
    // column (-1) fit their header and their widest cell, each with the same margin, so every two neighbours sit as
    // far apart. Numbers are right-aligned under right-aligned headers, text left-aligned, icons centred. An empty
    // filler cell after the last data column takes the rest of the row, so nothing moves towards the row buttons,
    // which keep their widths at the right. `equalColumns` keeps the flex columns equal instead (atom sites, atomic
    // displacements, the Analysis parameters), and `spreadColumns` shares the rest among those columns after their
    // fitted widths (Measured data). A row too narrow for its texts loses the margins first, then narrows its text
    // columns; a number column keeps its widest text, and a row still too wide scrolls sideways. Widths follow the content: a change of the content fits them again,
    // and scrolling changes none.
    // The shared column model (ADR-0103 decision 4): a table declares each column's kind and nothing else, and the
    // widths, the spare width and the alignments follow from the kinds, the same for every table (the owner,
    // 2026-11-22). A kind is one of
    //   "index"   the row number;
    //   "mark"    a small icon at the row's start (a colour, a datablock's icon);
    //   "name"    text a user gave: cut in its middle only when the sidebar cannot fit it;
    //   "text", "short"    fixed text, at a long or a short text's width;
    //   "number", "value", "uncertainty", "displacement", "change"    a number at its content type's width;
    //   "unit"    a unit, right after its value;
    //   "control" a check box or a button: at the table's right edge;
    // or a number, a fixed width (a selector sized from its options). A number, unit, mark, control or the row number
    // takes its kind's width or its header's, whichever is wider; a text column its header or its widest text. The spare
    // is left before the controls, or at the right end; nothing scrolls sideways (the owner, 2026-11-23). A table that
    // sets `columns` itself (the parameter table, which drops columns) keeps its own rule.
    property var columnKinds: []
    // Where a text column's texts are, by column: the model role it shows, or {role, edited: true} for a column of
    // inputs (measured in the bold an edit takes, with room for the caret). When every text column names one, the
    // widths come from the kinds, the headers and the model alone: no row is made to measure them, so they are known
    // while the table's group is folded and a first unfold changes nothing (edi ADR-0105). A table
    // whose text is not a plain role (icons, a selector, a derived text) is measured from its rows.
    property var columnTexts: []
    readonly property bool kindModel: columnKinds.length > 0
    function kindIsControl(kind: var): bool {
        return kind === "control" || kind === "mark";
    }
    // The gap between two neighbouring columns' content: each cell's margin and the column spacing, as in the Analysis
    // table (the owner, 2026-11-23; the layout check's limit).
    readonly property real contentGap: AppSizes.tableCellMargin * 2 + EaStyle.Sizes.tableColumnSpacing
    readonly property real columnSpacing: EaStyle.Sizes.tableColumnSpacing
    property var columns: kindModel ? columnKinds.map((kind, index) => typeof kind === "number" ? kind : kind === "index" ? numberColumnWidth : kind === "control" ? controlColumnWidth + (index < columnKinds.length - 1 ? AppSizes.tableCellMargin : 0) : kind === "mark" ? AppSizes.tableControlWidth : -1) : []
    // A row button's box, as wide as a button in a data cell, and the cell margins that part it from its neighbours; the
    // last one ends at its column's edge (T1, T3). A mark's column is its icon's and the margins.
    readonly property real controlColumnWidth: EaStyle.Sizes.tableRowHeight - 4 + AppSizes.tableCellMargin
    // Whether the row buttons' boxes keep that margin: the columns above are that wide.
    property bool insetButtons: kindModel
    // One type per column ("number", "short", "text", or "" for an icon, a check box or a column sized by its header):
    // when given, the widths come from the types and no row is measured, so changing data never moves a column
    // (ADR-0103 rule 4). A table without it fits its columns to its rows (ADR-0029).
    property var columnTypes: kindModel ? columnKinds.map(kind => typeof kind === "number" || kind === "index" || kindIsControl(kind) ? "" : kind) : []
    // The type of every flex column (-1) that columnTypes leaves untyped, e.g. "number" for a table of values.
    property string defaultColumnType: ""
    // The width the columns need. A number column is never narrower than its widest text, so a row wider than the
    // table scrolls sideways, its header with it.
    // A hidden (zero-width) column takes no spacing: the row's positioner skips it.
    readonly property real rowsWidth: columnWidths.reduce((sum, width) => sum + Math.max(0, width), 0) + EaStyle.Sizes.tableColumnSpacing * Math.max(0, columnWidths.filter(width => width > 0.5).length - 1) + rowPadding * 2
    // A sidebar table never scrolls sideways: its columns are sized to its width (ADR-0103 decision 4); only a table
    // outside the sidebar (a dialog's) may, when its rows are wider.
    readonly property bool scrollsSideways: !spansWidth && rowsWidth > width + 0.5
    contentWidth: scrollsSideways ? rowsWidth : width
    flickableDirection: scrollsSideways ? Flickable.AutoFlickDirection : Flickable.VerticalFlick
    // The same policy as the vertical bar, so it fades when idle as every other scroll bar does.
    ScrollBar.horizontal: EaElements.ScrollBar {
        policy: table.scrollsSideways ? table.scrollBarPolicy : ScrollBar.AlwaysOff
        interactive: table.scrollBarInteractive
    }
    // A table of values the user does not edit (calculated, or read from a file): its rows take no hover tint and its
    // value cells (CellLabel, NumberLabel) the grey of a cell shown, not edited, so editable tables stand out.
    property bool readOnly: false
    property bool equalColumns: false
    property var spreadColumns: []
    // The column margin is separate from the cell's own measured insets (ADR-0029).
    // A kind-model table's columns are at their content's width with no margin (the cell's inset is its padding).
    autoColumnPadding: kindModel ? 0 : EaStyle.Sizes.tableColumnSpacing * 3
    // The column that takes the spare width: a flexible name (text) column; in a table without one the last flexible
    // column, which holds it as empty space after its content, so every column stays minimal from the left and the
    // row's buttons stay at the right (the owner, 2026-11-22).
    readonly property int fillerIndex: {
        // A table that sets its own widths (the parameter table) has its own spare column.
        if (equalColumns || spreadColumns.length > 0 || !kindFloors)
            return -1;
        // The kind model: the last data column holds the spare as empty space after its content, before the controls;
        // no column, a name included, is wider than its content (the owner, 2026-11-23).
        if (kindModel) {
            for (let index = columnKinds.length - 1; index > 0; --index) {
                const kind = columnKinds[index];
                if (typeof kind === "string" && kind !== "index" && !kindIsControl(kind))
                    return index;
            }
            return -1;
        }
        // Without kinds too: the last flexible column, so the spare is one block just before the controls (T4).
        const flexible = columns.map((width, index) => width === -1 ? index : -1).filter(index => index >= 0);
        return flexible.length > 0 ? flexible[flexible.length - 1] : -1;
    }
    // Each column's widest text, its header's or a cell's, without the margin; the cells' alone, as last measured.
    property var fittedWidths: []
    // The width every column needs at its content, with the spacings, the row padding and the border (the width check
    // reads it).
    readonly property real naturalWidth: {
        if (!kindModel || fittedWidths.length !== columns.length)
            return 0;
        let sum = 0, taking = 0;
        for (let index = 0; index < columns.length; ++index) {
            const column = columns[index];
            if (column === -1) {
                sum += fittedWidths[index] ?? 0;
                ++taking;
            } else if (column > 0.5) {
                sum += column;
                ++taking;
            }
        }
        return sum + EaStyle.Sizes.tableColumnSpacing * Math.max(0, taking - 1) + rowPadding * 2;
    }
    property var contentWidths: []
    property bool refitting: true
    // The widths the rule gives, set as columnWidths only when one of them changes: each change makes every row apply
    // the widths again, and the rule is worked out again whenever the table's width moves during a page's layout.
    // Worked out only while the table can be seen: a sidebar width change on a page switch otherwise re-ruled every
    // table of every page (ADR-0102: hidden views do no work, the owner, 2026-11-23); shown again, it takes the width
    // it then has.
    readonly property var ruledWidths: visible ? ApplicationInfo.tableColumnWidths() : columnWidths
    onRuledWidthsChanged: ApplicationInfo.tableApplyRuledWidths(false)
    // The spare width the last data column holds after its content, as empty space before the row buttons: its
    // cells keep their text where it fits, a right-aligned number by its neighbours.
    property real fillerWidth: 0
    // Each padded cell's own paddings and alignment kind, by cell.
    property var basePaddings: new Map()
    property var cellKinds: new Map()
    // A cell's padding: its own, at least the cell margin on the side it aligns to, as much as its column keeps on the
    // other side, so neighbouring contents are one em apart whatever their alignment (T1), and in the last data column
    // the spare width after it. A
    // check box, which centres itself in its room, is pushed to the right edge by its left padding. A `fresh` cell, made
    // only to be measured, keeps its own paddings in no map, and the base paddings are returned.
    function columnRowOwner(row) {
        return ApplicationInfo.tableColumnRowOwner(row);
    }
    // Same width distribution as the pinned base ListView, with the original
    // row/cell lifetime retained across each observable width assignment.
    function applyWidths(row) {
        ApplicationInfo.tableApplyWidths(row);
    }
    function padForFiller(cell, column, kind = undefined, fresh = false) {
        return ApplicationInfo.tablePadForFiller(cell, column, kind, fresh);
    }
    property var checkCells: new Set()
    // A cell's kind, which sets how it aligns: a number, an icon or button, or text. A row button is checkable too, so
    // it is told from a check box by its icon first.
    // A cell's styling kind: from the column's declared kind in the kind model (numbers right, text left, controls as
    // the cell is), else from the cell itself.
    function kindOf(cell, index) {
        if (kindModel && index !== undefined && index < columnKinds.length) {
            const kind = columnKinds[index];
            if (typeof kind === "string" && !kindIsControl(kind) && kind !== "index")
                return ["number", "value", "uncertainty", "displacement", "change"].includes(kind) ? "number" : "text";
        }
        return ApplicationInfo.tableCellKind(cell);
    }
    function alignCell(cell, kind, fresh = false) {
        ApplicationInfo.tableAlignCell(cell, kind, fresh);
    }
    property var columnFitLife: ({
            alive: true,
            queued: false
        })
    function scheduleFitColumns() {
        ApplicationInfo.tableScheduleFitColumns();
    }
    Component.onDestruction: ApplicationInfo.tableDestroyed()

    // Styles the cells of `rows` (alignment and padding), the view's rows when null, and returns the widths their cells
    // need, at least `from` (a part of the model measured before). Only the whole model is measured (fitWholeModel); a
    // row the view makes, scrolled into view, is only styled and takes the widths the model was measured to (the owner,
    // 2026-10-27).
    function fitColumns(rows = null, from = null) {
        return ApplicationInfo.tableFitColumns(rows, from);
    }
    // The fitted widths: each column's header or its widest measured cell. A change of the header alone needs no new
    // measure of the rows.
    function combineWidths() {
        ApplicationInfo.tableCombineWidths();
    }
    // A change of the content fits the columns afresh to every row of the model (fitWholeModel), once the table shows.
    function refit() {
        ApplicationInfo.tableRefit();
    }
    // The cells of rows the view made, styled as the measured ones are.
    function styleCells() {
        ApplicationInfo.tableStyleCells();
    }
    // Forgets the cells of a row the view dropped, which would otherwise stay in the maps, each lookup scanning them.
    function forgetCells(cells) {
        ApplicationInfo.tableForgetCells(cells);
    }
    // Every row of the model is made beside the view, measured with the header, and dropped: the columns fit the widest
    // row wherever it is, and scrolling changes no width. A table not shown waits until it is.
    function fitWholeModel() {
        ApplicationInfo.tableFitWholeModel();
    }
    // A model of up to this many rows is measured at once, so a table settles while its group unfolds (a 112-point
    // background did not, measured a frame at a time). A larger one (a pattern's points) is measured a frame's worth
    // of rows at a time, so the window keeps responding; a new change of the content starts it again.
    readonly property int measuredAtOnce: 200
    // A refit of a table that has its widths already is measured in slices like a long model, whatever its length, and
    // the columns keep their widths until it ends (ADR-0102 rule 2); only the first fit is made at once.
    property bool liveRefit: false
    // Parameter columns reserve their kind's typical width, a kind's columns equal (tableCombineWidths); a table that
    // sets its own widths turns it off.
    // Drawn only once its columns have their widths from a finished measure and, in a sidebar, its room is placed: its
    // first drawn frame is its
    // layout, which then holds (T6, T7; the owner, 2026-11-23: tables changing their layout while a group opens). It
    // takes its place meanwhile.
    readonly property bool laidOut: columnWidths.length > 0 && columnWidths.every(width => width !== -1) && (roomColumn === null || roomShown > 0) && (!measureRunning || measuredEnough)
    property bool drawn: false
    onLaidOutChanged: if (laidOut)
        drawn = true
    opacity: drawn ? 1 : 0
    // A table whose layout never resolves (nothing left to measure) still shows; one being measured waits for it.
    Timer {
        running: table.visible && !table.drawn
        interval: 1500
        repeat: true
        onTriggered: if (!table.measureRunning && !table.refitting)
            table.drawn = true
    }
    property bool kindFloors: true
    // The titles' widths of the kind-reserved columns, kept for the rule's floors (tableColumnWidths).
    property var kindHeadings: []
    property bool measureSliced: false
    // A measure in progress, and whether the content changed meanwhile (it then runs once more when it ends).
    property bool measureRunning: false
    // A first measure that has run for 400 ms: the table shows with the rows it has measured, and the rest follow.
    property bool measuredEnough: false
    property double measureSince: 0
    property bool measureAgain: false
    // The whole model measured again a second after its values last changed (tableFitWholeModel).
    Timer {
        id: quietRefit
        interval: 1000
        onTriggered: table.refit()
    }
    property int measureRun: 0
    property var measuredWidths: null
    function measureRows(run, from) {
        ApplicationInfo.tableMeasureRows(run, from);
    }
    Timer {
        id: measureLater
        property int run: 0
        property int from: 0
        // Not 0 ms, which keeps a slice always due (PageIncubation in engine_setup.cpp).
        interval: 1
        onTriggered: table.measureRows(run, from)
    }
    // Rows not made while their page is still built in the background are measured a little later, when they can be
    // made, for at most ten seconds. Measured without them, a column fits only its header.
    property int unmadeRetries: 0
    Timer {
        id: measureMade
        property int run: 0
        property int from: 0
        interval: 100
        onTriggered: table.measureRows(run, from)
    }
    // Content that changed while the table was not shown, measured once it is.
    property bool unfitted: false
    // onScreen can miss the change that shows the table (a large table on the page a project opened onto stayed
    // unmeasured, Name taking the whole width): a visible table still waiting looks again a few times a second.
    Timer {
        interval: 250
        repeat: true
        running: table.unfitted && table.visible
        onTriggered: if (ApplicationInfo.tableOnScreen())
            table.refit()
    }
    onVisibleChanged: {
        ApplicationInfo.tableVisibleChanged();
        // Rows made while it was hidden may have had another width's heights.
        Qt.callLater(readRowHeights);
    }
    onOnScreenChanged: ApplicationInfo.tableOnScreenChanged()
    // Whether the table can be seen: in no collapsed group, and on the current item of every SwipeView it is in (a page,
    // a sidebar tab). A large model waits until its table can be seen: a pattern's points kept the window busy for many
    // seconds after a project opened. A small one is measured as soon as it is visible, as it takes little time.
    readonly property bool onScreen: ApplicationInfo.tableOnScreen()
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
    // A new layout of the flex columns measures the rows again; a fixed column's new width only works out the rule again.
    property string flexLayout: ""
    onColumnsChanged: ApplicationInfo.tableColumnLayoutChanged()
    // The spare width follows the columns: the last data column's cells take it as padding after their content.
    onColumnWidthsChanged: ApplicationInfo.tableColumnsChanged(true)
    onModelRevisionChanged: {
        ApplicationInfo.tableColumnsChanged(false);
        Qt.callLater(repairRows);
    }
    onCountChanged: {
        snapIntoBounds();
        ApplicationInfo.tableColumnsChanged(false);
        Qt.callLater(repairRows);
        // Nothing else asks: the table's own height, which would, waits for its room (T7).
        Qt.callLater(readRowHeights);
        Qt.callLater(placeRoom);
    }
    // Fewer rows (a filter, a removal) leave the old scroll beyond the new end, which ListView then eases back, so the
    // rows slid in under a blank band (the owner, 2026-11-17). The view moves at once instead: to the top when every row
    // fits, else to the nearest position that shows rows.
    onContentHeightChanged: snapIntoBounds()
    onOriginYChanged: snapIntoBounds()
    function snapIntoBounds() {
        if (moving || dragging || flicking)
            return;
        const top = originY;
        const bottom = count <= maxRowCountShow ? top : Math.max(top, originY + contentHeight - height);
        if (contentY < top - 0.5 || contentY > bottom + 0.5)
            contentY = Math.min(Math.max(contentY, top), bottom);
    }
    Component.onCompleted: {
        if (laidOut)
            drawn = true;
        ApplicationInfo.tableApplyRuledWidths(true);
        refit();
        roomColumn = findRoomColumn();
        Qt.callLater(readRowHeights);
        Qt.callLater(placeRoom);
    }
    onHeightChanged: {
        snapIntoBounds();
        Qt.callLater(repairRows);
        Qt.callLater(keepHeaderOnTop);
    }
    // The header stays at the top of the view, over the rows scrolled under it. A scroll set while the view was laying
    // out could leave it where the previous scroll put it, with a slice of an earlier row above it.
    onContentYChanged: Qt.callLater(keepHeaderOnTop)
    function keepHeaderOnTop() {
        if (headerItem && headerPositioning === ListView.OverlayHeader && Math.abs(headerItem.y - contentY) >= 0.5)
            headerItem.y = contentY;
    }
    // A view whose rows were all replaced before it laid out again could stop filling and show one stale row of what
    // its count promised (the owner, 2026-11-03): once it has laid out, such a view is rebuilt (ViewRows).
    function repairRows() {
        if (!columnFitLife.alive || !visible || count === 0)
            return;
        forceLayout();
        ViewRows.refill(table);
    }
    Connections {
        property var ownerLife: null
        Component.onCompleted: ApplicationInfo.tableOwnerCallback(3)
        target: table.contentItem
        function onChildrenChanged() {
            ApplicationInfo.tableOwnerCallback(0);
        }
    }
    // A header whose cells change after it was made (a column per structure arriving with the calculation) has
    // them sized and the columns fitted again.
    Connections {
        property var ownerLife: null
        Component.onCompleted: ApplicationInfo.tableOwnerCallback(3)
        target: table.headerItem
        ignoreUnknownSignals: true
        function onImplicitColumnWidthsChanged() {
            ApplicationInfo.tableOwnerCallback(1);
        }
    }
    // Long IDs and paths must leave room for the numeric cells and row controls.
    property real maximumTextColumnShare: 0.25
    // Each measured role's text width per row. An update measures only the rows it names, and the column
    // only changes when one of those widths did: a scan's rows update one by one, hundreds of times.
    property var rowWidths: ({})

    function textWidth(row: int, role: string): real {
        return ApplicationInfo.tableTextWidth(row, role);
    }
    // The width of `text` in the table's font.
    function advance(text: string): real {
        return ApplicationInfo.tableAdvance(text);
    }
    function textColumnWidth(role: string, title: string): real {
        return ApplicationInfo.tableTextColumnWidth(role, title, false);
    }
    // A fixed column sized by its type ("number", "short", "text") and its title, never by its rows (ADR-0103 rule 4).
    function typeColumnWidth(type: string, title: string): real {
        return ApplicationInfo.tableTypeColumnWidth(type, title);
    }
    // The widest of the column's texts and its title, with a cell's margins, however wide the table is.
    function naturalTextColumnWidth(role: string, title: string): real {
        return ApplicationInfo.tableTextColumnWidth(role, title, true);
    }
    // Cleared in place: the bindings that read the cache depend on modelRevision, never on the cache itself.
    function forgetWidths() {
        ApplicationInfo.tableForgetWidths();
    }
    function remeasure() {
        ApplicationInfo.tableRemeasure();
    }

    // A table with a current row (the base's `currentRow`, which its moving accent marker shows; edi ADR-0017 §11)
    // selects no row, since the base draws a bar on a selected (clicked) row, which would show at once beside the
    // marker (the owner, 2026-10-13).
    property bool marksCurrentRow: false
    selectable: !marksCurrentRow

    onModelChanged: forgetWidths()
    // While traced, each model reset and its row count: rows remade on a reset are a GUI-thread cost.
    Connections {
        target: ApplicationInfo.traceTables() ? table.sourceModel : null
        ignoreUnknownSignals: true
        function onModelReset() {
            console.warn(`table reset: ${table.objectName} ${table.count}`);
        }
        function onLayoutChanged() {
            console.warn(`table layout: ${table.objectName} ${table.count}`);
        }
    }

    FontMetrics {
        id: metrics
        property var ownerLife: null
        Component.onCompleted: ApplicationInfo.tableOwnerCallback(3)
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        onFontChanged: ApplicationInfo.tableOwnerCallback(2)
    }
    FontMetrics {
        id: boldMetrics
        property var ownerLife: null
        Component.onCompleted: ApplicationInfo.tableOwnerCallback(3)
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        font.bold: true
        onFontChanged: ApplicationInfo.tableOwnerCallback(2)
    }
    Connections {
        property var ownerLife: null
        Component.onCompleted: ApplicationInfo.tableOwnerCallback(3)
        // Only an item model signals changed rows; a plain list has nothing to connect.
        target: table.mirrorsRows ? table.rowsMirror : null
        ignoreUnknownSignals: true
        function onDataChanged(topLeft, bottomRight) {
            ApplicationInfo.tableDataChanged(topLeft, bottomRight);
        }
        function onCountChanged() {
            ApplicationInfo.tableOwnerCallback(2);
        }
        function onModelReset() {
            ApplicationInfo.tableOwnerCallback(2);
        }
        function onRowsMoved() {
            ApplicationInfo.tableOwnerCallback(2);
        }
        function onLayoutChanged() {
            ApplicationInfo.tableOwnerCallback(2);
        }
    }
}
