import QtQuick
import QtTest
import "RenderedTable.js" as Render
import edi.app
import EasyApplication.Gui.Components as Components

Item {
    id: surface
    width: 1400
    height: 400
    property int made: 0
    property string widest: "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW"
    ListModel {
        id: rows
    }
    FontMetrics {
        id: metrics
    }
    Component {
        id: tableFactory
        DataTable {
            width: 1200
            height: 200
            sourceModel: rows
            columns: [-1, -1]
            header: Components.ListViewHeader {
                Components.ListViewLabel {
                    text: "Name"
                }
                Components.ListViewLabel {
                    text: "A header wider than its values"
                }
            }
            delegate: TableRow {
                id: row
                required property string label
                required property string other
                Component.onCompleted: surface.made += 1
                Components.ListViewLabel {
                    text: row.label
                }
                Components.ListViewLabel {
                    text: row.other
                }
            }
        }
    }
    TestCase {
        name: "ModelColumnWidths"
        when: windowShown
        function init() {
            rows.clear();
            for (let i = 0; i < 1000; ++i)
                rows.append({
                    label: i === 917 ? surface.widest : "i",
                    other: "x"
                });
            surface.made = 0;
        }
        function test_distant_row_metrics_and_scroll() {
            const table = createTemporaryObject(tableFactory, surface);
            verify(table !== null, "The width witness uses the production DataTable and Qt model");
            verify(waitForPolish(table), "The table finishes its initial visible-row layout");
            tryVerify(() => table.fittedWidths.length === 2 && table.fittedWidths[0] > 0, 3000, "The model publishes both fitted column widths");
            verify(table.itemAtIndex(917) === null, "The widest row starts far outside the viewport");
            verify(surface.made < 100, "Column measurement creates no extra model rows: only viewport delegates may be built; actual " + surface.made);
            const header = table.headerItem;
            const labels = Render.descendants(header).filter(item => typeof item.text === "string" && typeof item.horizontalAlignment === "number" && (item.text === "Name" || item.text === "A header wider than its values"));
            verify(labels.length >= 2, "Both real header cells expose their fonts for independent Qt metrics");
            metrics.font = labels[0].font;
            const first = Math.ceil(metrics.advanceWidth(surface.widest));
            metrics.font = labels[1].font;
            const second = Math.ceil(metrics.advanceWidth("A header wider than its values"));
            verify(table.fittedWidths[0] >= first && table.fittedWidths[0] <= first + 2, "The first fitted width equals the distant widest data text at the actual Qt font metrics");
            verify(table.fittedWidths[1] >= second && table.fittedWidths[1] <= second + 2, "The second fitted width equals its widest header at Qt font metrics");
            const widths = JSON.stringify(Array.from(table.columnWidths));
            for (const index of [917, 999, 0]) {
                table.positionViewAtIndex(index, ListView.Center);
                verify(waitForPolish(table), "Scrolling lays out the actual requested rows");
                compare(JSON.stringify(Array.from(table.columnWidths)), widths, "Column widths remain unchanged when scrolling past the distant widest row and back");
            }
            rows.setProperty(917, "label", surface.widest + "WWWWW");
            tryVerify(() => table.fittedWidths[0] > first + 2, 3000, "A data edit invalidates the model width even while the edited row is off screen");
        }
    }
}
