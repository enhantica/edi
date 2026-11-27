// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtTest

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A table whose columns are all declared (kinds, and the model role of each text column) knows its width while its
// group is folded, and opening the group changes nothing: the width is the row number, each number at its kind's
// typical value, each text at its role's widest value and the fixed widths, with the spacings (draft ADR "Declared
// columns"). The three tables have the columns of Atomic displacements, the moments in another form and Reflections.
Item {
    id: root

    width: 1000
    height: 900

    // A table of `kinds` over `rows`, each cell showing its column's role (`roles`); short headers, so the contents
    // set every width.
    component DeclaredTable: DataTable {
        id: declared

        property var roles: []

        width: 900
        height: 150
        header: EaComponents.ListViewHeader {
            Repeater {
                model: declared.columnKinds.length
                delegate: EaComponents.ListViewLabel {
                    required property int index
                    text: index > 0 ? "a" : ""
                }
            }
        }
        delegate: TableRow {
            id: row

            required property var model

            Repeater {
                model: declared.columnKinds.length
                delegate: EaComponents.ListViewLabel {
                    required property int index
                    text: index === 0 ? row.index + 1 : String(row.model[declared.roles[index]] ?? "")
                }
            }
        }
    }

    Column {
        width: parent.width

        EaElements.GroupBox {
            id: adpGroup
            width: parent.width
            title: "Atomic displacements"
            collapsible: true
            collapsed: true

            DeclaredTable {
                id: adp
                columnKinds: ["index", "name", 60, "displacement", "displacement", "displacement", "displacement", "displacement", "displacement", "displacement"]
                columnTexts: ["", "label"]
                roles: ["", "label", "type", "u", "u", "u", "u", "u", "u", "u"]
                sourceModel: ListModel {
                    ListElement {
                        label: "La1"
                        type: "Uani"
                        u: "0.0123"
                    }
                    ListElement {
                        label: "O_apical_long_name"
                        type: "Biso"
                        u: "0.5"
                    }
                }
            }
        }
        EaElements.GroupBox {
            id: momentGroup
            width: parent.width
            title: "Magnetic moments"
            collapsible: true
            collapsed: true

            DeclaredTable {
                id: moments
                columnKinds: ["index", "name", "short", "value", "value", "value", "value", "text"]
                columnTexts: ["", "label", "ion", "", "", "", "", "symmform"]
                roles: ["", "label", "ion", "m", "m", "m", "m", "symmform"]
                sourceModel: ListModel {
                    ListElement {
                        label: "Co1"
                        ion: "Co2+"
                        m: "3.1"
                        symmform: "mx,my,mz"
                    }
                    ListElement {
                        label: "Fe"
                        ion: "none"
                        m: "0"
                        symmform: "mx,mx,0"
                    }
                }
            }
        }
        EaElements.GroupBox {
            id: reflectionGroup
            width: parent.width
            title: "Reflections"
            collapsible: true
            collapsed: true

            DeclaredTable {
                id: reflections
                columnKinds: ["index", "text", "number", "number", "number"]
                columnTexts: ["", "hkl"]
                roles: ["", "hkl", "d", "x", "f"]
                sourceModel: ListModel {
                    ListElement {
                        hkl: "1 0 0"
                        d: "3.9"
                        x: "22.8"
                        f: "120.5"
                    }
                    ListElement {
                        hkl: "10 -3 12"
                        d: "0.81"
                        x: "141.2"
                        f: "2.4"
                    }
                }
            }
        }
    }

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    TestCase {
        name: "DeclaredColumns"
        when: windowShown

        // Each kind's width as the draft ADR states it, independent of the table's code.
        function kindWidth(table, kind, column): real {
            const margin = AppSizes.tableCellMargin;
            if (typeof kind === "number")
                return kind;
            if (kind === "index")
                return table.numberColumnWidth;
            const samples = {
                "displacement": "0.0000",
                "value": "-0.0000",
                "number": "-00000.00"
            };
            if (samples[kind] !== undefined)
                return Math.ceil(metrics.advanceWidth(samples[kind])) + 2 * margin - 1;
            let widest = 0;
            for (let row = 0; row < table.sourceModel.count; ++row)
                widest = Math.max(widest, metrics.advanceWidth(String(table.sourceModel.get(row)[table.columnTexts[column]])));
            return Math.ceil(widest) + 2 * margin;
        }
        function expectedWidth(table): real {
            let sum = 0;
            for (let column = 0; column < table.columnKinds.length; ++column)
                sum += kindWidth(table, table.columnKinds[column], column);
            return sum + EaStyle.Sizes.tableColumnSpacing * (table.columnKinds.length - 1) + 2 * table.rowPadding;
        }
        function test_the_width_is_known_folded_and_stays_when_opened_data() {
            return [
                {
                    "tag": "atomic displacements",
                    "table": adp,
                    "group": adpGroup
                },
                {
                    "tag": "moments",
                    "table": moments,
                    "group": momentGroup
                },
                {
                    "tag": "reflections",
                    "table": reflections,
                    "group": reflectionGroup
                }
            ];
        }
        function test_the_width_is_known_folded_and_stays_when_opened(data) {
            verify(data.group.collapsed);
            tryVerify(() => data.table.naturalWidth > 0, 2000, "the width is known while the group is folded");
            const folded = data.table.naturalWidth;
            compare(folded, expectedWidth(data.table), "the kinds' widths and the spacings");
            data.group.collapsed = false;
            tryVerify(() => data.table.drawn && !data.table.measureRunning && !data.table.refitting, 2000);
            compare(data.table.naturalWidth, folded, "opening the group changes no width");
        }
    }
}
