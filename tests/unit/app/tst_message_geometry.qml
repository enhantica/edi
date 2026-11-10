// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1100
    height: 900
    Component {
        id: dialogComponent
        WarningsDialog {}
    }
    TestCase {
        name: "MessageGeometry"
        when: windowShown
        property var dialog

        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            dialog = createTemporaryObject(dialogComponent, surface);
            verify(dialog !== null);
        }
        function cleanup() {
            dialog.close();
            tryCompare(dialog, "visible", false);
            Session.closeProject();
        }
        function visibleItem(name) {
            let item = null;
            tryVerify(() => {
                item = Ui.find(dialog.contentItem, name);
                return item !== null;
            }, 2000, "The rendered dialog exposes " + name);
            return item;
        }
        function click(item) {
            const point = Ui.clickPoint(item);
            verify(point !== null);
            let delay = 0;
            for (let parent = item.parent; parent; parent = parent.parent) {
                if (typeof parent.pressDelay === "number")
                    delay = Math.max(delay, parent.pressDelay + 1);
            }
            mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
        }
        function test_wrapping_and_repeated_empty_transitions_settle() {
            let shortHeight = 0;
            let fixedWidth = 0;
            const fixtures = ["e04_t1/warning-project", "message_wrapping", "message_wrapping"];
            for (let pass = 0; pass < fixtures.length; ++pass) {
                verify(Session.openProject(Qt.resolvedUrl("../../fixtures/" + fixtures[pass])), Session.lastError);
                compare(Session.loadWarnings.count, 1);
                const message = Session.loadWarnings.text(0, "message");
                dialog.open();
                tryCompare(dialog, "opened", true);
                const table = visibleItem("warnings.list");
                const label = visibleItem("warnings.message.0");
                compare(label.text, message);
                verify(waitForPolish(dialog.contentItem, 2000), "Wrapped delegates reach stable geometry");
                verify(waitForRendering(dialog.contentItem));
                verify(label.width > 0 && label.height >= label.contentHeight, "The entire wrapped message fits its cell");
                if (pass === 0) {
                    compare(label.lineCount, 1);
                    shortHeight = table.contentHeight;
                    fixedWidth = dialog.width;
                } else {
                    verify(label.lineCount > 1, "The long native warning exercises real wrapping");
                    verify(table.contentHeight > shortHeight, "Wrapped rows grow beyond a one-line message");
                    compare(dialog.width, fixedWidth);
                }
                const populatedHeight = dialog.height;
                if (pass === 1)
                    click(findChild(dialog, "warnings.dismissAll"));
                else
                    click(visibleItem("warnings.dismiss.0"));
                tryCompare(Session.loadWarnings, "count", 0);
                verify(waitForPolish(dialog.contentItem, 2000), "Dismissal settles the empty-list geometry");
                visibleItem("warnings.empty");
                verify(table.height > 0, "An empty message list retains a nonzero viewport");
                if (pass > 0)
                    verify(dialog.height < populatedHeight, "Dismissing a wrapped row shrinks the dialog");
                compare(dialog.width, fixedWidth);
                dialog.close();
                tryCompare(dialog, "visible", false);
                Session.closeProject();
            }
        }
    }
}
