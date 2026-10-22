import QtQuick
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "LegendMarkParity"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment")), "Legend parity must use independently committed element data");
        Ui.click(test, Probe, appWindow, "appBar.tab.structure");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.atom_site");
        verify(waitForRendering(appWindow.contentItem), "Legend and table must both render before comparison");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_pattern_marks_are_drawn_with_series_widths() {
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        let toggle;
        tryVerify(() => {
            toggle = Ui.control(Probe, appWindow, "chart.toolbar.legend");
            return toggle !== null;
        }, 3000, "The pattern legend button becomes rendered beside the coloured axis titles");
        compare(toggle.checked, false, "Coloured axis titles replace the legend box by default");
        Ui.click(test, Probe, appWindow, "chart.toolbar.legend");
        tryCompare(toggle, "checked", true, 2000, "The legend button explicitly shows the optional legend box");
        let legend;
        tryVerify(() => {
            legend = Ui.control(Probe, appWindow, "chart.legend");
            return legend !== null;
        }, 3000, "The actual pattern legend must be reached after chart population");
        tryVerify(() => Probe.rows(legend.entries).length > 0, 2000, "The pattern legend must expose its series");
        const rows = Probe.rows(legend.entries);
        verify(rows.some(row => row.mark === "line") && rows.some(row => row.mark === "tick") && rows.some(row => row.mark === "dash"), "The witness must exercise series lines, dashed background and Bragg ticks");
        rows.forEach(row => {
            verify(row.mark === "line" || row.mark === "tick" || row.mark === "dash", "Pattern marks must be geometry kinds, never Unicode characters");
            verify(row.markWidth > 0, "Every pattern mark must carry its series' positive width");
        });
        const entries = Ui.itemsWithProperty(legend, "segments");
        compare(entries.length, rows.length, "Every pattern series must instantiate one shared-height legend row");
        entries.forEach(entry => compare(entry.height, AppSizes.legendRowHeight, "Pattern legend rows must retain the default legend spacing"));
        const shapes = Ui.itemsWithProperty(legend, "thickness").filter(item => item.visible);
        compare(shapes.length, rows.length, "Every pattern legend mark must instantiate a real drawn shape");
        shapes.forEach(shape => {
            compare(shape.parent.text, "", "The shape's container must not draw a text glyph for its mark");
            verify(!Probe.nativeText(shape), "A pattern mark must be a geometric item, not a native text node");
            if (shape.parent.mark === "line") {
                compare(shape.height, shape.thickness, "A horizontal mark must use its series' width as its thickness");
                verify(shape.width > shape.height, "A line mark must be a horizontal shape");
            } else if (shape.parent.mark === "dash") {
                const pieces = Array.from(shape.children).filter(child => child.visible && typeof child.color !== "undefined" && child.width > 0);
                verify(pieces.length >= 2, "A dashed background mark contains multiple separated geometric strokes");
                const ordered = pieces.sort((a, b) => a.x - b.x);
                function sample(image, x, y) {
                    const at = shape.mapToItem(appWindow.contentItem, x, y);
                    return String(image.pixel(Math.floor(at.x * image.width / appWindow.contentItem.width), Math.floor(at.y * image.height / appWindow.contentItem.height)));
                }
                const middleGap = (ordered[0].x + ordered[0].width + ordered[1].x) / 2;
                tryVerify(() => {
                    const rendered = grabImage(appWindow.contentItem);
                    return ordered.every(piece => sample(rendered, piece.x + piece.width / 2, piece.height / 2) !== sample(rendered, middleGap, shape.thickness / 2));
                }, 2000, "The actual dashed legend finishes the page transition before its underlay is captured");
                shape.visible = false;
                verify(waitForRendering(appWindow.contentItem), "The dash witness captures the actual legend underlay without its mark");
                const underlay = grabImage(appWindow.contentItem);
                shape.visible = true;
                verify(waitForRendering(appWindow.contentItem), "The actual dashed mark returns before its ink and gap are sampled");
                let frame;
                tryVerify(() => {
                    frame = grabImage(appWindow.contentItem);
                    return pieces.every(piece => sample(frame, piece.x + piece.width / 2, piece.height / 2) !== sample(underlay, piece.x + piece.width / 2, piece.height / 2));
                }, 2000, "Every geometric background dash contributes visible ink over the actual legend underlay");
                pieces.forEach(piece => {
                    verify(!Probe.nativeText(piece) && piece.width > piece.height, "Every background dash is horizontal geometry rather than a text glyph");
                    compare(piece.height, shape.thickness, "Every background dash retains the series line width");
                });
                for (let i = 1; i < ordered.length; ++i) {
                    const end = ordered[i - 1].x + ordered[i - 1].width, start = ordered[i].x;
                    verify(start > end, "The dashed background has a positive empty gap between consecutive strokes");
                    compare(sample(frame, (end + start) / 2, shape.thickness / 2), sample(underlay, (end + start) / 2, shape.thickness / 2), "The rendered dash gap stays empty instead of becoming a solid line");
                }
            } else {
                compare(shape.width, shape.thickness, "A Bragg tick must use its series' width as its thickness");
                verify(shape.height > shape.width, "A tick mark must be a vertical shape");
            }
        });
    }
    function test_element_icon_and_colour_match_table_data() {
        return [
            {
                tag: "jmol"
            },
            {
                tag: "vesta"
            }
        ];
    }
    function test_element_icon_and_colour_match_table(row) {
        Session.project.structureViewOptions.colorScheme = row.tag;
        const tableIcon = Ui.control(Probe, appWindow, "atomSite.icon.0");
        const legend = Ui.control(Probe, appWindow, "structure.view.legend");
        verify(tableIcon !== null && legend !== null, "The actual table and structure legend must be reached");
        let entries = [];
        tryVerify(() => {
            entries = Ui.itemsWithProperty(legend, "segments");
            return entries.length > 0;
        }, 2000, "The structure legend must create its real element entries");
        const element = entries.find(entry => entry.label === "La");
        verify(element !== undefined, "The minimal structure's element must have a legend entry");
        const expected = tableIcon.segments[0];
        tryVerify(() => element.segments[0].icon === expected.icon, 2000, "The legend must use the exact atom icon emitted by the table");
        tryVerify(() => String(element.segments[0].color) === String(tableIcon.segments[0].color), 2000, "The legend and table must share the selected scheme's element colour");
        const midpoint = Math.round((AppSizes.legendRowHeight + EaStyle.Sizes.comboBoxHeight) / 2);
        entries.forEach(entry => compare(entry.height, midpoint, "Structure legend rows must sit halfway between pattern and filter-dropdown spacing"));
        verify(element.segments[0].dot !== true && element.segments[0].text === undefined, "The element icon must replace both circle shapes and text dots");
    }
}
