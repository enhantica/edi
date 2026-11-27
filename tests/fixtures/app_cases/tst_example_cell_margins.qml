// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// An example's title, tags and description keep the table's cell margin on both sides, so the row number and the title
// are one em apart (T1).
Item {
    id: root

    width: 400
    height: 200

    ExampleCell {
        id: cell

        width: 300
        height: 100
        title: "Title"
        tagLabels: ["One", "Two"]
        detail: "A description long enough to take more than one line in a cell as narrow as this one is here"
    }

    TestCase {
        name: "ExampleCellMargins"
        when: windowShown

        // The cell's column of lines.
        function lines(): Item {
            return Array.from(cell.children).find(child => child.implicitHeight > 0 && child.children.length >= 3);
        }
        function test_the_lines_keep_the_cell_margin() {
            const column = lines();
            verify(column);
            compare(column.x, AppSizes.tableCellMargin);
            compare(column.width, cell.width - 2 * AppSizes.tableCellMargin);
            for (const line of column.children)
                verify(line.mapToItem(cell, 0, 0).x >= AppSizes.tableCellMargin && line.mapToItem(cell, line.width, 0).x <= cell.width - AppSizes.tableCellMargin + 0.01);
        }
        function test_the_cell_stays_as_tall_as_its_lines() {
            compare(cell.implicitHeight, lines().implicitHeight);
        }
    }
}
