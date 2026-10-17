// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import DisplayFontTests 1.0

Item {
    id: surface
    width: 1100
    height: 900
    Rectangle {
        anchors.fill: parent
        color: Style.Colors.themeBackground
    }
    QtObject {
        id: blocks
        property int count: 0
        function text(index, role) {
            if (role === "name")
                return "bank_" + index;
            if (role === "file")
                return "dataset_" + index + ".dat";
            return "phase_" + index + " · phase_" + index + ".edi";
        }
        signal dataChanged
    }
    DisplayFontProof {
        id: fonts
    }
    Component {
        id: namesFactory
        BlockNames {
            width: 600
        }
    }
    Component {
        id: examplesFactory
        ExamplesGroup {
            width: 800
        }
    }
    Component {
        id: preferencesFactory
        AppPreferencesDialog {}
    }
    TestCase {
        name: "ReportOwnerLooks"
        when: windowShown
        function initTestCase() {
            surface.Window.window.width = surface.width;
            surface.Window.window.height = surface.height;
        }
        function cleanup() {
            Preferences.dialogShown = false;
            Session.closeProject();
        }
        function test_project_items_have_distinct_lines_data() {
            const rows = [];
            for (const count of [0, 1, 11, 12, 30])
                for (const kind of ["structure", "experiment"])
                    rows.push({
                        tag: kind + "-" + count,
                        count: count,
                        kind: kind
                    });
            return rows;
        }
        function test_project_items_have_distinct_lines(data) {
            blocks.count = data.count;
            const view = createTemporaryObject(namesFactory, surface, {
                blocks: blocks,
                blockKind: data.kind
            });
            verify(view !== null && waitForPolish(view), "The real Project list lays out the independently named blocks");
            surface.Window.window.update();
            verify(waitForRendering(surface), "The actual block lines render before geometry is inspected");
            const indices = data.count <= 11 ? Array.from({
                length: data.count
            }, (_, i) => i) : [0, 1, 2, 3, 4, -1, data.count - 5, data.count - 4, data.count - 3, data.count - 2, data.count - 1];
            const expected = indices.map(i => i < 0 ? "…" : blocks.text(i, data.kind === "experiment" ? "name" : "label") + (data.kind === "experiment" ? " · " + blocks.text(i, "file") : ""));
            const drawn = Render.texts(view).filter(item => expected.includes(item.text));
            compare(JSON.stringify(drawn.map(item => item.text)), JSON.stringify(expected), "Each Project item names its datablock and file; more than eleven show exactly first five, ellipsis, last five");
            for (let i = 1; i < drawn.length; ++i) {
                const above = drawn[i - 1].mapToItem(view, 0, drawn[i - 1].height).y;
                const below = drawn[i].mapToItem(view, 0, 0).y;
                verify(below >= above, "Project items occupy separate nonoverlapping lines rather than a wrapped comma-separated run");
            }
        }
        function test_example_titles_use_a_regular_face() {
            const group = createTemporaryObject(examplesFactory, surface, {
                collapsed: false
            });
            verify(group !== null && waitForPolish(group), "The production Examples list lays out its real catalogue");
            const list = findChild(group, "examples.list");
            verify(list !== null && list.count > 0, "The regular-weight gate reaches actual example rows");
            list.forceLayout();
            const row = list.itemAtIndex(0);
            verify(row !== null, "The Examples viewport materializes a real title row");
            let title = null;
            tryVerify(() => {
                title = Render.texts(row).find(item => item.text === row.sample + " · " + row.origin);
                return title !== undefined;
            }, 1500, "The face check reaches the real example title rather than a secondary label");
            compare(title.font.bold, false, "Example titles use regular weight on desktop and WebAssembly");
            compare(title.font.weight, Font.Normal, "Example titles request the regular physical face");
            verify(!/bold/i.test(title.font.styleName), "Example titles cannot retain a Bold style-name override");
            compare(fonts.failures(title.text, title.font.family, title.font.weight, title.font.styleName, 400).join("\n"), "", "Actual example-title glyph runs use the bundled regular physical face on every platform");
        }
        function test_diagnostics_show_has_the_control_height_and_full_frame() {
            const dialog = createTemporaryObject(preferencesFactory, surface);
            verify(dialog !== null, "The actual Preferences dialog opens for its Develop controls");
            Preferences.dialogShown = true;
            tryCompare(dialog, "opened", true, 1000, "The actual Preferences popup finishes opening before pointer input");
            const tab = findChild(dialog, "preferences.tab.develop");
            verify(tab !== null, "Develop remains a real Preferences tab");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            verify(waitForPolish(dialog.contentItem) && waitForRendering(dialog.contentItem), "Develop completes layout and renders its bottom control");
            const show = findChild(dialog, "preferences.diagnostics");
            const reference = findChild(dialog, "preferences.engineThreads");
            verify(show !== null && reference !== null && show.visible, "The Show gate reaches the actual button and combo-box reference");
            compare(show.height, reference.height, "Diagnostics Show has the dialog's normal control height");
            const position = show.mapToItem(dialog.contentItem, 0, 0);
            verify(position.y >= 0 && position.y + show.height <= dialog.contentItem.height, "The entire Show frame remains inside the Develop page and dialog bounds");
            const image = grabImage(show);
            verify(image.width > 0 && image.height >= show.height, "The rendered Show button includes its entire bottom frame");
        }
    }
}
