// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
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
                    prefix: "BSD 3-Clause License"
                },
                {
                    label: gpl,
                    prefix: "GNU GENERAL PUBLIC LICENSE"
                }
            ]) {
                mouseClick(entry.label, entry.label.width / 2, entry.label.height / 2);
                tryVerify(() => Render.descendants(surface).some(item => item.visible && typeof item.text === "string" && item.text.includes(entry.prefix) && item.readOnly === true && item.textFormat === TextEdit.PlainText), 1000, "Each identifier opens its real licence as read-only plain text");
                keyClick(Qt.Key_Escape);
            }
        }
        function texts() {
            return Render.texts(dialog.contentItem);
        }

        name: "AboutLicenceLinks"
        when: windowShown
    }
}
