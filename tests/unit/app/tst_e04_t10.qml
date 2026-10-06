import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

//  I17-I20. Hand-run while app-test is owner-disabled.
// Buttons and tooltips are transcribed from diffraction-lib structure.html.j2,
// not from the StructureToolbar under test.
TestCase {
    id: test
    name: "E04T10StructureView"
    when: windowShown
    property var appWindow
    property var view
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " gate 5 requires the production app window");
        appWindow.requestActivate();
        tryCompare(appWindow, "active", true, 2000, " gate 5 real pointer input reaches the active production window");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function open(path) {
        Session.openProject(Probe.repoUrl(path));
        verify(Session.hasProject, " gate 5 opens the independent committed dataset");
        Ui.click(test, Probe, appWindow, "appBar.tab.structure");
        tryVerify(() => Review.find(Ui.page(appWindow), "structure.view") !== null, 5000, " gate 5 Structure page hosts the real structure view");
        view = Review.find(Ui.page(appWindow), "structure.view");
        tryVerify(() => view.current, 10000, " I12 first worker publication presents current geometry");
    }
    function object(name) {
        const result = findChild(view, name);
        verify(result !== null, " P5 view exposes its declared object identity: " + name);
        return result;
    }
    function click(name) {
        const button = object("structure.toolbar." + name);
        mouseClick(button, button.width / 2, button.height / 2);
    }
    function test_committed_structure_counts_data() {
        // Counts are independently measured crysta API values in packet P0 table 1.
        return [
            {
                tag: "cosio",
                path: "pd-neut-cwl_cosio-d20_start-1",
                atoms: 39,
                bonds: 34
            },
            {
                tag: "lbco",
                path: "pd-neut-cwl_lbco-hrpt_start-2",
                atoms: 15,
                bonds: 6
            },
            {
                tag: "ncaf",
                path: "pd-neut-tof_ncaf-wish-2bank_start-3",
                atoms: 90,
                bonds: 109
            }
        ];
    }
    function test_committed_structure_counts(data) {
        open("docs/user/cli/" + data.path + "/project");
        compare(view.atomCount, data.atoms, " I3 root count is independent crysta position count");
        compare(view.bondCount, data.bonds, " I7 root count is independent crysta bond count");
        compare(view.cellEdgeCount, 12, " I2 root count exposes twelve cell edges");
        verify(view.revision > 0, " I12 a visible first scene has a publication revision");
        ["spheres", "cylinders", "shared", "labels", "legend", "hover", "hint"].forEach(name => object("structure.view." + name));
        compare(object("structure.view.hint").text.split(/\n|,\s*/), ["drag = rotate", "wheel = zoom", "right-drag = pan"], " I19 hint retains the three independent pointer rules across line layout");
    }
    function test_toolbar_buttons_tooltips_order_placement_and_defaults() {
        open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project");
        const buttons = [["projection", "Parallel (orthographic) view"], ["a", "View along a"], ["b", "View along b"], ["c", "View along c"], ["reset", "Reset view"], ["atoms", "Atoms: all / asymmetric unit / none"], ["labels", "Labels"], ["bonds", "Bonds"], ["cell", "Cell"], ["axes", "Axes"]];
        let right = -1;
        buttons.forEach(row => {
            const button = object("structure.toolbar." + row[0]);
            verify(button.visible, " I18 available features have visible buttons");
            compare(button.toolTip, row[1], " I18 tooltip is the diffraction-lib button's tooltip");
            compare(button.width, button.height, " I18 reused chart buttons keep their square shape");
            const point = button.mapToItem(view, 0, 0);
            verify(point.x > right && point.y > 0 && point.y < view.height / 3, " I18 buttons follow the reference order inside the view's top band");
            right = point.x;
        });
        verify(!findChild(view, "structure.toolbar.moments"), " I18 no unused moments feature is offered");
        ["atoms", "bonds", "cell", "axes"].forEach(name => verify(object("structure.toolbar." + name).checked, " I18 default available geometry features are on"));
        verify(!object("structure.toolbar.labels").checked, " I18 labels start off");
        const colors = object("structure.toolbar.colors");
        compare(colors.currentText, "jmol", " I18 colour scheme defaults to the base's Jmol palette");
        compare(colors.count, 2, " I18 colour selector offers exactly the two published schemes");
        compare(colors.textAt(0), "jmol", " I18 Jmol is the first colour scheme");
        compare(colors.textAt(1), "vesta", " I18 VESTA is the second colour scheme");
        const download = object("structure.toolbar.download");
        compare(download.toolTip, "Download PNG", " I18 download action names the PNG output");
        const at = download.mapToItem(view, 0, 0);
        verify(at.x > view.width / 2 && at.y > view.height / 2, " I18 standalone download sits inside the bottom-right corner");
    }
    function test_opened_popup_shows_its_entries_data() {
        return [
            {
                tag: "colors-light",
                appearance: false,
                dark: false,
                entries: ["jmol", "vesta"]
            },
            {
                tag: "colors-dark",
                appearance: false,
                dark: true,
                entries: ["jmol", "vesta"]
            },
            {
                tag: "atom-view-light",
                appearance: true,
                dark: false,
                entries: ["covalent", "vdw", "ionic", "adp"]
            },
            {
                tag: "atom-view-dark",
                appearance: true,
                dark: true,
                entries: ["covalent", "vdw", "ionic", "adp"]
            }
        ];
    }
    function test_opened_popup_shows_its_entries(data) {
        // I18 and D11's externally declared choices must be drawn, not only counted.
        EaStyle.Colors.theme = data.dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project");
        if (data.appearance) {
            Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
            Ui.expandGroup(test, Probe, appWindow, "group.appearance");
        }
        const combo = data.appearance ? findChild(Ui.page(appWindow), "structure.appearance.atomView") : object("structure.toolbar.colors");
        verify(combo !== null, " I18/D11 real selected page owns the popup control");
        Ui.scrollIntoView(combo);
        tryVerify(() => Ui.exposed(combo), 2000, " I18/D11 popup is opened by an exposed user control");
        verify(waitForPolish(appWindow, 2000), " gate 5 popup opener has completed its real layout");
        tryVerify(() => !Ui.moving(appWindow.contentItem), 2000, " gate 5 popup opener's page has finished moving");
        mouseClick(combo, combo.width / 2, combo.height / 2);
        tryCompare(combo.popup, "opened", true, 2000, " I18/D11 mouse input really opened the popup");
        const list = combo.popup.contentItem;
        compare(list.count, data.entries.length, " I18/D11 opened popup has every independently named entry");
        data.entries.forEach((expected, index) => {
            tryVerify(() => list.itemAtIndex(index) !== null, 2000, " I18/D11 every popup entry is materialised");
            const entry = list.itemAtIndex(index);
            compare(entry.text, expected, " I18/D11 the opened entry actually carries its required visible text");
            const label = entry.contentItem;
            compare(label.text, expected, " I18/D11 the actual drawn popup label names its independently declared choice");
            let effectiveOpacity = label.color.a;
            for (let ancestor = label; ancestor; ancestor = ancestor.parent) {
                verify(ancestor.visible && ancestor.opacity > 0, " gate 5 opened popup text has no invisible or transparent visual ancestor");
                effectiveOpacity *= ancestor.opacity;
            }
            const contrast = Math.abs(label.color.r - combo.popup.background.color.r) + Math.abs(label.color.g - combo.popup.background.color.g) + Math.abs(label.color.b - combo.popup.background.color.b);
            verify(contrast * effectiveOpacity > .1, " gate 5 popup glyph colour remains visibly distinct after actual inherited opacity");
            verify(Ui.rendered(label) && label.opacity > 0 && label.color.a > 0 && label.contentWidth > 0 && label.contentHeight > 0, " I18/D11 popup text has visible unclipped nonempty glyph geometry");
            verify(waitForRendering(entry), " gate 5 popup label reaches a rendered frame");
            const image = grabImage(entry);
            // Text ink must change an interior pixel from the label's blank margin.
            // No screenshot golden or product-generated correctness value is used.
            const blank = image.pixel(image.width - 2, Math.floor(image.height / 2));
            let ink = false;
            for (let y = 2; y < image.height - 2 && !ink; ++y)
                for (let x = 2; x < image.width - 2 && !ink; ++x) {
                    const pixel = image.pixel(x, y);
                    ink = Math.abs(pixel.r - blank.r) + Math.abs(pixel.g - blank.g) + Math.abs(pixel.b - blank.b) > .1;
                }
            verify(ink, " gate 5 each opened popup entry draws visible text ink in both themes");
        });
        const choice = list.itemAtIndex(data.entries.length - 1);
        mouseClick(choice, choice.width / 2, choice.height / 2);
        tryCompare(combo, "currentIndex", data.entries.length - 1, 2000, " I18/D11 visible last entry accepts real pointer input");
        tryCompare(combo.popup, "opened", false, 2000, " I18/D11 selecting a visible entry closes the popup");
    }
    function test_projection_reset_and_feature_behaviour() {
        open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project");
        const projection = object("structure.toolbar.projection");
        click("projection");
        compare(projection.toolTip, "Perspective view", " I18 projection button toggles to the real perspective camera");
        ["a", "b", "c"].forEach(name => click(name));
        click("reset");
        compare(projection.toolTip, "Perspective view", " I18 reset preserves the selected projection");
        click("projection");
        compare(projection.toolTip, "Parallel (orthographic) view", " I18 opposite toggle restores orthographic projection");
        click("atoms");
        verify(object("structure.toolbar.atoms").checked, " I18 first atom toggle keeps the asymmetric unit visible");
        click("atoms");
        verify(!object("structure.toolbar.atoms").checked, " I18 second atom toggle hides all atoms");
        click("atoms");
        verify(object("structure.toolbar.atoms").checked, " I18 third atom toggle restores all atoms");
        ["labels", "bonds", "cell", "axes"].forEach(name => {
            const button = object("structure.toolbar." + name);
            const before = button.checked;
            click(name);
            compare(button.checked, !before, " I18 each feature button changes actual view options");
            click(name);
            compare(button.checked, before, " I18 a second feature toggle restores its prior state");
        });
        click("cell");
        compare(view.cellEdgeCount, 0, " I8 cell toggle removes the actual cell edges");
        click("cell");
        compare(view.cellEdgeCount, 12, " I8 cell toggle restores the actual cell edges");
        click("bonds");
        compare(view.bondCount, 0, " I7 bond toggle removes the actual bond cylinders");
        click("bonds");
        compare(view.bondCount, 6, " I7 bond toggle restores the independently counted bonds");
    }
}
