import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundAnalysisOwnership"
    when: windowShown
    property var appWindow
    property var group
    property var roleWriters
    Component { id: application; ApplicationWindow { width: 900; height: 900; visible: true } }
    Component { id: parameters; ParametersGroup { width: 720; y: 20; tableViewportHeight: 500 } }
    Component {
        id: roleWriterFactory
        Repeater {
            model: Session.project ? Session.project.parameters : null
            delegate: Item {
                // Qt's model-role assignment calls QAbstractItemModel::setData,
                // then ParameterTableModel::setRole; setRole is not a QML method.
                property var rowModel: model
                function assign(next) { rowModel.value = next; }
            }
        }
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null && waitForRendering(appWindow.contentItem),
               "Analysis ownership must host the actual production ParametersGroup in a rendered window");
    }
    function cleanup() {
        if (roleWriters) roleWriters.destroy();roleWriters = null;
        if (group) group.destroy();group = null;
        Session.closeProject();appWindow.destroy();Probe.releaseScratchProjects();
    }
    function setup(kind, automatic) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/readonly-" + kind)),
               "Analysis ownership must load real free and fixed background rows for " + kind);
        const exp = Session.project.currentExperiment;
        exp.backgroundEstimateMode = automatic ? "auto" : "manual";
        compare(exp.backgroundEstimateMode, automatic ? "auto" : "manual",
                "The ownership stimulus must reach the actual mode setter before editing");
        group = parameters.createObject(appWindow.contentItem, {project: Session.project});
        verify(group !== null && waitForPolish(group), "The real Analysis Main table must finish layout");
        const table = Ui.find(group, "parameters.list", true);
        verify(table !== null && table.sourceModel !== null, "Analysis must expose its production parameter filter");
        table.sourceModel.categoryFilter = "background";
        table.sourceModel.variability = ParameterFilterModel.All;
        verify(waitForPolish(group), "The real Background category must finish laying out its editors");
        return {exp: exp, table: table, filtered: Probe.rows(table.sourceModel)};
    }
    function exercise(kind, route, fixed, automatic) {
        const context = setup(kind, automatic);
        const rowIndex = context.filtered.findIndex(row => row.parameter.free !== fixed);
        verify(rowIndex >= 0, "The actual filtered Background table must contain the requested free/fixed control");
        const item = context.filtered[rowIndex].parameter;
        const before = item.value, flags = item.free;
        const text = context.exp.text.text;
        group.selected = item;
        let cell = null;
        tryVerify(() => {
            cell = Ui.find(group, "parameters.value." + rowIndex, true);
            return cell !== null && cell.item === item;
        }, 500, "The keyboard target must edit the selected actual background ParameterItem");
        const target = before + 0.125;
        if (route === "cell") {
            Ui.scrollIntoView(cell);
            const hit = Ui.clickPoint(cell);
            verify(hit !== null, "The actual Analysis value cell must expose a visible pointer target");
            mouseClick(cell, hit.x, hit.y);
            cell.forceActiveFocus();
            verify(cell.activeFocus, "The actual Analysis value cell must receive keyboard focus before the edit attempt");
            if (automatic) {
                verify(before !== 9, "The typed Auto negative control must differ from the original value");
                cell.selectAll();
                verify(SettingsProof.key(cell, Qt.Key_9), "The Auto Analysis cell must receive an actual attempted numeric key");
            } else {
                verify(SettingsProof.type(cell, String(target)), "The Manual Analysis editor must receive real numeric keyboard input");
            }
            verify(SettingsProof.key(cell, Qt.Key_Return), "Return must exercise the production Analysis commit path");
        } else if (route === "slider") {
            const slider = Ui.find(group, "parameters.slider", true);
            verify(slider !== null, "The selected Analysis row must expose its real parameters.slider input");
            Ui.scrollIntoView(slider);
            const hit = Ui.clickPoint(slider);
            verify(hit !== null, "The actual Analysis slider must expose a visible pointer target");
            mousePress(slider, slider.width * .5, hit.y);
            mouseMove(slider, slider.width * .8, hit.y);
            mouseRelease(slider, slider.width * .8, hit.y);
            if (automatic) verify(!slider.enabled,
                "Analysis must disable its value slider for Auto-owned points and coefficients, including fixed rows");
        } else if (route === "model") {
            const all = Probe.rows(Session.project.parameters);
            const sourceIndex = all.findIndex(row => row.parameter === item);
            verify(sourceIndex >= 0, "The role-write control must address the same actual registered ParameterItem");
            roleWriters = roleWriterFactory.createObject(group);
            verify(roleWriters !== null, "The public role-write control must instantiate actual Qt model delegates");
            tryCompare(roleWriters, "count", all.length, 500,
                       "The Qt model-role delegates must address every actual registered row");
            verify(roleWriters.itemAt(sourceIndex).rowModel.parameter === item,
                   "The role-write delegate must target the same background ParameterItem as Analysis");
            roleWriters.itemAt(sourceIndex).assign(target);
        } else {
            item.value = target;
        }
        if (automatic) {
            compare(item.value, before, "Every Analysis user value entry must refuse Auto background writes before mutation: " + route);
            compare(item.free, flags, "A refused Auto value edit must preserve the free/fixed state");
            compare(context.exp.backgroundEstimateMode, "auto", "A refused Analysis write must retain Auto mode");
            compare(context.exp.text.text, text,
                    "Refused Analysis edits must preserve all rows, constants, settings and saved provenance exactly");
            if (route === "model" || route === "binding") {
                verify(/auto/i.test(item.lastError) && /background/i.test(item.lastError),
                       "The shared user-edit boundary must explain Auto background ownership on refusal: " + item.lastError);
            }
            if (route === "cell") verify(cell.locked,
                "Analysis value cells must lock Auto values while retaining the free/fixed context menu");
        } else {
            verify(Math.abs(item.value - before) > 1e-8,
                   "The same actual Analysis input must change a Manual background value, proving a live edit path: " + route);
            if (route !== "slider") compare(item.value, target, "Manual Analysis edits must retain the requested numeric value");
        }
        console.log("BACKGROUND_ANALYSIS_OWNERSHIP " + kind + " " + route + " mode=" + (automatic ? "auto" : "manual") + " checked=true");
    }
    function test_entries_data() {
        const result = [];
        ["line-segment", "polynomial", "chebyshev"].forEach(kind => {
            ["cell", "slider", "model", "binding"].forEach(route => {
                [false, true].forEach(fixed => result.push({tag: kind + "_" + route + "_" + (fixed ? "fixed" : "free"), kind: kind, route: route, fixed: fixed, automatic: true}));
                result.push({tag: kind + "_" + route + "_manual", kind: kind, route: route, fixed: false, automatic: false});
            });
        });
        return result;
    }
    function test_entries(data) { exercise(data.kind, data.route, data.fixed, data.automatic); }
    function test_free_fixed_data() { return ["line-segment", "polynomial", "chebyshev"].map(kind => ({tag: kind, kind: kind})); }
    function test_free_fixed(data) {
        const context = setup(data.kind, true);
        [true, false].forEach(initial => {
            const index = context.filtered.findIndex(row => row.parameter.free === initial);
            verify(index >= 0, "The Analysis free/fixed control must reach both authored variability states");
            const item = context.filtered[index].parameter, before = item.value;
            let box = null;
            tryVerify(() => {
                box = Ui.find(group, "parameters.free." + index, true);
                return box !== null && box.enabled;
            }, 500, "Auto must retain an enabled actual Analysis free/fixed checkbox");
            Ui.scrollIntoView(box);
            const hit = Ui.clickPoint(box);
            verify(hit !== null, "Auto free/fixed must remain an actual pointer action");
            mouseClick(box, hit.x, hit.y);
            compare(item.free, !initial, "Actual Analysis checkbox input must toggle free/fixed in Auto");
            compare(item.value, before, "Permitted Auto free/fixed toggling must preserve the numeric value");
            compare(context.exp.backgroundEstimateMode, "auto", "Permitted free/fixed toggling must retain Auto");
        });
        console.log("BACKGROUND_ANALYSIS_FREE_FIXED " + data.kind + " checked=true");
    }
}
