// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app

Item {
    width: 600
    height: 500
    ListModel {
        id: rows
        ListElement {
            label: "one"
        }
    }
    Component {
        id: tableComponent
        DataTable {
            width: 500
            columnWidths: [numberColumnWidth, textColumnWidth("label", "id"), -1, -1, 40]
            delegate: Item {
                width: 500
                height: 30
            }
        }
    }
    TestCase {
        name: "TableLayout"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            rows.setProperty(0, "label", "one");
        }
        function test_empty_attach_replace_detach() {
            const table = createTemporaryObject(tableComponent, parent);
            verify(table !== null);
            compare(table.model, null);
            table.sourceModel = undefined;
            compare(table.model, null);
            table.sourceModel = rows;
            tryCompare(table, "count", 1);
            table.sourceModel = null;
            tryCompare(table, "count", 0);
            table.sourceModel = rows;
            tryCompare(table, "count", 1);
            table.sourceModel = undefined;
            tryCompare(table, "count", 0);
        }
        function test_long_ids_preserve_numeric_columns_and_actions() {
            const table = createTemporaryObject(tableComponent, parent, {
                sourceModel: rows
            });
            verify(table !== null);
            rows.setProperty(0, "label", "long.identifier.".repeat(100));
            tryVerify(() => Math.abs(table.resolvedColumnWidths[1] - table.width * 0.25) < 0.1);
            verify(table.resolvedColumnWidths[2] > 0);
            compare(table.resolvedColumnWidths[2], table.resolvedColumnWidths[3]);
            compare(table.resolvedColumnWidths[4], 40);
            rows.setProperty(0, "label", "short");
            tryVerify(() => table.resolvedColumnWidths[1] < table.width * 0.25);
        }
        function test_arrow_font_is_bundled_and_loaded() {
            tryCompare(EaStyle.Fonts.encodeSansRegular, "status", FontLoader.Ready);
            compare(EaStyle.Fonts.encodeSansRegular.name, "Encode Sans");
            verify(String(EaStyle.Fonts.encodeSansRegular.source).includes("EncodeSans-Regular.ttf"));
        }
    }
}
