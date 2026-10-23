import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundReadonly"
    when: windowShown
    property var appWindow
    property var hostedBackground
    Component { id: application; Main {} }
    Component { id: manualBackground; BackgroundGroup { width: 650; x: 20; y: 20; z: 1000 } }
    function init() {
        Session.closeProject();
        appWindow = null;
        hostedBackground = null;
    }
    function cleanup() {
        if (hostedBackground) hostedBackground.destroy();
        hostedBackground = null;
        Session.closeProject();
        appWindow.close();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function control(name) {
        const result = Ui.find(hostedBackground || Ui.page(appWindow), name, true);
        verify(result !== null, "The active Main pane must expose stable control " + name);
        return result;
    }
    function choose(selector, auto) {
        Ui.scrollIntoView(selector);
        // The shared helper settles viewport/layout/rendering and honours each
        // ancestor's pressDelay before delivering real input.
        Ui.click(test, Probe, appWindow, selector.objectName);
        tryVerify(() => selector.popup && selector.popup.visible, 500,
                  "The actual estimation mode selector must open its choices");
        verify(SettingsProof.key(selector, auto ? Qt.Key_End : Qt.Key_Home),
               "The mode selector must receive real option navigation");
        verify(SettingsProof.key(selector, Qt.Key_Return), "Return must select the actual estimation mode");
        tryCompare(selector.popup, "visible", false, 500,
                   "The selected mode popup must finish closing before table input");
    }
    function state(model, points) {
        return JSON.stringify(Probe.rows(model).map(row => points ?
            [row.id, row.position, row.intensity.value, row.intensity.free] :
            [row.id, row.order, row.coef.value, row.coef.free]));
    }
    function exercise(kind, contextRow) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/readonly-" + kind)),
               "The app must open authored rows before its first estimate: " + kind);
        // Open the fixture before Main constructs its charts; the ownership
        // workflow does not need an empty-project chart and its replacement.
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Read-only acceptance must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The read-only table window must render");
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.background");
        const pointType = kind === "line-segment";
        const selector = control("background_estimate.mode");
        compare(String(selector.label).trim().toLowerCase(), "estimation mode",
                "Every type must label the manual/auto selector estimation mode");
        verify(/manual/i.test(String(selector.ToolTip.text)) && /auto/i.test(String(selector.ToolTip.text)),
               "The estimation mode tooltip must explain both Manual and Auto");
        const table = control(pointType ? "background.list" : "background.terms");
        const model = table.sourceModel;
        const identities = pointType ? ["background.id.0", "background.position.0", "background.intensity.0"] :
                                      ["background.termId.0", "background.order.0", "background.coef.0"];
        const cells = identities.map(control);
        cells.forEach(cell => verify(cell.enabled && !cell.readOnly,
            "Every Manual row editor must remain enabled and writable: " + cell.objectName));
        const fixed = control(pointType ? "background.intensity.1" : "background.coef.1");
        // TextInput colours have the production ThemeChange animation. Wait for
        // their exact semantic targets, rather than snapshotting a transition.
        tryVerify(() => Qt.colorEqual(cells[2].color, EaStyle.Colors.chartForegroundsExtra[1]) &&
                       Qt.colorEqual(fixed.color, EaStyle.Colors.themeForeground) &&
                       cells.slice(0, 2).every(cell => Qt.colorEqual(cell.color, EaStyle.Colors.themeForeground)),
                  EaStyle.Times.themeChange + 500,
                  "The Manual table theme transition must finish at the ordinary id/position/fixed and free colours before capturing them");
        const colours = cells.map(cell => String(cell.color));
        const fixedColour = String(fixed.color);
        verify(Qt.colorEqual(cells[2].color, EaStyle.Colors.chartForegroundsExtra[1]),
               "The free control must start in the normal green parameter colour");
        verify(cells[2].font.bold, "The authored free intensity or coefficient must be visibly bold in Manual");
        const before = state(model, pointType);
        choose(selector, true);
        tryCompare(Session.project.currentExperiment, "backgroundEstimateMode", "auto", 500,
                   "Real selection must enter Auto before testing edit refusal");
        tryVerify(() => cells.every((cell, index) => String(cell.color) === colours[index]) &&
                       String(fixed.color) === fixedColour,
                  EaStyle.Times.themeChange + 500,
                  "The Auto table theme transition must settle before judging preserved Manual colours");
        console.log("BACKGROUND_READINESS mode=actual-click theme=settled");
        cells.forEach((cell, index) => {
            verify(cell.enabled, "Auto must keep each value-locked cell enabled for its normal appearance: " + cell.objectName);
            compare(String(cell.color), colours[index], "Auto read-only cells must preserve their Manual colours, including free green");
        });
        verify(cells[2].font.bold, "Auto must retain the free intensity or coefficient's bold appearance");
        compare(String(fixed.color), fixedColour, "Auto must preserve the normal fixed parameter colour too");
        verify(fixed.enabled && !fixed.font.bold,
               "Auto must retain the ordinary fixed parameter appearance and enabled context target");
        const buttons = pointType ? ["background.append", "background.namePoints", "background.estimate"] :
                                    ["background.appendTerm", "background.nameTerms", "background.estimate"];
        buttons.forEach(name => verify(!control(name).enabled,
            "Auto must disable all three below-table actions: " + name));
        const deletePrefix = pointType ? "background.remove." : "background.removeTerm.";
        const deletes = Ui.itemsWithProperty(table, "objectName").filter(item => String(item.objectName).startsWith(deletePrefix));
        verify(deletes.length >= 2 && deletes.every(item => !item.enabled),
               "Auto must disable every instantiated row delete, including both free and fixed rows");
        if (contextRow >= 0) {
            const cell = contextRow === 0 ? cells[2] : fixed;
            Ui.scrollIntoView(cell);
            const target = Ui.clickPoint(cell);
            verify(target !== null, "A read-only value cell must remain a real context-menu target");
            // Before: opening the menu alone counted. After: real free/fixed clicks work in Auto.
            let inputDelay = 0;
            for (let parent = cell.parent; parent; parent = parent.parent)
                if (typeof parent.pressDelay === "number") inputDelay = Math.max(inputDelay, parent.pressDelay + 1);
            mouseClick(cell, target.x, target.y, Qt.RightButton, Qt.NoModifier, inputDelay);
            tryVerify(() => cell.contextMenu !== null && cell.contextMenu.opened, 500,
                      "A real right click must open the Auto value cell contextMenu");
            const flag = cell.fitCheckBox;
            verify(flag !== null && flag !== undefined && flag.visible && flag.enabled,
                   "Auto value-cell context menu must expose an enabled free/fixed checkbox through fitCheckBox");
            const hit = Ui.clickPoint(flag);
            verify(hit !== null, "The Auto free/fixed context checkbox must receive actual pointer input");
            mouseClick(flag, hit.x, hit.y);
            const expected = JSON.parse(before);
            expected[contextRow][3] = !expected[contextRow][3];
            compare(state(model, pointType), JSON.stringify(expected),
                    "Each Auto context toggle must change only the selected free flag, preserving ids and values");
            compare(Session.project.currentExperiment.backgroundEstimateMode, "auto",
                    "A working free/fixed context action must retain Auto estimation mode");
            compare(cell.font.bold, expected[contextRow][3],
                    "The Auto cell must update its free/fixed appearance after each actual context toggle");
            cell.contextMenu.close();
            console.log("BACKGROUND_AUTO_FLAGS " + kind + " row=" + contextRow + " context=toggle mode=auto");
            return;
        }
        // Read-only is observable edit refusal, not Qt's readOnly flag (which hides fit controls).
        cells.forEach((cell, index) => {
            Ui.scrollIntoView(cell);cell.forceActiveFocus();
            // Text acceptance is not event delivery: a read-only field may reject
            // the key immediately or its commit guard may reject it on Return.
            verify(cell.activeFocus, "Each Auto cell must have focus before the actual edit attempt");
            verify(typeof cell.selectAll === "function", "Each Auto cell must expose its actual text-selection entry");
            cell.selectAll();
            verify(SettingsProof.key(cell, Qt.Key_9), "Every Auto cell must receive an actual attempted value or id key");
            verify(SettingsProof.key(cell, Qt.Key_Return), "Return must exercise the actual Auto commit guard");
            compare(state(model, pointType), before,
                    "Auto keyboard edits of ids, positions/orders and values must leave every row unchanged");
        });
        Ui.scrollIntoView(table);
        verify(table.enabled && table.interactive && table.contentHeight > table.height,
               "Auto must keep the populated background table enabled, interactive and scrollable");
        const y = table.contentY, hit = Ui.clickPoint(table);
        verify(hit !== null, "The Auto table must expose a real wheel target");
        mouseWheel(table, hit.x, hit.y, 0, -240);
        tryVerify(() => table.contentY > y, 500, "Actual wheel input must scroll the read-only Auto table");
        console.log("BACKGROUND_READONLY " + kind + " auto=refused scroll=true context=preserved manual=separate-control");
    }
    function manualReturn(kind) {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/readonly-" + kind));
        const text = SettingsProof.text(input, "experiments/bank.edi");
        verify(text.indexOf("_background_estimate.mode manual") >= 0,
               "The bounded Manual-return control must start from the same authored background rows");
        verify(SettingsProof.write(input, "experiments/bank.edi",
               text.replace("_background_estimate.mode manual", "_background_estimate.mode auto")),
               "The Manual-return fixture changes only the mode to the unchanged post-refusal Auto state");
        verify(Session.openProject(input), "The Manual-return control must load its actual persisted Auto state");
        appWindow = application.createObject(null);
        verify(appWindow !== null && waitForRendering(appWindow.contentItem),
               "Manual return must use the rendered full production window");
        // Other cases retain full page/category navigation. This return flow
        // hosts the identical Main BackgroundGroup in the visible Main page,
        // avoiding an unrelated pattern chart before scroll/selector/key input.
        hostedBackground = manualBackground.createObject(Ui.page(appWindow),
            {experiment: Session.project.currentExperiment});
        verify(hostedBackground !== null && waitForPolish(hostedBackground),
               "Manual return must render the actual Main BackgroundGroup");
        verify(waitForRendering(hostedBackground),
               "The hosted production table must render before real scrolling or mode input");
        const pointType = kind === "line-segment";
        const selector = control("background_estimate.mode");
        compare(Session.project.currentExperiment.backgroundEstimateMode, "auto",
                "The Manual-return control must begin in Auto before actual selector input");
        const table = control(pointType ? "background.list" : "background.terms");
        const model = table.sourceModel;
        const before = state(model, pointType);
        Ui.scrollIntoView(table);
        const y = table.contentY, hit = Ui.clickPoint(table);
        verify(hit !== null, "Manual return must retain the real scrolled-table precondition");
        mouseWheel(table, hit.x, hit.y, 0, -240);
        tryVerify(() => table.contentY > y, 500, "Manual return must follow actual Auto table scrolling");
        const buttons = pointType ? ["background.append", "background.namePoints", "background.estimate"] :
                                    ["background.appendTerm", "background.nameTerms", "background.estimate"];
        const identities = pointType ? ["background.id.0", "background.position.0", "background.intensity.0"] :
                                      ["background.termId.0", "background.order.0", "background.coef.0"];
        choose(selector, false);
        tryCompare(Session.project.currentExperiment, "backgroundEstimateMode", "manual", 500,
                   "Real selection must return to Manual before permitting edits");
        buttons.forEach(name => verify(control(name).enabled, "Manual must restore all three below-table actions: " + name));
        table.positionViewAtBeginning();
        verify(waitForPolish(table), "The scrolled Manual table must recreate its first row editor");
        const editor = control(identities[2]);
        verify(!editor.readOnly && editor.enabled, "Manual must restore a writable intensity or coefficient cell");
        Ui.scrollIntoView(editor);editor.forceActiveFocus();
        verify(SettingsProof.type(editor, "8.125"), "The permitted Manual cell must receive real keyboard input");
        verify(SettingsProof.key(editor, Qt.Key_Return), "Return must commit the permitted Manual value");
        const changed = Probe.rows(model)[0];
        compare(pointType ? changed.intensity.value : changed.coef.value, 8.125,
                "The actual Manual editor must update the underlying public parameter exactly");
        const expected = JSON.parse(before);
        expected[0][2] = 8.125;
        compare(state(model, pointType), JSON.stringify(expected),
                "The Manual return must change only the entered height or coefficient, preserving ids, positions/orders and flags");
        console.log("BACKGROUND_MANUAL_RETURN " + kind + " auto=loaded scroll=true manual=edited");
    }
    function test_points_manual_return() { manualReturn("line-segment"); }
    function test_polynomial_manual_return() { manualReturn("polynomial"); }
    function test_chebyshev_manual_return() { manualReturn("chebyshev"); }
    function test_points() { exercise("line-segment", -1); }
    function test_points_free() { exercise("line-segment", 0); }
    function test_points_fixed() { exercise("line-segment", 1); }
    function test_polynomial() { exercise("polynomial", -1); }
    function test_polynomial_free() { exercise("polynomial", 0); }
    function test_polynomial_fixed() { exercise("polynomial", 1); }
    function test_chebyshev() { exercise("chebyshev", -1); }
    function test_chebyshev_free() { exercise("chebyshev", 0); }
    function test_chebyshev_fixed() { exercise("chebyshev", 1); }
}
