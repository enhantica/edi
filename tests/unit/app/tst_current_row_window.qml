// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "../../fixtures/current_row_style/reference.js" as RowStyle

TestCase {
    id: test
    name: "CurrentRowWindow"
    when: windowShown
    property var appWindow
    property int savedTheme
    Component {
        id: application
        Main {}
    }
    function init() {
        savedTheme = Style.Colors.theme;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The reported row-input paths run in the actual application window");
        appWindow.width = 1200;
        appWindow.height = 1000;
        verify(waitForRendering(appWindow.contentItem), "The actual application window renders before pointer input");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
        Style.Colors.theme = savedTheme;
    }
    function test_input_data() {
        const cases = [];
        for (const table of ["atomSites.list", "parameters.list"])
            for (const mode of ["selection", "cursor", "background"])
                for (const dark of [false, true])
                    cases.push({
                        tag: "window." + table + "-" + mode + (dark ? "-dark" : "-light"),
                        table: table,
                        mode: mode,
                        dark: dark
                    });
        return cases;
    }
    function click(cell) {
        Ui.scrollIntoView(cell);
        verify(waitForPolish(appWindow), "The actual sidebar finishes layout before its cell receives input");
        const point = Ui.clickPoint(cell);
        verify(point !== null, "The reported cell is inside the actual application's visible sidebar");
        let delay = 0;
        for (let p = cell.parent; p; p = p.parent)
            if (typeof p.pressDelay === "number")
                delay = Math.max(delay, p.pressDelay + 1);
        mouseClick(cell, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
    }
    function test_input(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "The full-window input check opens a real scientific project");
        const atoms = data.table === "atomSites.list";
        Ui.click(test, Probe, appWindow, "appBar.tab." + (atoms ? "structure" : "analysis"));
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        if (atoms)
            Ui.expandGroup(test, Probe, appWindow, "group.atom_site");
        const table = Ui.find(Ui.page(appWindow), data.table, true);
        verify(table !== null && table.count > 1, "The active production page exposes distinct real table rows");
        table.positionViewAtIndex(0, ListView.Beginning);
        table.forceLayout();
        verify(waitForPolish(table), "The actual page's row delegates materialize before input");
        const first = Render.cells(table.itemAtIndex(0))[0];
        const second = Render.cells(table.itemAtIndex(1))[0];
        const editor = Ui.find(table.itemAtIndex(1), atoms ? "atomSite.label.1" : "parameters.value.1", true);
        verify(editor !== null && editor.enabled, "The reported editable cell belongs to the actual second row");
        if (data.mode === "selection") {
            click(first);
            compare(table.markerRow, 0, "A non-editable cell click moves the actual page's line without Tab");
            click(second);
            compare(table.markerRow, 1, "Another non-editable cell click moves the actual page's line immediately");
            click(first);
            click(editor);
            compare(table.markerRow, 1, "An editable-cell click moves the actual page's line immediately without Tab");
            tryVerify(() => second.font.bold && String(second.color) === String(Style.Colors.themeAccent) && !first.font.bold && String(first.color) !== String(Style.Colors.themeAccent), 1500, "Only the actual current row number is bold in the accent colour");
        } else if (data.mode === "cursor") {
            click(editor);
            tryVerify(() => Render.descendants(editor).some(item => item.activeFocus && item.readOnly === false && item.cursorVisible === true && item.cursorRectangle && item.cursorRectangle.height > 0), 500, "The actual application grants the clicked editor an active text cursor without Tab");
        } else {
            click(editor);
            mouseMove(appWindow.contentItem, appWindow.contentItem.width - 2, appWindow.contentItem.height - 2);
            const root = appWindow.contentItem, theme = data.dark ? "dark" : "light";
            for (const index of [0, 1]) {
                const row = table.itemAtIndex(index);
                tryVerify(() => {
                    appWindow.update();
                    const at = row.mapToItem(root, 8, 4), image = grabImage(root);
                    return String(image.pixel(Math.round(at.x), Math.round(at.y))).toLowerCase() === (index % 2 ? RowStyle.reference.even : RowStyle.reference.odd)[theme];
                }, 1500, "The actual page retains alternating row backgrounds after the pointer leaves its active editor");
            }
        }
    }
}
