// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQml.Models

import EasyApplication.Gui.Style as EaStyle
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
    Keys.onPressed: event => ApplicationInfo.tableKeyPressed(event)
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
    // The column margin is separate from the cell's own measured insets (ADR-0029).
    autoColumnPadding: EaStyle.Sizes.tableColumnSpacing * 3
    // The last data column, which holds the spare width as empty space after its content; -1 for none.
    readonly property int fillerIndex: equalColumns || spreadColumns.length > 0 ? -1 : columns.lastIndexOf(-1)
    // Each column's widest text, its header's or a cell's, without the margin; the cells' alone, as last measured.
    property var fittedWidths: []
    property var contentWidths: []
    property bool refitting: true
    // The widths the rule gives, set as columnWidths only when one of them changes: each change makes every row apply
    // the widths again, and the rule is worked out again whenever the table's width moves during a page's layout.
    readonly property var ruledWidths: ApplicationInfo.tableColumnWidths()
    onRuledWidthsChanged: ApplicationInfo.tableApplyRuledWidths(false)
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
    function kindOf(cell) {
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
    onVisibleChanged: ApplicationInfo.tableVisibleChanged()
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
        ApplicationInfo.tableColumnsChanged(false);
        Qt.callLater(repairRows);
    }
    Component.onCompleted: {
        ApplicationInfo.tableApplyRuledWidths(true);
        refit();
    }
    onHeightChanged: Qt.callLater(repairRows)
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
        target: table.model
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
