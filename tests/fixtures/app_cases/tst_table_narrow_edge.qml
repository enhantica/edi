// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtTest

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table whose numbers narrow to fit still ends at its right edge: the pixels its whole-pixel columns leave go to the
// last data column, so the row's button does not stop short of the edge (T3).
Item {
    id: root

    width: 600
    height: 200

    DataTable {
        id: table

        width: 400
        height: 150
        columnKinds: ["index", "value", "value", "value", "value", "value", "value", "control"]
        sourceModel: ListModel {
            ListElement {
                amount: "0.12345"
            }
            ListElement {
                amount: "0.54321"
            }
        }
        header: EaComponents.ListViewHeader {
            Repeater {
                model: 8
                delegate: EaComponents.ListViewLabel {
                    required property int index
                    text: index > 0 && index < 7 ? "v" : ""
                }
            }
        }
        delegate: TableRow {
            id: row

            required property string amount

            Repeater {
                model: 8
                delegate: EaComponents.ListViewLabel {
                    required property int index
                    text: index === 0 ? row.index + 1 : index < 7 ? row.amount : ""
                }
            }
        }
    }

    TestCase {
        name: "TableNarrowEdge"
        when: windowShown

        function laidOut(): bool {
            return table.columnWidths.length === 8 && table.columnWidths.every(width => width > 0);
        }
        function rowEnd(): real {
            return table.columnWidths.reduce((sum, width) => sum + width, 0) + 7 * EaStyle.Sizes.tableColumnSpacing + 2 * table.rowPadding;
        }
        function test_the_row_ends_at_the_edge_at_every_width() {
            tryVerify(laidOut);
            for (const width of [390, 391, 392, 393, 394, 395, 396, 397, 398, 399]) {
                table.width = width;
                tryVerify(() => Math.abs(rowEnd() - width) < 0.01, 1000, `the row ends at ${rowEnd()} of ${width}`);
                // The numbers before the last one stay equally wide (T5).
                for (let column = 2; column < 6; ++column)
                    compare(table.columnWidths[column], table.columnWidths[1]);
            }
        }
    }
}
