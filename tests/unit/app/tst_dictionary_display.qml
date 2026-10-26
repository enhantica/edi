import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "DisplayedText.js" as Displayed
import "FileSpelling.js" as FileSpelling

TestCase {
    id: test
    name: "DictionaryDisplay"
    when: windowShown
    property var appWindow
    property var expected
    Component { id: application; Main {} }
    function init() {
        expected = JSON.parse(Probe.readReferenceFile("dictionary.json"));
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Display checks use the production application window");
        Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.hasProject, "The independent P1 display project opens in the app");
        verify(waitForRendering(appWindow.contentItem), "The production window renders before inspection");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_page_data() {
        return [{tag: "structure", page: "structure"},
                {tag: "experiment", page: "experiment"},
                {tag: "analysis", page: "analysis"},
                {tag: "report", page: "report"}];
    }
    function test_page(data) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, "The selected workflow page reaches the actual viewport");
        const tier = data.page === "analysis" ? "extras" : "basic";
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + tier);
        if (tab && !tab.checked) Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
        tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000,
                  "The selected sidebar finishes its transition before inspection");
        const root = Ui.page(appWindow);
        const anchor = {structure: "cell", experiment: "instrument", analysis: "minimizer", report: "reportContents"}[data.page];
        Ui.expandGroup(test, Probe, appWindow, "group." + anchor);
        const anchorGroup = Ui.control(Probe, appWindow, "group." + anchor);
        verify(anchorGroup !== null, "Each checked page reaches its expected real sidebar group");
        const shown = Review.descendants(anchorGroup).filter(item => Ui.rendered(item));
        verify(shown.length > 0, "Every checked page has real rendered content");
        for (const item of shown) {
            if (typeof item.text !== "string") continue;
            verify(!/^_[a-zA-Z0-9_]+\./.test(item.text),
                   "A rendered field never shows a raw EDI data name");
            verify(!expected.tokens.includes(item.text),
                   "A rendered field shows its dictionary option name rather than the stored token");
        }
        for (const group of [anchorGroup]) {
            const id = String(group.objectName).slice(6);
            const reference = expected.categories[id];
            if (!reference || typeof group.title !== "string") continue;
            compare(group.title, reference.loop ? reference.loop_title : reference.title,
                    "Every rendered category title follows its dictionary source");
            const categoryName = new RegExp(reference.edi_name + "(?![\\w.])");
            verify([group].concat(Review.descendants(group)).some(item =>
                       typeof item.mapToItem === "function" && item.ToolTip && categoryName.test(item.ToolTip.text)),
                   "Every rendered group title has its category in a tooltip");
        }
        for (const field of shown.filter(item => item.item && typeof item.label === "string")) {
            const uid = String(field.item.category) + "." + String(field.item.name);
            const reference = expected.items[uid];
            if (!reference) continue;
            const labels = [reference.display_name];
            for (const token in (reference.variants || {})) {
                const variant = reference.variants[token];
                if (variant && variant.display_name) labels.push(variant.display_name);
            }
            verify(labels.includes(field.label),
                   "Every rendered parameter field uses its dictionary label or declared type variant");
            const tag = reference.edi_names ? reference.edi_names[0] : reference.cif_tag;
            verify([field].concat(Review.descendants(field)).some(item =>
                       typeof item.mapToItem === "function" && item.ToolTip && item.ToolTip.text.includes(tag)),
                   "Every rendered parameter label has its actual file item in a tooltip");
        }
        if (data.page !== "structure") return;
        const parameter = Session.project.currentStructure.cell.lengthA;
        parameter.value = 3.890915;
        Ui.expandGroup(test, Probe, appWindow, "group.cell");
        const field = Ui.control(Probe, appWindow, "cell.length_a");
        verify(field !== null, "Cell display is checked through its real field");
        Ui.scrollIntoView(field);
        const written = FileSpelling.parameter(Session.project.currentStructure.text.text, "cell.length_a");
        tryCompare(field, "text", written, 2000,
                   "The rendered cell field follows file/Text spelling under the active save rule");
        compare(field.label, expected.items["cell.length_a"].display_name,
                "The field label is read from the independently loaded dictionary file");
        verify(field.ToolTip.text.includes("_cell.length_a"),
               "The field tooltip identifies the EDI item it labels");
        field.forceActiveFocus();
        tryCompare(field, "text", written, 2000,
                   "An active edit field retains the same file/Text spelling");
        root.forceActiveFocus();
        compare(parameter.value, 3.890915, "Leaving an unchanged edit preserves the stored double");
        parameter.value = 3.8;
        tryCompare(field, "text", FileSpelling.parameter(Session.project.currentStructure.text.text, "cell.length_a"), 2000,
                   "A field retains exactly the file/Text trailing-zero spelling");
        compare(parameter.value, 3.8, "Display padding leaves the stored value unchanged");
    }
    function test_category_data() {
        return [
            {tag: "cell", page: "structure", tier: "basic", group: "cell", uid: "cell.length_a", value: 3.890915},
            {tag: "fractional", page: "structure", tier: "basic", group: "atom_site", uid: "atom_site.fract_x", value: 0.33333},
            {tag: "occupancy", page: "structure", tier: "basic", group: "atom_site", uid: "atom_site.occupancy", value: 0.5823456},
            {tag: "instrument", page: "experiment", tier: "basic", group: "instrument", uid: "instrument.setup_wavelength", value: 1.49412345},
            {tag: "peak", page: "experiment", tier: "basic", group: "peak", uid: "peak.broad_gauss_u", value: 0.123456789},
            {tag: "background", page: "experiment", tier: "basic", group: "background", uid: "background.intensity", value: 0.000012345678},
            {tag: "linked_structure", page: "experiment", tier: "basic", group: "linked_structure", uid: "linked_structure.scale", value: 1234567.8},
            {tag: "absorption", page: "experiment", tier: "extras", group: "absorption", uid: "absorption.mu_r", value: 0.036123456},
            {tag: "preferred_orientation", page: "experiment", tier: "extras", group: "preferred_orientation", uid: "preferred_orientation.march_r", value: 0.923456}
        ];
    }
    function test_category(data) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, "The category's page reaches the viewport before sidebar interaction");
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + data.tier);
        if (tab && !tab.checked) Ui.click(test, Probe, appWindow, "sideBar.tab." + data.tier);
        tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000,
                  "The category's sidebar finishes its transition");
        if (data.tag === "absorption")
            Session.project.currentExperiment.absorptionType = "cylinder-hewat";
        Ui.expandGroup(test, Probe, appWindow, "group." + data.group);
        const group = Ui.control(Probe, appWindow, "group." + data.group);
        verify(group !== null, "Every numeric category reaches its real group");
        const candidates = Review.descendants(group).filter(item => item.item &&
            String(item.item.category) + "." + String(item.item.name) === data.uid);
        verify(candidates.length > 0, "Every numeric witness reaches its own real parameter editor");
        const field = candidates[0];
        Ui.scrollIntoView(field);
        field.item.value = data.value;
        const written = FileSpelling.parameter(FileSpelling.block(Session.project, field.item), data.uid);
        verify(written !== "" && Number.isFinite(Number(written)),
               "Every numeric category has a nonempty numeric file/Text witness");
        tryVerify(() => Review.descendants(field).some(item =>
            Displayed.problem(item, written, false) === ""), 2000,
            "Every category field renders exactly its file/Text value in a native text item");
        compare(field.item.value, data.value, "The native rendered display preserves the input double");
    }

}
