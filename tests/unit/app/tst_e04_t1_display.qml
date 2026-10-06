import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "DisplayedText.js" as Displayed
import "../../fixtures/e04_t1/display_oracle.js" as Oracle

TestCase {
    id: test
    name: "E04T1DisplayedValues"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    Component { id: textWitness; Text { width: 160; height: 30; text: "powder" } }
    Component { id: fieldWitness; TextField { width: 160; height: 30; readOnly: true; text: "62" } }
    Component { id: comboWitness; ComboBox { width: 160; height: 30; enabled: false; model: ["powder"]; currentIndex: 0 } }
    Component { id: clipWitness; Item { width: 160; height: 30; clip: true } }

    Component {
        id: fixedGroupWitness
        Item {
            width: 140; height: 24
            objectName: "group.fixedWitness"
            property string title: ""
            property bool collapsible: false
            property bool collapsed: false
            property alias titleArea: header
            property alias contentItem: body
            Item { id: header; visible: false; width: 140; height: 0 }
            Item { id: body; anchors.fill: parent }
        }
    }

    function initTestCase() {
        failOnWarning(/.*/);
        appWindow = application.createObject(null);
        verify(appWindow !== null, "gate 3: displayed values run against production Main");
        verify(waitForRendering(appWindow.contentItem), "gate 3: production window renders before value checks");
    }
    function cleanupTestCase() {
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem), "gate 3: pending layouts settle before window destruction");
        appWindow.destroy();
    }
    function click(name) {
        const selected = Ui.control(Probe, appWindow, name);
        // Re-selecting the same tab need not schedule a new rendered frame.
        if (selected && selected.checked === true) return;
        Ui.click(test, Probe, appWindow, name);
    }
    function findAny(root, name) {
        if (root.objectName === name) return root;
        const children = root.children || [];
        for (let i = 0; i < children.length; ++i) {
            const found = findAny(children[i], name);
            if (found) return found;
        }
        return null;
    }
    function renderers(root) {
        let found = [];
        if (root.visible && typeof root.text === "string" &&
                (typeof root.getText === "function" || typeof root.lineCount === "number"))
            found.push(root);
        (root.children || []).forEach(child => found = found.concat(renderers(child)));
        return found;
    }
    function test_loaded_display_data() { return Oracle.frozen.cases; }
    function test_loaded_display(data) {
        failOnWarning(data.tag === Oracle.frozen.cases[0].tag
            ? /\A(?!QRhiGles2: Failed to create (?:temporary context|context)\z)[\s\S]*\z/ : /.*/);
        const url = Probe.repoUrl(data.path);
        // Reuse only the same unedited, read-only input; a different fixture is
        // always reopened. Selection and page setup below run for every row.
        if (!Session.hasProject || String(url) !== "file://" + Session.project.path)
            Session.openProject(url);
        verify(Session.hasProject, "gate 3: independent display fixture opens: " + data.path + " " + Session.lastError);
        if (data.selection) {
            const collection = data.page === "structure" ? "structures" : "experiments";
            const index = Probe.rows(Session.project[collection]).findIndex(row => row.name === data.selection);
            verify(index >= 0, "gate 3: selected block comes from the frozen file name");
            Session.project[data.page === "structure" ? "currentStructureIndex" : "currentExperimentIndex"] = index;
        }
        click("appBar.tab." + data.page);
        click("sideBar.tab." + data.tier);
        let root = Ui.page(appWindow);
        if (data.group !== "engines") {
            Ui.expandGroup(test, Probe, appWindow, "group." + data.group);
            root = Ui.control(Probe, appWindow, "group." + data.group);
        } else {
            root = Ui.windowRoot(appWindow);
        }
        let failures = [];
        data.fields.forEach(field => {
            const name = field[0], expected = field[1], kind = field[2];
            const control = kind === "label" ? Ui.find(root, name) : findAny(root, name);
            verify(control !== null, "gate 3: every frozen display field exists in its selected group: " + name);
            Ui.scrollIntoView(control);
            // Repeated blocks can show identical text without scheduling a frame.
            // Request one explicitly before retaining the rendering assertion.
            appWindow.update();
            verify(waitForPolish(appWindow, 2000) && waitForRendering(appWindow.contentItem),
                   "gate 3: field layout and rendering settle before observing displayed text");
            verify(Ui.rendered(control), "gate 3: field is exposed in the actual viewport: " + name);
            if (kind === "disabled")
                verify(!control.enabled, "gate 3: loaded experiment axes remain disabled");
            if (kind === "readonly" || kind === "number")
                verify(control.readOnly, "gate 3: derived and scan fields remain read-only");
            const isCombo = typeof control.displayText === "string" && control.popup !== undefined;
            const items = kind === "label" ? renderers(control)
                        : isCombo ? renderers(control.contentItem) : [control];
            verify(items.length > 0, "gate 3: each field has an actual native glyph renderer");
            //  note 14: gui-components Utils.toDefaultPrecision uses
            // three significant digits. Only display expectations are rounded;
            // frozen input doubles and  measuredRange model checks stay whole.
            // Point counts remain exact integers, never precision-rounded.
            const displayedExpected = kind === "number" && name !== "range.points"
                ? Number(expected.toPrecision(3)) : expected;
            const errors = items.map(item => Displayed.problem(item, displayedExpected, kind === "number"));
            if (!errors.includes("")) failures.push(name + ": " + errors.join("; "));
        });
        // Collect every field in a group so a blank first axis cannot hide the
        // other three blanks. Each project/group is a separate QtTest data row.
        compare(failures.join("\n"), "", "gate 3: native rendered text equals independent .edi/ITA values");
    }
    function test_display_oracle_escape_controls() {
        const label = createTemporaryObject(textWitness, appWindow.contentItem);
        const field = createTemporaryObject(fieldWitness, appWindow.contentItem);
        const combo = createTemporaryObject(comboWitness, appWindow.contentItem);
        verify(waitForRendering(appWindow.contentItem), "gate 3 controls: native witnesses render");
        compare(Displayed.problem(label, "powder", false), "", "gate 3 controls: a correct label passes");
        compare(Displayed.problem(field, 62, true), "", "gate 3 controls: a correct native field passes");
        compare(Displayed.problem(combo.contentItem, "powder", false), "", "gate 3 controls: a correct disabled combo passes");
        ["", "neutron"].forEach(wrong => {
            combo.contentItem.text = wrong;
            verify(Displayed.problem(combo.contentItem, "powder", false) !== "",
                   "gate 3 controls: correct combo model/index cannot hide blank or wrong rendered text");
            field.text = wrong;
            verify(Displayed.problem(field, 62, true) !== "",
                   "gate 3 controls: blank or wrong number text fails despite the expected model value");
        });
        label.visible = false;
        verify(Displayed.problem(label, "powder", false) !== "", "gate 3 controls: hidden correct text fails");
        label.visible = true;
        label.opacity = 0;
        verify(Displayed.problem(label, "powder", false) !== "", "gate 3 controls: transparent correct text fails");
        label.opacity = 1;
        label.color = "transparent";
        verify(Displayed.problem(label, "powder", false) !== "", "gate 3 controls: invisible glyph colour fails");
        const viewport = createTemporaryObject(clipWitness, appWindow.contentItem);
        const clipped = createTemporaryObject(textWitness, viewport, {x: 200});
        verify(Displayed.problem(clipped, "powder", false) !== "",
               "gate 3 controls: a correct label outside its clipped viewport fails");
    }
    function test_fixed_group_exposure_controls() {
        const pane = createTemporaryObject(clipWitness, appWindow.contentItem);
        const group = createTemporaryObject(fixedGroupWitness, pane);
        const inactive = createTemporaryObject(clipWitness, appWindow.contentItem);
        const other = createTemporaryObject(fixedGroupWitness, inactive);
        const window = {contentArea: [pane, inactive], appBarCentralTabs: {currentIndex: 0}};
        compare(Ui.control(Probe, window, group.objectName), group,
                "note 8: fixed untitled groups are discovered through rendered content in the active pane");
        group.visible = false;
        compare(Ui.control(Probe, window, group.objectName), null,
                "note 8: an inactive pane cannot substitute its same-named visible group");
        window.appBarCentralTabs.currentIndex = 1;
        compare(Ui.control(Probe, window, group.objectName), other,
                "note 8: selecting the other pane exposes only its own group");
        group.visible = true;
        window.appBarCentralTabs.currentIndex = 0;
        [[200, 0], [0, 50]].forEach(position => {
            group.x = position[0]; group.y = position[1];
            compare(Ui.control(Probe, window, group.objectName), null,
                    "note 8: fixed content outside either clipped viewport axis is not exposed");
        });
        group.x = 0; group.y = 0;
        group.collapsible = true;
        compare(Ui.control(Probe, window, group.objectName), null,
                "note 8: a foldable group cannot bypass its missing rendered header");
        group.collapsible = false;
        group.collapsed = true;
        compare(Ui.control(Probe, window, group.objectName), null,
                "note 8: collapsed content cannot masquerade as a fixed-open group");
        group.collapsed = false;
        group.title = "Titled";
        compare(Ui.control(Probe, window, group.objectName), null,
                "note 8: a titled group still requires its rendered header");
    }
    function test_parameter_readonly_columns_data() {
        //  seams 2/4: independent admissible ranges and bracket-derived
        // uncertainty, including a nonzero crystallographic decimal uncertainty.
        return [
            {tag: "bounded", path: "structure.atom_sites[La].occupancy", namePieces: ["layer-group", "atom", "La", "fill", "Occ."], error: "0", units: "", bounds: ["0", "1"]},
            {tag: "half-bounded", path: "experiment.absorption.mu_r", namePieces: ["microscope", "tint", "μ R"], error: "0", units: "", bounds: ["0", "inf"]},
            {tag: "unbounded", path: "experiment.linked_structure.scale", namePieces: ["microscope", "layer-group", "1", "weight", "Scale"], error: "", units: "", bounds: ["-inf", "inf"]},
            {tag: "decimal-uncertainty", fixture: "pd-neut-tof_si-sepd_start-2", path: "structure.cell.length_a", namePieces: ["layer-group", "cube", "ruler", "a"],
             error: "0.001", units: "Å"}
        ];
    }
    function test_parameter_readonly_columns(data) {
        Session.openProject(Probe.repoUrl("docs/user/cli/" + (data.fixture || "pd-neut-cwl_lbco-hrpt_start-2") + "/project"));
        verify(Session.hasProject, "seam 4: parameter display witness opens");
        click("appBar.tab.analysis");
        click("sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
        const index = Probe.rows(Session.project.parameters).findIndex(row => row.path === data.path);
        verify(index >= 0, "seam 4: independent canonical parameter path is present");
        const table = Ui.control(Probe, appWindow, "parameters.list");
        verify(table !== null, "seam 4: real parameter table is visible");
        Ui.scrollIntoView(table);
        verify(waitForPolish(appWindow, 2000),
               "seam 4: table viewport layout settles before positioning the parameter row");
        table.forceLayout();
        table.positionViewAtIndex(index, ListView.Center);
        tryVerify(() => findAny(table, "parameters.row." + index) !== null, 2000,
                  "seam 4: scrolling instantiates the selected parameter row");
        const row = findAny(table, "parameters.row." + index);
        const cells = row.contentRowData;
        verify(cells.length >= 7, "seams 2/4: real row exposes the named read-only columns");
        //  idea 12 / ADR-0017 §8: the name is now an iconified composition,
        // with its canonical path in the tooltip. Symbols below are frozen
        // pre- metadata regression pins (core/include/edi/parameter_spec.hpp
        // at f3ea7af), not values generated by ParameterNames or the app.
        let columns = [[3, data.units], [4, data.error]];
        if (data.bounds) columns = columns.concat([[5, data.bounds[0]], [6, data.bounds[1]]]);
        // Positioning the ListView alone does not settle its enclosing sidebar.
        // A later layout can move the row back outside that clipped viewport.
        // Retry exposure, never the expected values: wrong text must still fail.
        tryVerify(() => {
            Ui.scrollIntoView(row);
            return waitForPolish(appWindow, 2000) &&
                waitForRendering(appWindow.contentItem, 2000) &&
                !Ui.moving(appWindow.contentItem) &&
                columns.every(column => Ui.rendered(cells[column[0]]));
        }, 2000, "seam 4: parameter labels settle inside every enclosing viewport before reading");
        const nameRenderers = renderers(cells[1]);
        compare(nameRenderers.length, data.namePieces.length,
                "idea 12/seam 4: the native name composition has exactly the declared pieces");
        nameRenderers.forEach((item, i) => compare(Displayed.problem(item, data.namePieces[i], false), "",
                "idea 12/seam 4: every native icon, row label and short name renders its frozen declaration"));
        columns.forEach(column => compare(Displayed.problem(cells[column[0]], column[1], false), "",
                "seams 2/4: native units, error and bound labels display independent values"));
    }
}
