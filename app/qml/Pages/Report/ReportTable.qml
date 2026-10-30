// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table of the report preview, set as the HTML report's tables (the owner's reference report, 2026-10-13), built as
// every edi table is (edi ADR-0029): a list of TableRows and ListView cells, a shaded header, alternating rows one
// line apart, selecting nothing, and the numbers of a column aligned on their decimal point. Without `columns` it is
// a key-value table, its keys set apart from their values. A table wider than its place scrolls sideways.
Flickable {
    id: table

    property var columns: []
    property var rows: []
    readonly property bool keyValue: columns.length === 0
    readonly property int columnCount: keyValue ? (rows.length > 0 ? rows[0].length : 0) : columns.length
    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The reference's 20.4 pt line and 6 pt column padding for its 10.04 pt body, and its key column's 28 px.
    readonly property real rowHeight: Math.round(em * 20.4 / 10.04)
    readonly property real padding: Math.round(em * 6 / 10.04)
    readonly property real keyGap: Math.round(em * 2)
    readonly property real border: EaStyle.Sizes.borderThickness
    // A long table (an experiment's thousands of data points) shows a window of rows that scrolls; the list builds each
    // row as it comes into view, so the preview stays responsive.
    readonly property bool windowed: rows.length > 100
    readonly property int windowRows: 20
    // Every width is measured with the cells' own font, and again when it changes: a font that loads after the table
    // is made (macOS) would otherwise leave the columns measured with the fallback one, and clip their text.
    readonly property real dotWidth: ApplicationInfo.reportTableDotWidth()
    // Per column: whether its cells are numbers, the widths of their parts before and after the decimal point, and
    // the column's width.
    readonly property var layout: ApplicationInfo.reportTableLayout()
    // The list's width: the columns, the spacing the rows put between them and the frame, and a windowed table's scroll
    // bar clear of the last column.
    readonly property real tableWidth: ApplicationInfo.reportTableWidth()

    // A number's parts: before its decimal point, and after it (an s.u. bracket, an exponent and units after a space).
    // Null for a text that is not a number.
    function split(text: string): var {
        return ApplicationInfo.reportTableSplit(text);
    }

    width: Math.min(tableWidth, parent ? parent.width : tableWidth)
    height: contentHeight + (horizontal.visible ? horizontal.height : 0)
    contentWidth: tableWidth
    contentHeight: list.height
    flickableDirection: Flickable.HorizontalFlick
    interactive: contentWidth > width
    boundsBehavior: Flickable.StopAtBounds
    clip: true
    visible: rows.length > 0
    ScrollBar.horizontal: EaElements.ScrollBar {
        id: horizontal
        policy: table.contentWidth > table.width ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
    }

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: table.em
    }

    // One cell: a number on its decimal point, any other text from the left, each piece a ListView label.
    component Cell: Item {
        id: cell

        required property int column
        required property string text
        readonly property var parts: table.layout[column] && table.layout[column].numeric ? table.split(text) : null

        width: table.layout[column] ? table.layout[column].width : 0
        height: table.rowHeight

        EaComponents.ListViewLabel {
            visible: !cell.parts
            width: cell.width
            leftPadding: table.padding
            rightPadding: table.padding
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideNone
            // An agreement factor with its subscript (FactorText).
            textFormat: FactorText.has(cell.text) ? Text.RichText : Text.PlainText
            text: FactorText.has(cell.text) ? FactorText.rich(cell.text) : cell.text
        }
        Row {
            visible: cell.parts !== null
            x: cell.width - table.padding - width
            height: cell.height
            EaComponents.ListViewLabel {
                width: table.layout[cell.column] ? table.layout[cell.column].left : 0
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideNone
                textFormat: Text.PlainText
                text: cell.parts ? cell.parts.left : ""
            }
            // A number without a point gives the point's place to what follows its digits (an s.u. or units), so
            // `611(16)` stays together and its digits still end where the column's points are.
            EaComponents.ListViewLabel {
                visible: cell.parts !== null && cell.parts.dot
                width: table.dotWidth
                horizontalAlignment: Text.AlignLeft
                elide: Text.ElideNone
                text: "."
            }
            EaComponents.ListViewLabel {
                width: (table.layout[cell.column] ? table.layout[cell.column].right : 0) + (cell.parts && cell.parts.dot ? 0 : table.dotWidth)
                horizontalAlignment: Text.AlignLeft
                elide: Text.ElideNone
                textFormat: Text.PlainText
                text: cell.parts ? cell.parts.right : ""
            }
        }
    }

    // The rows as a list model, each row's cells in one string, as the list's selection model needs a model it can
    // index.
    readonly property string cellSeparator: "\u001f"
    ListModel {
        id: rowModel
    }
    // Rebuilt in place: a row keeps its delegate while it exists, and only rows past the new end are removed.
    onRowsChanged: ApplicationInfo.reportTableRowsChanged()

    // The cells size themselves from `layout`, so the list sets no column widths.
    EaComponents.ListView {
        id: list

        width: table.tableWidth
        tableRowHeight: table.rowHeight
        rowPadding: 0
        maxRowCountShow: table.windowed ? table.windowRows : Math.max(1, rowModel.count)
        selectable: false
        multiSelection: false
        cacheBuffer: 0
        defaultInfoText: ""
        model: rowModel
        scrollBarPolicy: table.windowed ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff

        // The header: shaded, a number column's title centred over its numbers; none for a key-value table.
        header: table.keyValue ? null : headerComponent

        delegate: TableRow {
            id: line

            required property string cells

            Repeater {
                model: line.cells.split(table.cellSeparator)
                delegate: Cell {
                    required property string modelData
                    required property int index
                    column: index
                    text: modelData
                }
            }
        }
    }
    Component {
        id: headerComponent

        EaComponents.ListViewHeader {
            Repeater {
                // The lists themselves are the models, so a delegate holds its own text while a shorter list
                // replaces it.
                model: table.columns
                delegate: EaComponents.ListViewLabel {
                    id: heading
                    required property string modelData
                    required property int index
                    width: table.layout[index] ? table.layout[index].width : 0
                    leftPadding: table.padding
                    rightPadding: table.padding
                    horizontalAlignment: table.layout[index] && table.layout[index].numeric ? Text.AlignHCenter : Text.AlignLeft
                    elide: Text.ElideNone
                    textFormat: Text.PlainText
                    text: modelData
                }
            }
        }
    }
}
