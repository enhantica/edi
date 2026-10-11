// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents
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
    Component {
        id: baseTableComponent
        EaComponents.ListView {
            model: undefined
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
        // Long-ID acceptance measures actual production cells in tst_table_geometry.qml.
        function test_base_selection_initializes_with_undefined_model() {
            const table = createTemporaryObject(baseTableComponent, parent);
            verify(table !== null);
            compare(table.count, 0);
            table.model = rows;
            tryCompare(table, "count", 1);
            table.model = undefined;
            tryCompare(table, "count", 0);
        }
        function test_arrow_font_is_bundled_and_loaded() {
            tryCompare(EaStyle.Fonts.encodeSansRegular, "status", FontLoader.Ready);
            compare(EaStyle.Fonts.encodeSansRegular.name, "Encode Sans");
            verify(String(EaStyle.Fonts.encodeSansRegular.source).includes("EncodeSans-Regular.ttf"));
        }
    }
}
