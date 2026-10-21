// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A table of the report preview, set as the HTML report's tables (the owner's reference report, 2026-10-13): a thin
// border, a shaded header and alternating rows in the app tables' colours, rows one line apart, and the numbers of a
// column aligned on their decimal point. No row tints on hover: the preview is a document. Without `columns` it is a key-value table, its
// keys set apart from their values. A table wider than its place scrolls sideways.
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
    // A long table (an experiment's thousands of data points) shows a window of rows that scrolls, each row built as
    // it comes into view, so the preview stays responsive.
    readonly property bool windowed: rows.length > 100
    readonly property int windowRows: 20
    // Every width is measured with the cells' own font, and again when it changes: a font that loads after the table
    // is made (macOS) would otherwise leave the columns measured with the fallback one, and clip their text.
    readonly property real dotWidth: {
        metrics.font;  // re-measured when the font changes
        return Math.ceil(metrics.advanceWidth("."));
    }
    // Per column: whether its cells are numbers, the widths of their parts before and after the decimal point, and
    // the column's width.
    readonly property var layout: {
        metrics.font;  // re-measured when the font changes
        const out = [];
        for (let column = 0; column < columnCount; ++column) {
            let numbers = 0, others = 0, left = 0, right = 0, plain = 0;
            for (const row of rows) {
                const text = row[column] ?? "";
                if (text === "")
                    continue;
                const parts = table.split(text);
                if (parts) {
                    ++numbers;
                    left = Math.max(left, metrics.advanceWidth(parts.left));
                    right = Math.max(right, metrics.advanceWidth(parts.right));
                } else {
                    ++others;
                }
                plain = Math.max(plain, metrics.advanceWidth(text));
            }
            const numeric = numbers > 0 && others === 0;
            const header = keyValue ? 0 : metrics.advanceWidth(columns[column]);
            const content = numeric ? Math.ceil(left) + dotWidth + Math.ceil(right) : Math.ceil(plain);
            out.push({
                "numeric": numeric,
                "left": Math.ceil(left),
                "right": Math.ceil(right),
                "width": Math.max(content, Math.ceil(header)) + 2 * padding + (keyValue && column === 0 ? keyGap : 0)
            });
        }
        return out;
    }
    // A windowed table keeps its scroll bar clear of the last column.
    readonly property real tableWidth: layout.reduce((sum, column) => sum + column.width, 0) + 2 * border + (windowed ? vertical.width : 0)

    // A number's parts: before its decimal point, and after it (an s.u. bracket, an exponent and units after a space).
    // Null for a text that is not a number.
    function split(text: string): var {
        const match = /^([-−+]?[0-9]*)(\.?)([0-9]*(?:\([0-9]+\))?(?:[eE][-+]?[0-9]+)?(?: [^ 0-9].*)?)$/.exec(text);
        if (!match || !/[0-9]/.test(match[1] + match[3]))
            return null;
        return {
            "left": match[1],
            "dot": match[2] !== "",
            "right": match[3]
        };
    }

    width: Math.min(tableWidth, parent ? parent.width : tableWidth)
    height: contentHeight + (horizontal.visible ? horizontal.height : 0)
    contentWidth: tableWidth
    contentHeight: body.height + 2 * border
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

    // One row, its background alternating.
    component Line: Rectangle {
        id: line
        required property var modelData
        required property int index
        width: body.width
        height: table.rowHeight
        color: index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1

        Row {
            Repeater {
                model: line.modelData
                delegate: Cell {
                    required property string modelData
                    required property int index
                    column: index
                    text: modelData
                }
            }
        }
    }

    // One cell: a number on its decimal point, any other text from the left.
    component Cell: Item {
        id: cell

        required property int column
        required property string text
        readonly property var parts: table.layout[column] && table.layout[column].numeric ? table.split(text) : null

        width: table.layout[column] ? table.layout[column].width : 0
        height: table.rowHeight

        Text {
            visible: !cell.parts
            x: table.padding
            anchors.verticalCenter: parent.verticalCenter
            font: metrics.font
            color: EaStyle.Colors.themeForeground
            // An agreement factor with its subscript (FactorText).
            textFormat: FactorText.has(cell.text) ? Text.RichText : Text.PlainText
            text: FactorText.has(cell.text) ? FactorText.rich(cell.text) : cell.text
        }
        Row {
            visible: cell.parts !== null
            x: cell.width - table.padding - width
            anchors.verticalCenter: parent.verticalCenter
            Text {
                width: table.layout[cell.column] ? table.layout[cell.column].left : 0
                horizontalAlignment: Text.AlignRight
                font: metrics.font
                color: EaStyle.Colors.themeForeground
                textFormat: Text.PlainText
                text: cell.parts ? cell.parts.left : ""
            }
            // A number without a point gives the point's place to what follows its digits (an s.u. or units), so
            // `611(16)` stays together and its digits still end where the column's points are.
            Text {
                visible: cell.parts !== null && cell.parts.dot
                width: table.dotWidth
                font: metrics.font
                color: EaStyle.Colors.themeForeground
                text: "."
            }
            Text {
                width: (table.layout[cell.column] ? table.layout[cell.column].right : 0) + (cell.parts && cell.parts.dot ? 0 : table.dotWidth)
                font: metrics.font
                color: EaStyle.Colors.themeForeground
                textFormat: Text.PlainText
                text: cell.parts ? cell.parts.right : ""
            }
        }
    }

    Column {
        id: body

        x: table.border
        y: table.border
        width: table.tableWidth - 2 * table.border

        // The header: shaded, a line under it, a number column's title centred over its numbers.
        Rectangle {
            visible: !table.keyValue
            width: body.width
            height: table.rowHeight
            color: EaStyle.Colors.contentBackground

            Row {
                // The lists themselves are the models, so a delegate holds its own text while a shorter list
                // replaces it.
                Repeater {
                    model: table.keyValue ? [] : table.columns
                    delegate: Item {
                        id: heading
                        required property string modelData
                        required property int index
                        width: table.layout[index] ? table.layout[index].width : 0
                        height: table.rowHeight
                        Text {
                            x: table.layout[heading.index] && table.layout[heading.index].numeric ? Math.round((heading.width - width) / 2) : table.padding
                            anchors.verticalCenter: parent.verticalCenter
                            font: metrics.font
                            // The text colour, as the app tables' headers have it.
                            color: EaStyle.Colors.themeForeground
                            textFormat: Text.PlainText
                            text: heading.modelData
                        }
                    }
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: table.border
                color: EaStyle.Colors.appBorder
            }
        }
        Repeater {
            model: table.windowed ? [] : table.rows
            delegate: Line {}
        }
        ListView {
            visible: table.windowed
            width: body.width
            height: visible ? table.windowRows * table.rowHeight : 0
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: table.windowed ? table.rows : []
            delegate: Line {}
            ScrollBar.vertical: EaElements.ScrollBar {
                id: vertical
                policy: ScrollBar.AlwaysOn
            }
        }
    }
    // The thin border, over the cells.
    Rectangle {
        width: table.tableWidth
        height: body.height + 2 * table.border
        color: "transparent"
        border.width: table.border
        border.color: EaStyle.Colors.appBorder
    }
}
