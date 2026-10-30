// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

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
    columnWidths: ApplicationInfo.tableColumnWidths()
    // The spare width the last data column holds after its content, as empty space before the row buttons: its
    // cells keep their text where it fits, a right-aligned number by its neighbours.
    property real fillerWidth: 0
    // Each padded cell's own paddings and alignment kind, by cell.
    property var basePaddings: new Map()
    property var cellKinds: new Map()
    // A cell's padding: its own, a spacing more on the side it aligns to, so a right-aligned number and a
    // left-aligned text in neighbouring columns never meet, and in the last data column the spare width after it.
    function columnRowOwner(row) {
        return ApplicationInfo.tableColumnRowOwner(row);
    }
    // Same width distribution as the pinned base ListView, with the original
    // row/cell lifetime retained across each observable width assignment.
    function applyWidths(row) {
        ApplicationInfo.tableApplyWidths(row);
    }
    function padForFiller(cell, column) {
        ApplicationInfo.tablePadForFiller(cell, column);
    }
    // A cell's kind, which sets how it aligns: a number, an icon or button, or text.
    function kindOf(cell) {
        return ApplicationInfo.tableCellKind(cell);
    }
    function alignCell(cell, kind) {
        ApplicationInfo.tableAlignCell(cell, kind);
    }
    property var columnFitLife: ({
            alive: true,
            queued: false
        })
    function scheduleFitColumns() {
        ApplicationInfo.tableScheduleFitColumns();
    }
    Component.onDestruction: ApplicationInfo.tableDestroyed()

    function fitColumns() {
        ApplicationInfo.tableFitColumns();
    }
    // A change of the content fits the columns afresh; scrolling only adds rows to what was measured.
    function refit() {
        ApplicationInfo.tableRefit();
    }
    onColumnsChanged: ApplicationInfo.tableColumnsChanged(false)
    // The spare width follows the columns: the last data column's cells take it as padding after their content.
    onColumnWidthsChanged: ApplicationInfo.tableColumnsChanged(true)
    onModelRevisionChanged: ApplicationInfo.tableColumnsChanged(false)
    onCountChanged: ApplicationInfo.tableColumnsChanged(false)
    Component.onCompleted: refit()
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
