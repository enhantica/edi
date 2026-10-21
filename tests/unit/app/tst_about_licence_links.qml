// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    id: surface

    height: 1000
    width: 1100

    Component {
        id: factory

        AboutDialog {
        }
    }
    TestCase {
        property var dialog

        function byText(value) {
            return texts().find(item => item.text === value);
        }
        function cleanup() {
            if (dialog)
                dialog.destroy();
            dialog = null;
        }
        function test_links_order_and_plain_text() {
            dialog = factory.createObject(surface);
            verify(dialog !== null, "The acceptance check opens the production About dialog");
            dialog.open();
            tryCompare(dialog, "opened", true, 1000, "The production About window finishes opening");
            const description = findChild(dialog.contentItem, "about.description");
            const copyright = findChild(dialog.contentItem, "about.copyright");
            const bsd = byText("BSD-3-Clause");
            const gpl = byText("GPL-3.0-only");
            const dependencies = byText("Third-party licences");
            verify(description && copyright && bsd && gpl && dependencies, "The one About page shows its description, licence identifiers, third-party link and contributors together");
            const at = item => item.mapToItem(surface, 0, 0).y;
            verify(at(description) < at(bsd) && at(bsd) < at(dependencies) && at(dependencies) < at(copyright), "About puts the licence pair between the description and the contributors");
            const before = at(bsd) - at(description) - description.height;
            const after = at(copyright) - at(dependencies) - dependencies.height;
            verify(Math.abs(before - after) < 1, "The pair of licence links has equal space above and below");
            for (const entry of [
                {
                    label: bsd,
                    expected: Probe.readFile("LICENSE")
                },
                {
                    label: gpl,
                    expected: Probe.readFile("COPYING")
                }
            ]) {
                mouseClick(entry.label, entry.label.width / 2, entry.label.height / 2);
                tryVerify(() => Render.descendants(surface.Window.window.contentItem).some(item => item.visible && typeof item.text === "string" && item.text === entry.expected && item.readOnly === true && item.textFormat === TextEdit.PlainText), 1000, "Each identifier opens its real licence as read-only plain text");
                keyClick(Qt.Key_Escape);
            }
            mouseClick(dependencies, dependencies.width / 2, dependencies.height / 2);
            const table = findChild(surface.Window.window.contentItem, "about.components");
            verify(table !== null && table.visible && table.count > 0, "The third-party link opens the actual dependency table");
            table.forceLayout();
            const header = Render.cells(table.headerItem);
            const row = table.itemAtIndex(0);
            verify(row !== null && row.enabled && row.opacity === 1, "Dependency rows look enabled");
            const cells = Render.cells(row);
            compare(header.length, 3, "The dependency popup has only component, version and licence columns");
            compare(cells.length, 3, "Each dependency row has the same three columns as its header");
            const left = item => item.mapToItem(table, 0, 0).x;
            verify(Math.abs(left(header[0]) - left(cells[0])) < 1, "The first dependency cell and header share their left margin");
            verify(Math.abs(left(header[2]) + header[2].width - left(cells[2]) - cells[2].width) < 1, "The last dependency cell and header share their right margin");
            mouseClick(cells[0], cells[0].width / 2, cells[0].height / 2);
            compare(table.selectedIndexes.length, 0, "Clicking an enabled-looking dependency never selects its row");
        }
        function texts() {
            return Render.texts(dialog.contentItem);
        }

        name: "AboutLicenceLinks"
        when: windowShown
    }
}
