// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "HeldEditGuards"
    when: windowShown
    property var app
    property var original
    SignalSpy { id: fields; signalName: "valueChanged" }
    SignalSpy { id: modified; signalName: "modifiedChanged" }
    SignalSpy { id: edited; signalName: "projectEdited" }
    Component { id: application; Main {} }
    function init() {
        Session.closeProject();
        app = application.createObject(null);
        verify(app !== null, "The held guard runs in the actual application window");
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "Loss protection starts with an independently saved user project");
        tryVerify(() => Session.project && !Session.project.calculating, 5000, "The saved user project finishes loading before the held edit");
        original = Session.project;
        verify(!original.modified, "The guard witness starts clean rather than relying on an earlier unsaved edit");
        verify(original.currentStructure !== null, "The real user project exposes its editable structure");
        fields.target = original.currentStructure.cell.lengthA;
        modified.target = original;
        edited.target = original;
        fields.clear(); modified.clear(); edited.clear();
        AppState.open(AppState.Page.Home);
    }
    function cleanup() {
        fields.target = null; modified.target = null; edited.target = null;
        if (Session.project)
            Session.project.adjusting = false;
        Session.closeProject();
        if (app)
            app.destroy();
        app = null; original = null;
    }
    function question() {
        const found = Probe.objectsWithProperty(app, "objectName").filter(x => x.objectName === "unsavedChanges");
        compare(found.length, 1, "The native guard owns one actual unsaved-changes question");
        return found[0];
    }
    function test_guard_data() {
        const rows = [];
        for (const action of ["close", "open", "create", "replace"])
            for (const state of ["held", "clean"])
                rows.push({tag: action + "-" + state, action: action, held: state === "held"});
        return rows;
    }
    function test_guard(data) {
        const value = original.currentStructure.cell.lengthA;
        const before = value.value;
        if (data.held) {
            original.adjusting = true;
            value.value = before * 1.013;
            tryVerify(() => !original.calculating, 5000, "The held edit completes its chart calculation before the guard reads state");
            compare(value.lastError, "", "The nontrivial held edit is admitted rather than refused by a busy or fixed parameter");
        }
        let runs = 0;
        const successor = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        const createParent = SettingsProof.emptyDirectory();
        const action = () => {
            ++runs;
            if (data.action === "create")
                verify(Session.createProject("guard_successor", "", String(createParent)), "A consented Create reaches its actual Session producer");
            else if (data.action === "replace") {
                const examples = Session.examples;
                examples.searchText = ""; examples.filterValue = "";
                let id = "";
                for (let row = 0; row < examples.count && !id; ++row)
                    id = String(examples.text(row, "exampleId"));
                verify(id.length > 0, "The replacement control uses an actually indexed local example");
                verify(Session.openExample(id), "A consented example replacement reaches its actual collection producer");
            } else
                verify(Session.openProject(successor), "A consented Open reaches its actual Session producer");
        };
        if (data.action === "close")
            app.close();
        else if (data.action === "create")
            AppState.afterChanges(action, () => {}, true);
        else
            AppState.afterChanges(action);
        const dialog = question();
        if (data.held) {
            tryVerify(() => dialog.visible || runs > 0 || (data.action === "close" && !app.visible), 2000, "Each real native loss guard reaches its question or continuation");
            verify(dialog.visible && runs === 0 && (data.action !== "close" || app.visible), "A held edit blocks native Close, Open, Create and replacement until consent");
            compare(Session.project, original, "Showing the question retains the exact held user project");
            compare(fields.count + modified.count + edited.count, 0, "Guard queries do not publish the held edit to ordinary listeners");
            const cancel = dialog.standardButton(Dialog.Cancel);
            verify(cancel !== null && cancel.visible && cancel.enabled, "The actual unsaved-changes question exposes Cancel");
            const point = Ui.clickPoint(cancel);
            verify(point !== null, "Cancel has an exposed actual input point");
            mouseClick(cancel, point.x, point.y);
            tryCompare(dialog, "visible", false, 2000, "Cancel finishes the real loss-prevention question");
            compare(Session.project, original, "Cancel preserves the original owner");
            original.adjusting = false;
            tryVerify(() => !original.calculating, 5000, "The retained held edit completes its actual release");
            compare(value.value, before * 1.013, "Cancel preserves the exact nontrivial edit when its ordinary value is published at release");
        } else {
            if (data.action === "close")
                tryCompare(app, "visible", false, 2000, "A genuinely clean project still permits native closing");
            else
                tryVerify(() => runs === 1, 3000, "A clean project admits the requested real replacement exactly once");
            verify(!dialog.visible, "The clean control does not invent an unsaved-changes question");
        }
    }
}
